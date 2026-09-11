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

import importlib.util
import json
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
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode()

    def read(self):
        return self._raw

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
