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

"""Compare two prompt trees and build a diff flamegraph."""

from __future__ import annotations

from typing import Any

from .core import Node


_ChildKey = tuple[str, int]  # (name, index among same-named siblings)
_Path = tuple[_ChildKey, ...]


def _child_keys(node: Node) -> list[_ChildKey]:
    """Positional identity for each child, so same-named siblings stay distinct."""
    counts: dict[str, int] = {}
    keys: list[_ChildKey] = []
    for child in node.children:
        i = counts.get(child.name, 0)
        counts[child.name] = i + 1
        keys.append((child.name, i))
    return keys


def _all_paths(node: Node, path: _Path) -> dict[_Path, tuple[int, str | None, list[_ChildKey]]]:
    """Return a dict path -> (tokens, text, child_keys) for every node."""
    result: dict[_Path, tuple[int, str | None, list[_ChildKey]]] = {}
    stack: list[tuple[Node, _Path]] = [(node, path)]
    while stack:
        current, cur_path = stack.pop()
        keys = _child_keys(current)
        result[cur_path] = (current.tokens, current.text, keys)
        for key, child in zip(keys, current.children):
            stack.append((child, (*cur_path, key)))
    return result


def _pair_child_keys(
    children_v1: list[_ChildKey],
    children_v2: list[_ChildKey],
    path_v1: _Path | None,
    path_v2: _Path | None,
    v1_map: dict,
    v2_map: dict,
) -> list[tuple[_ChildKey | None, _ChildKey | None]]:
    """Match same-named siblings across versions.

    Children with identical (text, tokens) pair up first, so inserting one
    sibling does not cascade "changed" onto its shifted twins; leftovers
    pair positionally. Returns (v1_key, v2_key) pairs - a None side marks
    an added (v2 only) or removed (v1 only) child. Pairs follow v2 order,
    then v1-only keys.
    """
    idxs1: dict[str, list[int]] = {}
    for name, i in children_v1:
        idxs1.setdefault(name, []).append(i)
    idxs2: dict[str, list[int]] = {}
    for name, j in children_v2:
        idxs2.setdefault(name, []).append(j)

    match: dict[tuple[str, int], int] = {}  # (name, v2 idx) -> v1 idx
    used1: dict[str, set[int]] = {}
    for name, js in idxs2.items():
        used = used1.setdefault(name, set())
        # Pass 1: pair identical (text, tokens) content regardless of position.
        for j in js:
            tokens_v2, text_v2, _ = v2_map[(*path_v2, (name, j))]
            for i in idxs1.get(name, []):
                if i in used:
                    continue
                tokens_v1, text_v1, _ = v1_map[(*path_v1, (name, i))]
                if text_v1 == text_v2 and tokens_v1 == tokens_v2:
                    match[(name, j)] = i
                    used.add(i)
                    break
        # Pass 2: pair the leftovers positionally.
        rest1 = [i for i in idxs1.get(name, []) if i not in used]
        rest2 = [j for j in js if (name, j) not in match]
        for i, j in zip(rest1, rest2):
            match[(name, j)] = i
            used.add(i)

    pairs: list[tuple[_ChildKey | None, _ChildKey | None]] = []
    for name, j in children_v2:
        i = match.get((name, j))
        pairs.append(((name, i) if i is not None else None, (name, j)))
    for name, i in children_v1:
        if i not in used1.get(name, ()):
            pairs.append(((name, i), None))
    return pairs


def _build_subtree(
    name: str,
    path_v1: _Path | None,
    path_v2: _Path | None,
    v1_map: dict,
    v2_map: dict,
) -> Node:
    """Build the unified diff subtree for a v1/v2 path pair.

    Recursive: depth is bounded by the input trees' depth, and build_tree
    is itself recursive, so inputs that could overflow here would already
    have failed upstream.
    """
    in_v1 = path_v1 is not None and path_v1 in v1_map
    in_v2 = path_v2 is not None and path_v2 in v2_map

    if in_v2:
        tokens_v2, text_v2, children_v2 = v2_map[path_v2]
    else:
        tokens_v2, text_v2, children_v2 = 0, None, []

    if in_v1:
        tokens_v1, text_v1, children_v1 = v1_map[path_v1]
    else:
        tokens_v1, text_v1, children_v1 = 0, None, []

    if in_v1 and in_v2:
        if text_v1 == text_v2 and tokens_v1 == tokens_v2:
            change = "same"
        else:
            change = "changed"
        delta = tokens_v2 - tokens_v1
    elif in_v2 and not in_v1:
        change = "added"
        delta = tokens_v2
    elif in_v1 and not in_v2:
        change = "removed"
        delta = -tokens_v1
    else:
        # Should not happen
        change = "same"
        delta = 0

    # v2 structure wins: when the node exists in v2, its leaf/internal
    # shape decides - a v2 leaf drops any v1 children, and a v2 internal
    # node contributes text=None below.
    if in_v2 and not children_v2:
        children_v1 = []

    children = [
        _build_subtree(
            (k2 or k1)[0],
            (*path_v1, k1) if k1 is not None and path_v1 is not None else None,
            (*path_v2, k2) if k2 is not None and path_v2 is not None else None,
            v1_map,
            v2_map,
        )
        for k1, k2 in _pair_child_keys(
            children_v1, children_v2, path_v1, path_v2, v1_map, v2_map
        )
    ]

    return Node(
        name=name,
        tokens=tokens_v2 if in_v2 else tokens_v1,
        children=children,
        text=text_v2 if in_v2 else text_v1,
        change=change,
        delta=delta,
    )


def build_diff_tree(v1: Node, v2: Node) -> Node:
    """Build a unified diff tree from two prompt trees."""
    # Root path is () in both maps, so differing root names still diff correctly.
    v1_map = _all_paths(v1, ())
    v2_map = _all_paths(v2, ())
    root_name = v2.name if v2.name == v1.name else "diff"
    tree = _build_subtree(root_name, (), (), v1_map, v2_map)
    # Union view: the root stays wide enough for removed content to remain
    # visible; report the net delta and leave the root itself uncolored.
    tree.tokens = max(v1.tokens, v2.tokens, 1)
    tree.change = None
    tree.delta = v2.tokens - v1.tokens
    return tree


def diff_prompts(
    v1: Any,
    v2: Any,
    output: str | None = "prompt_diff.html",
    title: str | None = None,
    tokenizer: Any = None,
    cost_per_token: float | None = None,
    width: int = 1200,
    height: int = 720,
) -> str:
    """Build and render a diff flamegraph between two prompts."""
    from .core import build_tree
    from .render import to_html

    tree1 = build_tree(v1, name="v1", tokenizer=tokenizer)
    tree2 = build_tree(v2, name="v2", tokenizer=tokenizer)
    diff_tree = build_diff_tree(tree1, tree2)
    html = to_html(
        diff_tree,
        title=title or "Prompt Diff",
        cost_per_token=cost_per_token,
        width=width,
        height=height,
    )
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)
    return html
