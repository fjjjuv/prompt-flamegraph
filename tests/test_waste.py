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

from prompt_flamegraph.core import build_tree
from prompt_flamegraph.waste import detect_waste


def test_detect_waste_duplicate_text():
    data = {
        "system_prompt": "hello world",
        "rag_context": {
            "doc_1": "hello world",
            "doc_2": "hello world",
        },
    }
    tree = build_tree(data)
    report = detect_waste(tree)
    assert any(f.kind == "duplicate" for f in report.findings)
    assert report.wasted_tokens > 0


def test_detect_waste_huge_rag():
    data = {
        "rag_context": {"x": "a " * 500},
        "system_prompt": "short",
    }
    tree = build_tree(data)
    report = detect_waste(tree)
    assert any(f.kind == "huge_rag" for f in report.findings)


def test_no_waste_on_clean_prompt():
    data = {
        "system_prompt": "Be helpful.",
        "history": ["hi"],
    }
    tree = build_tree(data)
    report = detect_waste(tree)
    assert not any(f.kind == "duplicate" for f in report.findings)


def test_detect_waste_near_duplicate_shingles():
    base = " ".join(f"word{i}" for i in range(30))
    other = " ".join(f"word{i}" for i in range(29)) + " changed"
    data = {"doc_1": base, "doc_2": other, "doc_3": "completely unrelated text here"}
    tree = build_tree(data)
    report = detect_waste(tree)
    findings = [f for f in report.findings if f.kind == "near_duplicate"]
    assert len(findings) == 1
    assert findings[0].tokens_wasted > 0
    assert "doc_3" not in findings[0].path


def test_detect_waste_context_window():
    data = {"system_prompt": "a " * 450}
    tree = build_tree(data)

    report = detect_waste(tree, context_window=500)
    assert any(f.kind == "context_window" for f in report.findings)

    report = detect_waste(tree, context_window=10_000)
    assert not any(f.kind == "context_window" for f in report.findings)


def test_wasted_tokens_never_exceeds_total():
    # Regression: leaves already counted as wasted by exact duplicates must not
    # be counted again by near-duplicate detection (wasted used to exceed total).
    data = {
        "a": "foo bar",
        "b": "foo bar",
        "c": "foo bar",
        "d": " foo bar ",
    }
    tree = build_tree(data)
    report = detect_waste(tree)

    dups = [f for f in report.findings if f.kind == "duplicate"]
    nears = [f for f in report.findings if f.kind == "near_duplicate"]
    assert len(dups) == 1
    assert dups[0].message.startswith("3×")
    # Only the kept leaf c plus variant d form the near-duplicate group.
    assert len(nears) == 1
    assert nears[0].message.startswith("2×")
    assert 0 < report.wasted_tokens <= report.total_tokens


def test_near_duplicate_found_despite_exact_duplicate():
    # Regression: an exact-duplicate group must not suppress shingle-based
    # near-duplicate detection for other similar leaves.
    base = " ".join(f"word{i}" for i in range(30))
    near = " ".join(f"word{i}" for i in range(29)) + " changed"
    data = {"doc_1": base, "doc_2": base, "doc_3": near}
    tree = build_tree(data)
    report = detect_waste(tree)

    assert any(f.kind == "duplicate" for f in report.findings)
    nears = [f for f in report.findings if f.kind == "near_duplicate"]
    assert len(nears) == 1
    assert "doc_3" in nears[0].path


def test_near_duplicate_found_beside_normalized_group():
    # Regression: one member of a normalized (whitespace/case) duplicate group
    # stays a shingle candidate so near-duplicates of the group are still found.
    base = " ".join(f"word{i}" for i in range(30))
    variant = " ".join(f"WORD{i}" for i in range(30))  # identical after normalize
    near = " ".join(f"word{i}" for i in range(29)) + " changed"
    data = {"doc_1": base, "doc_2": variant, "doc_3": near}
    tree = build_tree(data)
    report = detect_waste(tree)

    nears = [f for f in report.findings if f.kind == "near_duplicate"]
    assert any("doc_3" in f.path for f in nears)
    assert report.wasted_tokens <= report.total_tokens


def test_category_match_is_case_insensitive():
    # Regression: category names like "System_Prompt" must be caught.
    tree = build_tree({"System_Prompt": "a " * 400, "misc": "x"})
    assert any(f.kind == "large_system_prompt" for f in detect_waste(tree).findings)

    tree = build_tree({"Chat_History": "a " * 400, "misc": "x"})
    assert any(f.kind == "long_history" for f in detect_waste(tree).findings)

    tree = build_tree({"Tools": {f"tool_{i}": "does x" for i in range(6)}})
    assert any(f.kind == "too_many_tools" for f in detect_waste(tree).findings)

    tree = build_tree({"RAG_Context": "a " * 500, "misc": "x"})
    assert any(f.kind == "huge_rag" for f in detect_waste(tree).findings)


def test_near_duplicate_skip_is_reported_over_leaf_limit():
    # Regression: skipping the n-gram pass over _NGRAM_MAX_LEAVES must surface
    # a finding instead of being silent.
    data = {f"leaf_{i}": f"unique text number {i}" for i in range(301)}
    tree = build_tree(data)
    report = detect_waste(tree)
    skipped = [f for f in report.findings if f.kind == "near_duplicate_skipped"]
    assert len(skipped) == 1
    assert skipped[0].tokens_wasted == 0
    assert "301" in skipped[0].message

    data = {f"leaf_{i}": f"unique text number {i}" for i in range(300)}
    tree = build_tree(data)
    report = detect_waste(tree)
    assert not any(f.kind == "near_duplicate_skipped" for f in report.findings)
