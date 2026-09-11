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

"""Export a prompt token tree to SVG, JSON, or Markdown."""

from __future__ import annotations

import html as html_module
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Node
    from .waste import WasteReport


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return (part / whole) * 100


def _format_number(n: int) -> str:
    sign = "-" if n < 0 else ""
    a = abs(n)
    if a >= 1_000_000:
        return f"{sign}{a / 1_000_000:.2f}M"
    if a >= 1_000:
        return f"{sign}{a / 1_000:.1f}k"
    return str(n)


def _color(node: "Node", depth: int) -> str:
    if node.change == "added":
        return "#22c55e"
    if node.change == "removed":
        return "#ef4444"
    if node.change == "changed":
        return "#f59e0b"
    if node.change == "same":
        return "#94a3b8"

    import hashlib

    h = int(hashlib.md5(node.name.encode("utf-8")).hexdigest()[:8], 16) % 360
    s = 65 + (depth % 3) * 8
    l = max(28, 62 - depth * 12)
    return f"hsl({h}, {s}%, {l}%)"


def _text_color(node: "Node", depth: int) -> str:
    if node.change in ("removed", "changed"):
        return "#f8fafc"
    if node.change == "same":
        return "#0f172a"

    l = max(28, 62 - depth * 12)
    return "#0f172a" if l > 55 else "#f8fafc"


def to_svg(
    tree: "Node",
    title: str = "Prompt Flamegraph",
    width: int = 1200,
    row_height: int = 34,
) -> str:
    """Render a Node tree as a standalone, interactive SVG string."""
    width = int(width)
    max_depth = 0
    stack = [(tree, 0)]
    while stack:
        node, d = stack.pop()
        if d > max_depth:
            max_depth = d
        stack.extend((c, d + 1) for c in node.children)
    height = (max_depth + 1) * row_height + 80

    def y(d: int) -> int:
        return 50 + d * row_height

    # Build SVG content iteratively, tracking x and width
    bars: list[str] = []
    stack = [(tree, 0.0, float(width), tree.tokens, 0)]
    while stack:
        node, x, parent_w, parent_tokens, depth = stack.pop()
        node_w = parent_w * (node.tokens / parent_tokens) if parent_tokens > 0 else 0.0
        # root gets full width
        if depth == 0:
            node_w = parent_w
        fill = _color(node, depth)
        text = _text_color(node, depth)
        # Truncate the raw name, then escape — slicing escaped text could
        # split an HTML entity and produce malformed XML.
        safe = html_module.escape(node.name, quote=False)
        short_raw = node.name if len(node.name) < 25 else node.name[:22] + "…"
        short = html_module.escape(short_raw, quote=False)
        hover = f"{safe}: {_format_number(node.tokens)} tokens ({_pct(node.tokens, tree.tokens):.2f}%)"
        if node.change:
            hover += f" [{html_module.escape(node.change, quote=False)}]"

        bars.append(
            f'<rect x="{x:.2f}" y="{y(depth)}" width="{node_w:.2f}" height="{row_height}" '
            f'fill="{fill}" stroke="rgba(255,255,255,0.2)" rx="2"><title>{hover}</title></rect>'
        )
        if node_w > 30:
            bars.append(
                f'<text x="{x + node_w / 2:.2f}" y="{y(depth) + row_height / 2 + 4:.2f}" '
                f'text-anchor="middle" font-size="12" fill="{text}">{short}</text>'
            )

        child_x = x
        entries = []
        for child in node.children:
            child_w = node_w * (child.tokens / node.tokens) if node.tokens > 0 else 0.0
            entries.append((child, child_x, node_w, node.tokens, depth + 1))
            child_x += child_w
        stack.extend(reversed(entries))

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#f3f4f6"/>
  <text x="20" y="30" font-size="18" font-weight="bold" fill="#111827">{html_module.escape(title)}</text>
  <text x="20" y="50" font-size="13" fill="#4b5563">Total: {_format_number(tree.tokens)} tokens</text>
  <g transform="translate(0, 10)">
    {"".join(bars)}
  </g>
</svg>"""


def _md_cell(s: str) -> str:
    """Make a string safe inside a Markdown table cell / heading."""
    return s.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def to_markdown(
    tree: "Node",
    title: str = "Prompt Flamegraph",
    cost_per_token: float | None = None,
) -> str:
    """Render a Node tree as a Markdown table."""
    lines: list[str] = [f"# {_md_cell(title)}", ""]

    total = tree.tokens
    total_cost = (total * cost_per_token) if cost_per_token is not None else None
    lines.append(f"- **Total tokens:** {_format_number(total)}")
    if total_cost is not None:
        lines.append(f"- **Estimated cost:** ${total_cost:.6f}")
    lines.append("")
    lines.append("| Path | Tokens | % | Cost | Change |")
    lines.append("|------|--------|---:|------|--------|")

    def path_str(path: list[str]) -> str:
        return " › ".join(_md_cell(p) for p in path)

    stack = [(child, [child.name]) for child in reversed(tree.children)]
    while stack:
        node, path = stack.pop()
        pct = _pct(node.tokens, total)
        cost = (node.tokens * cost_per_token) if cost_per_token is not None else 0.0
        cost_str = f"${cost:.6f}" if cost_per_token is not None else "-"
        change_str = _md_cell(node.change) if node.change else "-"
        lines.append(
            f"| {path_str(path)} | {_format_number(node.tokens)} | {pct:.2f}% | {cost_str} | {change_str} |"
        )
        for child in reversed(node.children):
            stack.append((child, path + [child.name]))

    return "\n".join(lines)


def to_json(
    tree: "Node",
    title: str = "Prompt Flamegraph",
    cost_per_token: float | None = None,
    waste_report: "WasteReport | None" = None,
) -> str:
    """Render a Node tree as a machine-readable JSON string."""

    def node_to_dict(root: "Node") -> dict:
        # Iterative two-pass build so deep trees can't hit the recursion limit.
        dicts: dict[int, dict] = {}
        nodes: list[Node] = []
        stack = [root]
        while stack:
            node = stack.pop()
            nodes.append(node)
            d: dict = {"name": node.name, "tokens": node.tokens}
            if node.change:
                d["change"] = node.change
            if node.delta:
                d["delta"] = node.delta
            if node.text is not None:
                d["text"] = node.text
            dicts[id(node)] = d
            stack.extend(node.children)
        for node in nodes:
            dicts[id(node)]["children"] = [dicts[id(c)] for c in node.children]
        return dicts[id(root)]

    waste = None
    if waste_report is not None:
        waste = {
            "total_tokens": waste_report.total_tokens,
            "wasted_tokens": waste_report.wasted_tokens,
            "waste_ratio": waste_report.waste_ratio,
            "findings": [
                {
                    "kind": f.kind,
                    "path": f.path,
                    "message": f.message,
                    "tokens_wasted": f.tokens_wasted,
                }
                for f in waste_report.findings
            ],
        }

    return json.dumps(
        {
            "title": title,
            "total_tokens": tree.tokens,
            "cost_usd": (tree.tokens * cost_per_token) if cost_per_token is not None else None,
            "waste": waste,
            "tree": node_to_dict(tree),
        },
        ensure_ascii=False,
        indent=2,
    )
