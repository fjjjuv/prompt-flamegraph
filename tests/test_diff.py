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

import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from prompt_flamegraph.core import Node, build_tree
from prompt_flamegraph.diff import build_diff_tree, diff_prompts


def test_build_diff_tree_detects_added():
    v1 = {"system_prompt": "hello", "tools": [{"name": "a"}]}
    v2 = {"system_prompt": "hello", "tools": [{"name": "a"}, {"name": "b"}]}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    assert diff.tokens > 0
    names = {c.name: c.change for c in diff.children}
    assert names.get("tools") in ("changed", "same")


def test_diff_prompts_writes_html():
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "diff.html"
        v1 = {"system_prompt": "hello"}
        v2 = {"system_prompt": "hello", "extra": "world"}
        html = diff_prompts(v1, v2, output=str(out), title="Diff")
        assert out.exists()
        assert "Diff" in html


def test_diff_prompts_renders_changed_nodes():
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "diff.html"
        v1 = {"system_prompt": "hello", "notes": "aaa"}
        v2 = {"system_prompt": "hello", "notes": "bbb", "extra": "brand new"}
        html = diff_prompts(v1, v2, output=str(out))
        # The diff tree must contain the actual nodes, not an empty graph.
        assert "system_prompt" in html
        assert "notes" in html
        assert "extra" in html


def test_build_diff_tree_different_root_names():
    v1 = {"system_prompt": "hello"}
    v2 = {"system_prompt": "hello", "extra": "world"}
    t1 = build_tree(v1, name="v1")
    t2 = build_tree(v2, name="v2")
    diff = build_diff_tree(t1, t2)
    assert diff.name == "diff"
    names = {c.name: c.change for c in diff.children}
    assert names["system_prompt"] == "same"
    assert names["extra"] == "added"


def test_build_diff_tree_same_named_siblings():
    v1 = {
        "chat_history": [
            {"role": "user", "content": "aaa"},
            {"role": "user", "content": "bbb"},
        ]
    }
    v2 = {
        "chat_history": [
            {"role": "user", "content": "aaa"},
            {"role": "user", "content": "ccc ccc ccc ccc"},
        ]
    }
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    history = next(c for c in diff.children if c.name == "chat_history")
    # both "user" siblings must survive the diff, positionally matched
    assert [c.name for c in history.children] == ["user", "user"]
    assert [c.change for c in history.children] == ["same", "changed"]


def test_build_diff_tree_empty_v2_leaf_wins():
    v1 = {"note": "hello world"}
    v2 = {"note": ""}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    note = next(c for c in diff.children if c.name == "note")
    # An emptied v2 leaf must keep its own (falsy) values, not fall back to v1.
    assert note.text == ""
    assert note.tokens == 0
    assert note.change == "changed"


def test_build_diff_tree_leaf_becomes_dict():
    v1 = {"a": "hello"}
    v2 = {"a": {"b": "some text"}}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    node = next(c for c in diff.children if c.name == "a")
    # v2 is internal here: v1's leaf text must not leak onto the node.
    assert node.change == "changed"
    assert node.text is None
    assert [c.name for c in node.children] == ["b"]
    assert node.children[0].change == "added"


def test_build_diff_tree_dict_becomes_leaf():
    v1 = {"a": {"b": "some text"}}
    v2 = {"a": "hello"}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    node = next(c for c in diff.children if c.name == "a")
    # v2 is a leaf here: v1's children must be dropped entirely.
    assert node.change == "changed"
    assert node.text == "hello"
    assert node.children == []


def test_build_diff_tree_sibling_insert_no_cascade():
    v1 = {
        "chat_history": [
            {"role": "user", "content": "aaa"},
            {"role": "user", "content": "bbb bbb"},
        ]
    }
    v2 = {
        "chat_history": [
            {"role": "user", "content": "completely new message here"},
            {"role": "user", "content": "aaa"},
            {"role": "user", "content": "bbb bbb"},
        ]
    }
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    history = next(c for c in diff.children if c.name == "chat_history")
    # Identical messages pair by content, so only the inserted head is added.
    assert [c.name for c in history.children] == ["user", "user", "user"]
    assert [c.change for c in history.children] == ["added", "same", "same"]


def test_build_diff_tree_root_delta():
    v1 = {"a": "one two three"}
    v2 = {"a": "one"}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    assert diff.change is None
    assert diff.delta == t2.tokens - t1.tokens
    # Union view keeps the wider root so removed content stays visible.
    assert diff.tokens == max(t1.tokens, t2.tokens, 1)


def test_build_diff_tree_empty_v2_container_marks_removed():
    v1 = {"a": {"b": "some text", "c": "more text"}}
    v2 = {"a": {}}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    node = next(c for c in diff.children if c.name == "a")
    # An empty v2 container is not a leaf: v1 children stay visible as
    # removed instead of being silently dropped.
    assert node.change == "changed"
    assert node.text is None
    assert [c.name for c in node.children] == ["b", "c"]
    assert [c.change for c in node.children] == ["removed", "removed"]


def test_build_diff_tree_internal_siblings_match_by_shape():
    # Two same-named internal nodes with equal token sums but different
    # child keys must not pair by content.
    v1 = {"items": [{"name": "n", "bb": "y"}, {"name": "n", "aa": "x"}]}
    v2 = {"items": [{"name": "n", "aa": "x"}]}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    items = next(c for c in diff.children if c.name == "items")
    # The kept v2 sibling pairs with the identical-shape v1 sibling; the
    # other is removed near its original position.
    assert [c.name for c in items.children] == ["n", "n"]
    assert [c.change for c in items.children] == ["removed", "same"]
    assert all(c.change == "same" for c in items.children[1].children)


def test_build_diff_tree_deep_change_marks_ancestors():
    v1 = {"a": {"b": "x"}}
    v2 = {"a": {"b": "y"}}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    node = next(c for c in diff.children if c.name == "a")
    # Equal token sums must not hide a changed descendant.
    assert node.change == "changed"
    assert node.children[0].change == "changed"


def test_build_diff_tree_zero_token_added_child_marks_changed():
    v1 = {"a": {"b": "x"}}
    v2 = {"a": {"b": "x", "c": ""}}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    node = next(c for c in diff.children if c.name == "a")
    # An added child that costs no tokens still makes the parent changed.
    assert node.change == "changed"
    assert [c.name for c in node.children] == ["b", "c"]
    assert [c.change for c in node.children] == ["same", "added"]


def test_build_diff_tree_removed_child_keeps_position():
    v1 = {"a": "x", "gone": "y", "b": "z"}
    v2 = {"a": "x", "b": "z"}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    # Removed children interleave near their original position.
    assert [c.name for c in diff.children] == ["a", "gone", "b"]
    assert [c.change for c in diff.children] == ["same", "removed", "same"]


def test_build_diff_tree_depth_guard():
    # Hand-rolled Node trees bypass build_tree's own depth cap.
    node = root = Node(name="deep", tokens=0)
    for i in range(510):
        child = Node(name=f"n{i}", tokens=0)
        node.children.append(child)
        node = child
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(old_limit + 3000)
    try:
        with pytest.raises(ValueError, match="deeper than 500"):
            build_diff_tree(root, Node(name="shallow", tokens=0))
    finally:
        sys.setrecursionlimit(old_limit)
