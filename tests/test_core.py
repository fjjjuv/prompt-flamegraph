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
from pathlib import Path

import pytest

from prompt_flamegraph.core import (
    Node,
    build_tree,
    count_tokens,
    flatten_tree,
    get_tokenizer,
    profile_prompt,
)


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


def _nested(depth: int):
    data = current = {}
    for _ in range(depth):
        child: dict = {}
        current["x"] = child
        current = child
    current["leaf"] = "end"
    return data


def test_build_tree_deep_nesting_raises_valueerror():
    data = _nested(600)
    with pytest.raises(ValueError, match="deeper than 500"):
        build_tree(data)


def test_build_tree_moderate_depth_ok():
    tree = build_tree(_nested(400))
    assert tree.tokens > 0
    node = tree
    depth = 0
    while node.children:
        node = node.children[0]
        depth += 1
    assert depth == 401


def test_build_tree_circular_dict():
    data: dict = {"a": "x"}
    data["self"] = data
    with pytest.raises(ValueError, match="circular reference"):
        build_tree(data)


def test_build_tree_circular_list():
    data: list = ["x"]
    data.append(data)
    with pytest.raises(ValueError, match="circular reference"):
        build_tree(data)


def test_build_tree_shared_subtree_not_a_cycle():
    shared = {"k": "v"}
    tree = build_tree({"a": shared, "b": shared})
    assert tree.children[0].tokens == tree.children[1].tokens > 0
    assert tree.tokens == tree.children[0].tokens + tree.children[1].tokens


def test_build_tree_unserializable_leaves():
    class Custom:
        def __str__(self):
            return "custom-object"

    tree = build_tree({"blob": b"\x00\x01", "tags": {"a", "b"}, "obj": Custom()})
    leaves = {n.name: n for n in flatten_tree(tree) if n.is_leaf}
    assert leaves["blob"].tokens > 0
    assert leaves["obj"].text == "custom-object"
    assert isinstance(leaves["tags"].text, str)


def test_flatten_tree_iterative_deep():
    root = node = Node(name="n0", tokens=0)
    for i in range(1, 3000):
        child = Node(name=f"n{i}", tokens=i, text="x")
        node.children.append(child)
        node = child
    flat = flatten_tree(root)
    assert len(flat) == 3000
    assert flat[-1].name == "n2999"


def test_get_tokenizer_rejects_non_str():
    for bad in (123, ["x"], b"words", 4.5):
        with pytest.raises(TypeError):
            get_tokenizer(bad)


def test_get_tokenizer_model_prefix_case_insensitive():
    # "estimate" encoding model: works without tiktoken, proves the prefix matched.
    tok = get_tokenizer("Model:claude-sonnet-4")
    assert tok("hello world") > 0


def test_build_tree_model_kwarg_estimate():
    tree = build_tree({"system_prompt": "hello world"}, model="claude-sonnet-4")
    assert tree.tokens > 0


def test_build_tree_model_and_tokenizer_conflict():
    with pytest.raises(ValueError, match="mutually exclusive"):
        build_tree("x", model="gpt-4o", tokenizer="words")


@pytest.mark.skipif(
    importlib.util.find_spec("tiktoken") is not None,
    reason="tiktoken installed; no fallback warning expected",
)
def test_build_tree_model_falls_back_without_tiktoken():
    with pytest.warns(UserWarning, match="default estimator"):
        tree = build_tree({"s": "hello world"}, model="gpt-4o")
    assert tree.tokens > 0


def test_profile_prompt_model_kwarg(tmp_path: Path):
    out = tmp_path / "model.html"
    html = profile_prompt(
        {"system_prompt": "hello world"}, output=str(out), model="claude-sonnet-4"
    )
    assert html.startswith("<!DOCTYPE html>")
    assert out.exists()


def test_profile_prompt_model_and_tokenizer_conflict():
    with pytest.raises(ValueError, match="mutually exclusive"):
        profile_prompt("x", output=None, model="gpt-4o", tokenizer="words")


def test_guess_name_nested_function_tool():
    data = {
        "tools": [
            {"type": "function", "function": {"name": "read_file", "parameters": {}}},
        ]
    }
    tree = build_tree(data)
    tools = next(c for c in tree.children if c.name == "tools")
    assert tools.children[0].name == "read_file"


def test_build_tree_non_str_dict_keys_coerced():
    data = {None: "a", 1: "b", b"k": "c", (1, 2): "d"}
    tree = build_tree(data)
    names = {c.name for c in tree.children}
    assert names == {"None", "1", "b'k'", "(1, 2)"}
    assert all(isinstance(n.name, str) for n in flatten_tree(tree))


def test_build_tree_tokenizer_non_numeric_raises():
    for bad in ("many", None, [1], {"n": 1}):
        with pytest.raises(TypeError, match="tokenizer returned"):
            build_tree("hi", tokenizer=lambda t, _b=bad: _b)


def test_build_tree_tokenizer_negative_clamped_to_zero():
    tree = build_tree("hi there", tokenizer=lambda t: -5)
    assert tree.tokens == 0


def test_build_tree_tokenizer_float_truncated():
    tree = build_tree("hi there", tokenizer=lambda t: 3.9)
    assert tree.tokens == 3


def test_to_text_bytes_decodes_utf8():
    tree = build_tree({"blob": b"hello"})
    assert tree.children[0].text == "hello"


def test_to_text_bytes_invalid_utf8_replaced():
    tree = build_tree({"blob": b"\xff\xfe"})
    assert "\ufffd" in tree.children[0].text


def test_to_text_set_deterministic():
    tree = build_tree({"tags": {"b", "a"}})
    assert tree.children[0].text == json.dumps(["'a'", "'b'"])


def test_get_tokenizer_strips_and_lowercases_name():
    tok = get_tokenizer("  WORDS ")
    assert tok("hello world") > 0


def test_get_tokenizer_rejects_encoding_typos():
    for bad in ("o200k_typo", "cl100k_extra", "o200k_bases", "cl100kbase"):
        with pytest.raises(ValueError, match="Unknown tokenizer"):
            get_tokenizer(bad)


def test_load_tiktoken_unknown_encoding_raises_valueerror(monkeypatch):
    import sys
    import types

    from prompt_flamegraph.core import _load_tiktoken

    fake = types.ModuleType("tiktoken")

    def get_encoding(name):
        raise ValueError(f"fake: no such encoding {name}")

    fake.get_encoding = get_encoding
    monkeypatch.setitem(sys.modules, "tiktoken", fake)
    with pytest.raises(ValueError, match="unknown tiktoken encoding"):
        _load_tiktoken("bogus_encoding")


def test_node_repr_compact():
    node = Node(name="root", tokens=42, children=[Node(name="c", tokens=1)])
    assert repr(node) == "Node(name='root', tokens=42, children=1)"
    assert "children=[" not in repr(node)


def test_node_repr_shows_change():
    node = Node(name="n", tokens=1, change="added")
    assert repr(node) == "Node(name='n', tokens=1, children=0, change='added')"
