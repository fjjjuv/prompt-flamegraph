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

import pytest

from prompt_flamegraph.core import build_tree, get_tokenizer
from prompt_flamegraph.models import ALIASES, MODELS, list_models, resolve_model
from prompt_flamegraph.waste import detect_waste

HAS_TIKTOKEN = importlib.util.find_spec("tiktoken") is not None


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
