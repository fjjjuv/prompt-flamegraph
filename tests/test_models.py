# prompt-flamegraph - Lightweight prompt context flamegraph generator for LLMs.
# Copyright (C) 2026  fjjjuv
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import importlib.util
import json
import time
import urllib.error
import urllib.request

import pytest

from prompt_flamegraph.core import build_tree, get_tokenizer
from prompt_flamegraph.models import (
    ALIASES,
    MODELS,
    cache_age_days,
    list_models,
    resolve_model,
    update_models,
)
from prompt_flamegraph.waste import detect_waste

HAS_TIKTOKEN = importlib.util.find_spec("tiktoken") is not None

FAKE_LITELLM = {
    "remote-sonnet-x": {
        "input_cost_per_token": 3e-6,
        "output_cost_per_token": 15e-6,
        "max_input_tokens": 200_000,
        "litellm_provider": "anthropic",
    },
    "openai/o9-remote": {
        "input_cost_per_token": 1e-6,
        "output_cost_per_token": 2e-6,
        "max_tokens": 64_000,
        "litellm_provider": "openai",
    },
    "gpt-4o": {  # duplicate of a bundled model: the bundled spec must win
        "input_cost_per_token": 9.9e-6,
        "output_cost_per_token": 9.9e-6,
        "max_input_tokens": 128_000,
        "litellm_provider": "openai",
    },
    "legacy-gpt-3.5": {
        "input_cost_per_token": 5e-7,
        "output_cost_per_token": 1.5e-6,
        "max_tokens": 16_385,
        "litellm_provider": "openai",
    },
    "no-price": {"max_tokens": 8_000, "litellm_provider": "openai"},
    "no-context": {"input_cost_per_token": 1e-6, "litellm_provider": "openai"},
    "sample_spec": "not-a-dict",
}


def test_resolve_model_exact():
    spec = resolve_model("gpt-4o")
    assert spec.name == "gpt-4o"
    assert spec.encoding == "o200k_base"


def test_resolve_model_alias():
    assert resolve_model("4o").name == "gpt-4o"
    assert resolve_model("sonnet").name == "claude-sonnet-4"
    assert resolve_model("opus").name == "claude-opus-4.1"


def test_resolve_model_case_insensitive():
    assert resolve_model("GPT-4O").name == "gpt-4o"
    assert resolve_model("Sonnet").name == "claude-sonnet-4"
    assert resolve_model("  Gpt-4.1-Nano  ").name == "gpt-4.1-nano"


def test_resolve_model_unknown_raises():
    with pytest.raises(ValueError) as exc:
        resolve_model("not-a-model")
    assert "gpt-4o" in str(exc.value)
    assert "claude-sonnet-4" in str(exc.value)


def test_models_table_sane():
    for name, spec in MODELS.items():
        assert spec.name == name
        assert spec.encoding in ("cl100k_base", "o200k_base", "estimate")
        assert spec.input_per_mtok > 0
        assert spec.output_per_mtok > 0
        assert spec.context_window >= 8_000


def test_aliases_point_at_real_models():
    for alias, canonical in ALIASES.items():
        assert canonical in MODELS
        assert alias != canonical


def test_list_models():
    names = list_models()
    assert names == sorted(MODELS)
    assert "gpt-4o" in names


def test_get_tokenizer_model_estimate_no_tiktoken():
    # Non-OpenAI models use the estimator and never need tiktoken.
    tok = get_tokenizer("model:claude-sonnet-4")
    assert tok("hello world") == 2


def test_get_tokenizer_model_unknown():
    with pytest.raises(ValueError):
        get_tokenizer("model:bogus")


def test_get_tokenizer_model_tiktoken_encoding():
    pytest.importorskip("tiktoken")
    tok = get_tokenizer("model:gpt-4o")
    assert tok("hello world") == 2


def test_get_tokenizer_model_tiktoken_missing():
    if HAS_TIKTOKEN:
        pytest.skip("tiktoken installed")
    with pytest.raises(ImportError, match="tiktoken"):
        get_tokenizer("model:gpt-4o")


def test_get_tokenizer_o200k():
    pytest.importorskip("tiktoken")
    assert get_tokenizer("o200k")("hello world") == 2
    assert get_tokenizer("o200k_base")("hello world") == 2


