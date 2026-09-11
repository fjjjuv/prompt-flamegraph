# prompt-flamegraph - Lightweight prompt context flamegraph generator for LLMs.
# Copyright (C) 2026  fjjjuv
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Registry of known LLM models: encodings, prices and context windows."""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelSpec:
    name: str
    encoding: str  # "cl100k_base" | "o200k_base" | "estimate" (non-OpenAI models)
    input_per_mtok: float
    output_per_mtok: float
    context_window: int


MODELS: dict[str, ModelSpec] = {
    "gpt-4o": ModelSpec("gpt-4o", "o200k_base", 2.50, 10.00, 128_000),
    "gpt-4o-mini": ModelSpec("gpt-4o-mini", "o200k_base", 0.15, 0.60, 128_000),
    "gpt-4.1": ModelSpec("gpt-4.1", "o200k_base", 2.00, 8.00, 1_047_576),
    "gpt-4.1-mini": ModelSpec("gpt-4.1-mini", "o200k_base", 0.40, 1.60, 1_047_576),
    "gpt-4.1-nano": ModelSpec("gpt-4.1-nano", "o200k_base", 0.10, 0.40, 1_047_576),
    "o4-mini": ModelSpec("o4-mini", "o200k_base", 1.10, 4.40, 200_000),
    "claude-sonnet-4": ModelSpec("claude-sonnet-4", "estimate", 3.00, 15.00, 200_000),
    "claude-opus-4.1": ModelSpec("claude-opus-4.1", "estimate", 15.00, 75.00, 200_000),
    "claude-haiku-3.5": ModelSpec("claude-haiku-3.5", "estimate", 0.80, 4.00, 200_000),
    "llama-3.3-70b": ModelSpec("llama-3.3-70b", "estimate", 0.59, 0.79, 128_000),
    "mistral-large": ModelSpec("mistral-large", "estimate", 2.00, 6.00, 128_000),
    "gemini-2.5-pro": ModelSpec("gemini-2.5-pro", "estimate", 1.25, 10.00, 1_048_576),
    "gemini-2.5-flash": ModelSpec("gemini-2.5-flash", "estimate", 0.30, 2.50, 1_048_576),
}

ALIASES: dict[str, str] = {
    "4o": "gpt-4o",
    "gpt4o": "gpt-4o",
    "4o-mini": "gpt-4o-mini",
    "gpt4o-mini": "gpt-4o-mini",
    "4.1": "gpt-4.1",
    "gpt4.1": "gpt-4.1",
    "4.1-mini": "gpt-4.1-mini",
    "4.1-nano": "gpt-4.1-nano",
    "o4mini": "o4-mini",
    "sonnet": "claude-sonnet-4",
    "sonnet-4": "claude-sonnet-4",
    "claude-sonnet": "claude-sonnet-4",
    "opus": "claude-opus-4.1",
    "opus-4.1": "claude-opus-4.1",
    "claude-opus": "claude-opus-4.1",
    "haiku": "claude-haiku-3.5",
    "haiku-3.5": "claude-haiku-3.5",
    "claude-haiku": "claude-haiku-3.5",
    "llama": "llama-3.3-70b",
    "llama-3.3": "llama-3.3-70b",
    "llama-70b": "llama-3.3-70b",
    "mistral": "mistral-large",
    "gemini": "gemini-2.5-pro",
    "gemini-pro": "gemini-2.5-pro",
    "2.5-pro": "gemini-2.5-pro",
    "gemini-flash": "gemini-2.5-flash",
    "2.5-flash": "gemini-2.5-flash",
}


LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)
OFFLINE_ENV = "PROMPT_FLAMEGRAPH_OFFLINE"
_O200K_NAMES = re.compile(r"\b(gpt-4o|gpt-4\.1|gpt-5|o[0-9])\b")
_ANSI_SEQ = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")  # CSI escape sequences
_NONPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_MAX_PAYLOAD = 50_000_000  # bytes; refuse absurdly large pricing downloads
_MAX_NAME = 128
_MAX_ERROR_NAMES = 15

# _load_cache() memo: re-parsing a multi-MB models.json on every lookup was
# ~18ms per call. Keyed on (path, mtime, size) so a changed cache file is
# picked up for the cost of one stat().
_cache_memo: dict[str, object] = {"key": None, "data": {}, "fetched_at": None}


def _offline() -> bool:
    return os.environ.get(OFFLINE_ENV, "") not in ("", "0")


def _cache_path() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(root) / "prompt-flamegraph" / "models.json"


def _sanitize_remote(name: object, rec: object) -> ModelSpec | None:
    """Build a ModelSpec from a raw cache entry, or None when it is malformed.

    Names are stripped of control/ANSI bytes and capped at _MAX_NAME chars;
    prices must be finite and context_window a positive int.
    """
    if not isinstance(rec, dict):
        return None
    clean = _NONPRINTABLE.sub("", _ANSI_SEQ.sub("", str(name))).strip()[:_MAX_NAME].strip()
    if not clean:
        return None
    try:
        input_price = float(rec["input_per_mtok"])
        output_price = float(rec.get("output_per_mtok") or 0.0)
        context = int(rec["context_window"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    if not (math.isfinite(input_price) and math.isfinite(output_price)) or context <= 0:
        return None
    return ModelSpec(
        name=clean,
        encoding=str(rec.get("encoding", "estimate")),
        input_per_mtok=input_price,
        output_per_mtok=output_price,
        context_window=context,
    )


def _load_cache() -> dict[str, ModelSpec]:
    """Read the remote pricing cache; empty dict when missing or corrupt.

    Memoized on the cache file's (path, mtime, size): repeated lookups cost a
    single stat() instead of re-reading and re-parsing the whole file.
    """
    if _offline():
        return {}
    path = _cache_path()
    try:
        stat = path.stat()
    except OSError:
        return {}
    key = (str(path), stat.st_mtime, stat.st_size)
    if _cache_memo["key"] == key:
        return _cache_memo["data"]  # type: ignore[return-value]
    data: dict[str, ModelSpec] = {}
    fetched_at = None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        fetched_at = raw.get("fetched_at")
        for name, rec in raw["models"].items():
            spec = _sanitize_remote(name, rec)
            if spec is not None:
                data[spec.name] = spec
    except Exception:
        data, fetched_at = {}, None
    _cache_memo.update(key=key, data=data, fetched_at=fetched_at)
    return data


def _declared_length(resp) -> int | None:
    """Best-effort Content-Length of a response, or None when unknown."""
    try:
        value = resp.headers.get("Content-Length")
        return int(value) if value else None
    except (AttributeError, TypeError, ValueError):
        return None


def update_models(url: str = LITELLM_URL, timeout: float = 15.0) -> int:
    """Fetch LiteLLM's community pricing table into the local cache.

    Returns the number of models written. This is the only function that
    touches the network; lookups are offline by default.
    """
    if _offline():
        raise RuntimeError(f"{OFFLINE_ENV} is set; refusing to fetch pricing data")
    req = urllib.request.Request(url, headers={"User-Agent": "prompt-flamegraph"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            declared = _declared_length(resp)
            if declared is not None and declared > _MAX_PAYLOAD:
                raise ValueError(
                    f"pricing payload too large: {declared} bytes "
                    f"(limit {_MAX_PAYLOAD})"
                )
            try:
                body = resp.read(_MAX_PAYLOAD + 1)
            except TypeError:
                body = resp.read()  # stubbed responses without a size argument
    except (urllib.error.URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(f"failed to fetch pricing data: {reason}") from exc
    if len(body) > _MAX_PAYLOAD:
        raise ValueError(f"pricing payload exceeds {_MAX_PAYLOAD} bytes")
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("unexpected pricing payload: not a JSON object")

    models: dict[str, dict] = {}
    for name, rec in payload.items():
        if not isinstance(rec, dict):
            continue
        input_cost = rec.get("input_cost_per_token")
        context = rec.get("max_input_tokens") or rec.get("max_tokens")
        if input_cost is None or context is None:
            continue
        if rec.get("litellm_provider") == "openai":
            encoding = "o200k_base" if _O200K_NAMES.search(name) else "cl100k_base"
        else:
            encoding = "estimate"
        try:
            models[name] = {
                "encoding": encoding,
                "input_per_mtok": float(input_cost) * 1e6,
                "output_per_mtok": float(rec.get("output_cost_per_token") or 0.0) * 1e6,
                "context_window": int(context),
            }
        except (TypeError, ValueError):
            continue  # e.g. LiteLLM's "sample_spec" docstring entry

    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps({"fetched_at": time.time(), "models": models}, indent=1, sort_keys=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(blob, encoding="utf-8")
        os.replace(tmp, path)  # atomic on POSIX and Windows
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return len(models)


def _resolve_cached(key: str) -> ModelSpec | None:
    """Find a cached remote model, tolerating 'provider/name' prefixes."""
    cached = _load_cache()
    lowered = {name.lower(): spec for name, spec in cached.items()}
    if key in lowered:
        return lowered[key]
    short = key.rsplit("/", 1)[-1]
    for name in sorted(lowered):
        if name.rsplit("/", 1)[-1] == short:
            return lowered[name]
    return None


def _all_models() -> dict[str, ModelSpec]:
    merged = dict(_load_cache())  # copy: never mutate the memoized dict
    merged.update(MODELS)  # bundled curation wins on name collisions
    return merged


def resolve_model(name: str) -> ModelSpec:
    """Case-insensitive, alias-aware lookup. Raise ValueError listing available models."""
    key = name.strip().lower()
    canonical = key if key in MODELS else ALIASES.get(key)
    if canonical is not None:
        return MODELS[canonical]
    spec = _resolve_cached(key)
    if spec is not None:
        return spec
    names = list_models()
    if len(names) > _MAX_ERROR_NAMES:
        # Thousands of remote entries would spam stderr; show a prefix instead.
        listing = ", ".join(names[:_MAX_ERROR_NAMES]) + (
            f" ... and {len(names) - _MAX_ERROR_NAMES} more"
            " — run `prompt-flamegraph --list-models`"
        )
    else:
        listing = ", ".join(names)
    raise ValueError(f"Unknown model: {name!r}. Available models: {listing}")


def list_models() -> list[str]:
    """Return the sorted list of model names (bundled + cached remote)."""
    return sorted(set(MODELS) | set(_load_cache()))


def cache_age_days() -> float | None:
    """Age of the remote-pricing cache in days, or None if absent/offline.

    Prefers the ``fetched_at`` timestamp stored inside the cache JSON;
    falls back to the file mtime when it is missing or bogus.
    """
    if _offline():
        return None
    path = _cache_path()
    try:
        stat = path.stat()
    except OSError:
        return None
    _load_cache()  # refreshes _cache_memo for this file if it changed
    key = (str(path), stat.st_mtime, stat.st_size)
    fetched = _cache_memo["fetched_at"] if _cache_memo["key"] == key else None
    if not isinstance(fetched, (int, float)) or not math.isfinite(fetched) or fetched <= 0:
        fetched = stat.st_mtime
    return max(0.0, (time.time() - fetched) / 86400)
