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

"""Compare two prompt trees and build a diff flamegraph."""

from __future__ import annotations

from typing import Any

from .core import Node


def _all_paths(node: Node, path: tuple[str, ...]) -> dict[tuple[str, ...], tuple[int, str | None, list[str]]]:
    """Return a dict path -> (tokens, text, child_names) for every node."""
    current = (*path, node.name)
    result = {current: (node.tokens, node.text, [c.name for c in node.children])}
    for child in node.children:
        result.update(_all_paths(child, current))
    return result


def _build_subtree(
    name: str,
    path: tuple[str, ...],
    v1_map: dict,
    v2_map: dict,
) -> Node:
    """Recursively build the unified diff tree for a given path prefix."""
    in_v1 = path in v1_map
    in_v2 = path in v2_map

    if in_v2:
        tokens_v2, text_v2, children_v2 = v2_map[path]
    else:
        tokens_v2, text_v2, children_v2 = 0, None, []

    if in_v1:
        tokens_v1, text_v1, children_v1 = v1_map[path]
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

    # Child union
    child_names = sorted(set(children_v1) | set(children_v2))
    children: list[Node] = []
    for child_name in child_names:
        child_path = (*path, child_name)
        children.append(_build_subtree(child_name, child_path, v1_map, v2_map))

    return Node(
        name=name,
        tokens=tokens_v2 or tokens_v1,
        children=children,
        text=text_v2 or text_v1,
        change=change,
        delta=delta,
    )


def build_diff_tree(v1: Node, v2: Node) -> Node:
    """Build a unified diff tree from two prompt trees."""
    v1_map = _all_paths(v1, ())
    v2_map = _all_paths(v2, ())
    root_name = v2.name if v2.name == v1.name else "diff"
    root_path = (root_name,)
    # Ensure both maps contain the chosen root
    if (v1.name,) in v1_map and (v2.name,) in v2_map and v1.name == v2.name:
        v1_map[root_path] = v1_map.pop((v1.name,))
        v2_map[root_path] = v2_map.pop((v2.name,))
    tree = _build_subtree(root_name, root_path, v1_map, v2_map)
    tree.tokens = max(v1.tokens, v2.tokens, 1)
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
