# prompt-flamegraph - Lightweight prompt context flamegraph generator for LLMs.
# Copyright (C) 2025  fjjjuv
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