def test_detect_waste_context_window():
    data = {"system_prompt": "a " * 450}
    tree = build_tree(data)

    report = detect_waste(tree, context_window=500)
    findings = [f for f in report.findings if f.kind == "context_window"]
    assert len(findings) == 1
    assert "90.0%" in findings[0].message
    assert "500" in findings[0].message
    assert findings[0].tokens_wasted == 0

    report = detect_waste(tree, context_window=100_000)
    assert not any(f.kind == "context_window" for f in report.findings)

    report = detect_waste(tree)
    assert not any(f.kind == "context_window" for f in report.findings)


def test_detect_waste_context_window_critical():
    data = {"system_prompt": "a " * 450}
    tree = build_tree(data)
    report = detect_waste(tree, context_window=460)
    finding = next(f for f in report.findings if f.kind == "context_window")
    assert "truncation" in finding.message


def test_detect_waste_near_duplicate_whitespace_case():
    data = {
        "doc_a": "Hello   World, this is a Test!",
        "doc_b": "hello world this is a test",
    }
    tree = build_tree(data)
    report = detect_waste(tree)
    assert any(f.kind == "near_duplicate" for f in report.findings)
    assert not any(f.kind == "duplicate" for f in report.findings)


class _FakeResponse:
    def __init__(self, payload, headers=None):
        self._raw = json.dumps(payload).encode()
        self.headers = headers or {}

    def read(self, n=-1):
        return self._raw if n is None or n < 0 else self._raw[:n]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def fake_litellm(monkeypatch, tmp_path):
    """Redirect the model cache to tmp_path and stub the network fetch."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("PROMPT_FLAMEGRAPH_OFFLINE", raising=False)
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=0: _FakeResponse(FAKE_LITELLM)
    )
    return tmp_path / "prompt-flamegraph" / "models.json"


def test_update_models_writes_cache(fake_litellm):
    assert update_models() == 4
    data = json.loads(fake_litellm.read_text(encoding="utf-8"))
    assert data["fetched_at"] > 0
    assert "no-price" not in data["models"]
    assert "no-context" not in data["models"]
    assert "sample_spec" not in data["models"]
    spec = data["models"]["remote-sonnet-x"]
    assert spec["encoding"] == "estimate"
    assert spec["input_per_mtok"] == pytest.approx(3.0)
    assert spec["output_per_mtok"] == pytest.approx(15.0)
    assert spec["context_window"] == 200_000
    assert data["models"]["openai/o9-remote"]["encoding"] == "o200k_base"
    assert data["models"]["legacy-gpt-3.5"]["encoding"] == "cl100k_base"


def test_resolve_remote_only_model(fake_litellm):
    update_models()
    spec = resolve_model("remote-sonnet-x")
    assert spec.name == "remote-sonnet-x"
    assert spec.encoding == "estimate"
    assert spec.input_per_mtok == pytest.approx(3.0)
    assert spec.context_window == 200_000


def test_resolve_remote_provider_prefix(fake_litellm):
    update_models()
    assert resolve_model("o9-remote").name == "openai/o9-remote"
    assert resolve_model("OPENAI/O9-REMOTE").name == "openai/o9-remote"


def test_bundled_beats_remote_duplicate(fake_litellm):
    update_models()
    assert resolve_model("gpt-4o").input_per_mtok == pytest.approx(2.50)


def test_list_models_includes_remote(fake_litellm):
    update_models()
    names = list_models()
    assert "remote-sonnet-x" in names
    assert "openai/o9-remote" in names
    assert "gpt-4o" in names
    assert names == sorted(names)


def test_corrupt_cache_ignored(fake_litellm):
    fake_litellm.parent.mkdir(parents=True, exist_ok=True)
    fake_litellm.write_text("{ not json !!!", encoding="utf-8")
    assert list_models() == sorted(MODELS)
    assert resolve_model("gpt-4o").name == "gpt-4o"
    with pytest.raises(ValueError):
        resolve_model("remote-sonnet-x")


def test_offline_hides_remote(fake_litellm, monkeypatch):
    update_models()
    monkeypatch.setenv("PROMPT_FLAMEGRAPH_OFFLINE", "1")
    assert list_models() == sorted(MODELS)
    with pytest.raises(ValueError):
        resolve_model("remote-sonnet-x")
    assert cache_age_days() is None
    with pytest.raises(RuntimeError):
        update_models()


def test_cache_age_days(fake_litellm):
    assert cache_age_days() is None
    update_models()
    age = cache_age_days()
    assert age is not None and 0 <= age < 1


def test_lookups_never_touch_network(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("PROMPT_FLAMEGRAPH_OFFLINE", raising=False)

    def _boom(req, timeout=0):
        raise AssertionError("network access")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    assert resolve_model("gpt-4o").name == "gpt-4o"
    assert list_models() == sorted(MODELS)


def _write_cache(path, models, fetched_at=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"models": models}
    if fetched_at is not None:
        doc["fetched_at"] = fetched_at
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_load_cache_memoized(fake_litellm, monkeypatch):
    update_models()
    calls = []
    real_loads = json.loads

    def _spy(text, *args, **kwargs):
        calls.append(text)
        return real_loads(text, *args, **kwargs)

    monkeypatch.setattr(json, "loads", _spy)
    assert resolve_model("remote-sonnet-x").name == "remote-sonnet-x"
    assert resolve_model("remote-sonnet-x").name == "remote-sonnet-x"
    assert "remote-sonnet-x" in list_models()
    assert len(calls) == 1  # second lookup and list_models hit the memo


def test_load_cache_invalidates_on_change(fake_litellm):
    update_models()
    assert resolve_model("remote-sonnet-x").name == "remote-sonnet-x"
    data = json.loads(fake_litellm.read_text(encoding="utf-8"))
    data["models"]["swapped-in"] = {
        "encoding": "estimate",
        "input_per_mtok": 1.0,
        "output_per_mtok": 2.0,
        "context_window": 32_000,
    }
    fake_litellm.write_text(json.dumps(data, indent=1), encoding="utf-8")
    assert resolve_model("swapped-in").name == "swapped-in"


def test_update_models_atomic_write(fake_litellm):
    update_models()
    assert fake_litellm.exists()
    assert list(fake_litellm.parent.glob("*.tmp")) == []


def test_o200k_names_anchored(fake_litellm, monkeypatch):
    payload = dict(FAKE_LITELLM)
    payload["gpto4"] = {  # 'o4' embedded in a word: must NOT match o200k
        "input_cost_per_token": 1e-6,
        "output_cost_per_token": 2e-6,
        "max_tokens": 8_000,
        "litellm_provider": "openai",
    }
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=0: _FakeResponse(payload)
    )
    update_models()
    assert resolve_model("gpto4").encoding == "cl100k_base"
    assert resolve_model("o9-remote").encoding == "o200k_base"  # 'o9' still hits


def test_error_message_truncated(fake_litellm, monkeypatch):
    payload = {
        f"remote-{i:04d}": {"input_cost_per_token": 1e-6, "max_tokens": 8_000}
        for i in range(200)
    }
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=0: _FakeResponse(payload)
    )
    update_models()
    with pytest.raises(ValueError) as exc:
        resolve_model("zzz-missing")
    msg = str(exc.value)
    assert len(msg) < 2048
    assert "more" in msg and "--list-models" in msg
    assert "remote-0199" not in msg


def test_update_models_network_errors(fake_litellm, monkeypatch):
    def _url_error(req, timeout=0):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(urllib.request, "urlopen", _url_error)
    with pytest.raises(RuntimeError, match="failed to fetch pricing data"):
        update_models()

    def _timeout(req, timeout=0):
        raise TimeoutError("timed out")

    monkeypatch.setattr(urllib.request, "urlopen", _timeout)
    with pytest.raises(RuntimeError, match="failed to fetch pricing data"):
        update_models()


def test_update_models_refuses_huge_declared(fake_litellm, monkeypatch):
    class _Big:
        headers = {"Content-Length": str(60_000_000)}

        def read(self, n=-1):
            raise AssertionError("should not read an oversized payload")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: _Big())
    with pytest.raises(ValueError, match="too large"):
        update_models()


def test_update_models_refuses_huge_body(fake_litellm, monkeypatch):
    import prompt_flamegraph.models as models_mod

    monkeypatch.setattr(models_mod, "_MAX_PAYLOAD", 64)
    with pytest.raises(ValueError, match="exceeds"):
        update_models()


def test_sanitize_strips_ansi(fake_litellm):
    _write_cache(
        fake_litellm,
        {
            "\x1b[31mevil-name\x1b[0m": {
                "encoding": "estimate",
                "input_per_mtok": 1.0,
                "output_per_mtok": 2.0,
                "context_window": 32_000,
            },
        },
        fetched_at=time.time(),
    )
    spec = resolve_model("evil-name")
    assert spec.name == "evil-name"
    assert "\x1b" not in spec.name


def test_sanitize_skips_bad_entries(fake_litellm):
    good = {
        "encoding": "estimate",
        "input_per_mtok": 1.0,
        "output_per_mtok": 2.0,
        "context_window": 32_000,
    }
    _write_cache(
        fake_litellm,
        {
            "good-one": dict(good),
            "neg-ctx": dict(good, context_window=-5),
            "zero-ctx": dict(good, context_window=0),
            "nan-price": dict(good, input_per_mtok=float("nan")),
            "inf-price": dict(good, output_per_mtok=float("inf")),
            "missing-ctx": {"encoding": "estimate", "input_per_mtok": 1.0},
            "\x00\x01\x02": dict(good),  # sanitizes to "" -> skipped
            "long-name-" + "x" * 200: dict(good),
        },
        fetched_at=time.time(),
    )
    names = list_models()
    remote_names = set(names) - set(MODELS)
    long_name = next(n for n in names if n.startswith("long-name"))
    assert len(long_name) <= 128
    assert remote_names == {"good-one", long_name}


def test_cache_age_uses_fetched_at(fake_litellm):
    _write_cache(fake_litellm, {}, fetched_at=time.time() - 10 * 86400)
    age = cache_age_days()
    assert age is not None and 9 < age < 11


def test_cache_age_falls_back_to_mtime(fake_litellm):
    _write_cache(fake_litellm, {})  # no fetched_at key
    age = cache_age_days()
    assert age is not None and age < 1


def test_cache_age_none_after_delete(fake_litellm):
    update_models()
    assert cache_age_days() is not None
    fake_litellm.unlink()
    assert cache_age_days() is None


def test_sanitize_rejects_negative_prices(fake_litellm):
    base = {
        "encoding": "estimate",
        "input_per_mtok": 1.0,
        "output_per_mtok": 2.0,
        "context_window": 32_000,
    }
    _write_cache(
        fake_litellm,
        {
            "free-model": dict(base, input_per_mtok=0.0, output_per_mtok=0.0),
            "neg-input": dict(base, input_per_mtok=-1.0),
            "neg-output": dict(base, output_per_mtok=-0.5),
        },
        fetched_at=time.time(),
    )
    remote = set(list_models()) - set(MODELS)
    assert remote == {"free-model"}


def test_sanitize_encoding_validated(fake_litellm):
    base = {"input_per_mtok": 1.0, "output_per_mtok": 2.0, "context_window": 32_000}
    _write_cache(
        fake_litellm,
        {
            "enc-missing": dict(base),
            "enc-none": dict(base, encoding=None),
            "enc-blank": dict(base, encoding="   "),
            "enc-padded": dict(base, encoding=" cl100k_base "),
            "enc-bogus": dict(base, encoding="rot13"),
            "enc-nonstr": dict(base, encoding=42),
        },
        fetched_at=time.time(),
    )
    assert resolve_model("enc-missing").encoding == "estimate"
    assert resolve_model("enc-none").encoding == "estimate"
    assert resolve_model("enc-blank").encoding == "estimate"
    assert resolve_model("enc-padded").encoding == "cl100k_base"
    remote = set(list_models()) - set(MODELS)
    assert "enc-bogus" not in remote
    assert "enc-nonstr" not in remote


def test_update_models_malformed_payload(fake_litellm, monkeypatch):
    class _Raw:
        def __init__(self, raw):
            self._raw = raw
            self.headers = {}

        def read(self, n=-1):
            return self._raw if n is None or n < 0 else self._raw[:n]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=0: _Raw(b"{ not json !!!")
    )
    with pytest.raises(RuntimeError, match="failed to parse pricing data"):
        update_models()

    monkeypatch.setattr(
        urllib.request, "urlopen", lambda req, timeout=0: _Raw(b"\xff\xfe not utf-8")
    )
    with pytest.raises(RuntimeError, match="failed to parse pricing data"):
        update_models()


def test_update_models_leaves_tmp_symlink_alone(fake_litellm):
    # A planted "models.json.tmp" symlink must not be followed or clobbered.
    fake_litellm.parent.mkdir(parents=True)
    decoy_target = fake_litellm.parent.parent / "decoy.txt"
    decoy = fake_litellm.parent / "models.json.tmp"
    decoy.symlink_to(decoy_target)
    assert update_models() == 4
    assert decoy.is_symlink()
    assert not decoy_target.exists()
    assert json.loads(fake_litellm.read_text(encoding="utf-8"))["models"]


def test_update_models_requires_https(fake_litellm, monkeypatch):
    calls = []

    def _spy(req, timeout=0):
        calls.append(req.full_url)
        return _FakeResponse(FAKE_LITELLM)

    monkeypatch.setattr(urllib.request, "urlopen", _spy)
    for bad in ("http://example.com/m.json", "file:///etc/passwd", "ftp://x/y"):
        with pytest.raises(ValueError, match="https"):
            update_models(url=bad)
    assert calls == []


def test_update_models_redirect_schemes(fake_litellm, monkeypatch):
    class _Redirected(_FakeResponse):
        def __init__(self, payload, final_url):
            super().__init__(payload)
            self._final_url = final_url

        def geturl(self):
            return self._final_url

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=0: _Redirected(FAKE_LITELLM, "http://evil.example/p.json"),
    )
    with pytest.raises(ValueError, match="redirected"):
        update_models()

    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=0: _Redirected(FAKE_LITELLM, "https://cdn.example.com/p.json"),
    )
    assert update_models() == 4


def test_cache_path_expands_xdg_home(monkeypatch):
    from pathlib import Path

    import prompt_flamegraph.models as models_mod

    monkeypatch.setenv("XDG_CACHE_HOME", "~/pf-cache")
    assert models_mod._cache_path() == (
        Path.home() / "pf-cache" / "prompt-flamegraph" / "models.json"
    )


def test_cache_path_home_fallback(monkeypatch):
    import tempfile
    from pathlib import Path

    import prompt_flamegraph.models as models_mod

    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)

    def _no_home():
        raise RuntimeError("no home directory")

    monkeypatch.setattr(Path, "home", staticmethod(_no_home))
    assert models_mod._cache_path() == (
        Path(tempfile.gettempdir()) / "prompt-flamegraph" / "models.json"
    )


def test_resolve_model_long_name_truncated():
    with pytest.raises(ValueError) as exc:
        resolve_model("z" * 5_000)
    msg = str(exc.value)
    assert len(msg) <= 2_000
    assert "z" * 5_000 not in msg


def test_resolve_model_error_message_capped(fake_litellm):
    # 15 names of ~120 chars plus boilerplate would exceed the cap.
    models = {
        f"m{i:02d}-" + "x" * 120: {
            "encoding": "estimate",
            "input_per_mtok": 1.0,
            "output_per_mtok": 2.0,
            "context_window": 8_000,
        }
        for i in range(30)
    }
    _write_cache(fake_litellm, models, fetched_at=time.time())
    with pytest.raises(ValueError) as exc:
        resolve_model("missing-model")
    assert len(str(exc.value)) <= 2_000


def test_list_models_dedupes_case(fake_litellm):
    _write_cache(
        fake_litellm,
        {
            "GPT-4O": {  # case-only duplicate of a bundled name: bundled wins
                "encoding": "o200k_base",
                "input_per_mtok": 9.9,
                "output_per_mtok": 9.9,
                "context_window": 128_000,
            },
            "Remote-Only-X": {
                "encoding": "estimate",
                "input_per_mtok": 1.0,
                "output_per_mtok": 2.0,
                "context_window": 32_000,
            },
        },
        fetched_at=time.time(),
    )
    names = list_models()
    assert names.count("gpt-4o") == 1
    assert "GPT-4O" not in names
    assert "Remote-Only-X" in names
