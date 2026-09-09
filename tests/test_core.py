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

import json
from pathlib import Path

import pytest

from prompt_flamegraph.core import Node, build_tree, count_tokens, get_tokenizer, profile_prompt


def test_build_tree_flat_string():
    tree = build_tree("hello world", name="prompt")
    assert tree.name == "prompt"
    assert tree.tokens > 0
    assert tree.is_leaf


def test_build_tree_nested_dict():
    data = {
        "system_prompt": "You are an assistant.",
        "tools": [
            {"name": "read_file", "description": "Read a file."},
            {"name": "run_command", "description": "Run a shell command."},
        ],
    }
    tree = build_tree(data)
    assert tree.name == "prompt"
    assert tree.tokens == sum(c.tokens for c in tree.children)
    assert {c.name for c in tree.children} == {"system_prompt", "tools"}


def test_build_tree_lists():
    data = ["alpha", "beta", "gamma"]
    tree = build_tree(data, name="list")
    assert tree.name == "list"
    assert len(tree.children) == 3
    assert tree.tokens == sum(c.tokens for c in tree.children)


def test_count_tokens_returns_positive():
    assert count_tokens("hello world") > 0


def test_get_tokenizer_callable():
    def my_tokenizer(text: str) -> int:
        return len(text) // 4

    tok = get_tokenizer(my_tokenizer)
    assert tok("abcd") == 1


def test_profile_prompt_writes_html(tmp_path: Path):
    data = {
        "system_prompt": "System",
        "history": ["hi", "hello"],
    }
    out = tmp_path / "out.html"
    html = profile_prompt(data, output=str(out), title="Test")
    assert out.exists()
    assert html.startswith("<!DOCTYPE html>")
    assert "System" in html or "system" in html


def test_profile_prompt_cost(tmp_path: Path):
    data = {"system_prompt": "system text" * 50, "history": ["hello"]}
    out = tmp_path / "cost.html"
    profile_prompt(data, output=str(out), cost_per_token=2e-6)
    content = out.read_text(encoding="utf-8")
    assert "cost" in content.lower() or "$" in content
