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


# Children narrower than this share of their parent's bar are merged into a
# single trailing "· N more ·" aggregate instead of being drawn individually.
_MIN_PCT = 2.0
# …or below this absolute pixel width.
_MIN_PX = 26.0
# Rough px-per-char estimate used to decide which label fits inside a bar.
_CHAR_PX = 7.0
_LABEL_PAD = 8.0
# No label at all on bars narrower than this.
_MIN_LABEL_PX = 30.0
# Muted styling for synthetic "· N more ·" aggregate bars.
_AGGREGATE_FILL = "#cbd5e1"
_AGGREGATE_TEXT = "#0f172a"


def _bar_label(name: str, tokens: int, bar_w: float) -> str | None:
    """Pick the best-fitting label for a bar, or None if it is too narrow.

    Prefers "name — tokens"; falls back to the (possibly truncated) name
    alone; returns None for slivers. Truncation always happens on the raw
    string — callers escape afterwards.
    """
    if bar_w < _MIN_LABEL_PX:
        return None
    avail = bar_w - _LABEL_PAD
    short = name if len(name) < 25 else name[:22] + "…"
    full = f"{short} — {_format_number(tokens)}"
    if len(full) * _CHAR_PX <= avail:
        return full
    if len(short) * _CHAR_PX <= avail:
        return short
    max_chars = int(avail / _CHAR_PX)
    if max_chars >= 4:
        return short[: max_chars - 1] + "…"
    return None


def to_svg(
    tree: "Node",
    title: str = "Prompt Flamegraph",
    width: int = 1200,
    row_height: int = 34,
    max_depth: int = 8,
    aggregate: bool = True,
) -> str:
    """Render a Node tree as a standalone, interactive SVG string.

    Children narrower than ``_MIN_PCT`` percent of their parent's bar are
    merged into one trailing synthetic "· N more ·" node (summed tokens).
    Nodes deeper than ``max_depth`` are likewise aggregated into their
    ancestor's "· N more ·" bucket. The Node tree itself is never modified.
    Pass ``aggregate=False`` to draw every node, however thin.
    """
    width = int(width)

    def y(d: int) -> int:
        return 50 + d * row_height

    # Build SVG content iteratively, tracking x and width.
    bars: list[str] = []
    rendered_max_depth = 0

    def emit_bar(
        name: str,
        tokens: int,
        x: float,
        w: float,
        depth: int,
        fill: str,
        text_fill: str,
        hover: str,
    ) -> None:
        nonlocal rendered_max_depth
        if depth > rendered_max_depth:
            rendered_max_depth = depth
        bars.append(
            f'<rect x="{x:.2f}" y="{y(depth)}" width="{w:.2f}" height="{row_height}" '
            f'fill="{fill}" stroke="rgba(255,255,255,0.2)" rx="2"><title>{hover}</title></rect>'
        )
        label_raw = _bar_label(name, tokens, w)
        if label_raw is not None:
            # Truncate raw, then escape — slicing escaped text could split
            # an HTML entity and produce malformed XML.
            label = html_module.escape(label_raw, quote=False)
            bars.append(
                f'<text x="{x + w / 2:.2f}" y="{y(depth) + row_height / 2 + 4:.2f}" '
                f'text-anchor="middle" font-size="12" fill="{text_fill}">{label}</text>'
            )

    stack = [(tree, 0.0, float(width), 0)]
    while stack:
        node, x, node_w, depth = stack.pop()
        fill = _color(node, depth)
        text = _text_color(node, depth)
        safe = html_module.escape(node.name, quote=False)
        hover = f"{safe}: {_format_number(node.tokens)} tokens ({_pct(node.tokens, tree.tokens):.2f}%)"
        if node.change:
            hover += f" [{html_module.escape(node.change, quote=False)}]"
        emit_bar(node.name, node.tokens, x, node_w, depth, fill, text, hover)

        def child_width(child: "Node") -> float:
            w = node_w * (child.tokens / node.tokens) if node.tokens > 0 else 0.0
            # Diff trees can produce children wider than their parent.
            return min(w, node_w)

        child_x = x
        entries = []
        agg: list[tuple[Node, float]] = []
        if not aggregate:
            # Draw every child however thin — hover <title> still gives
            # the real name/tokens for each sliver.
            for child in node.children:
                child_w = child_width(child)
                entries.append((child, child_x, child_w, depth + 1))
                child_x += child_w
        elif depth < max_depth:
            min_w = node_w * (_MIN_PCT / 100)
            for child in node.children:
                child_w = child_width(child)
                if child_w < min_w or child_w < _MIN_PX:
                    # Too narrow to draw on its own — fold into the bucket.
                    agg.append((child, child_w))
                else:
                    entries.append((child, child_x, child_w, depth + 1))
                    child_x += child_w
        else:
            # Depth cap: every descendant collapses into the bucket.
            for child in node.children:
                agg.append((child, child_width(child)))
        if agg:
            agg_tokens = sum(c.tokens for c, _ in agg)
            agg_w = sum(w for _, w in agg)
            agg_name = f"· {len(agg)} more ·"
            # Hover lists the top few merged nodes, then "and K more".
            shown = [
                f"{c.name}: {_format_number(c.tokens)} tokens" for c, _ in agg[:5]
            ]
            if len(agg) > 5:
                shown.append(f"and {len(agg) - 5} more")
            names = ", ".join(shown)
            agg_hover = (
                f"{agg_name}: {_format_number(agg_tokens)} tokens "
                f"({_pct(agg_tokens, tree.tokens):.2f}%) "
                f"[{html_module.escape(names, quote=False)}]"
            )
            emit_bar(
                agg_name,
                agg_tokens,
                child_x,
                agg_w,
                depth + 1,
                _AGGREGATE_FILL,
                _AGGREGATE_TEXT,
                agg_hover,
            )
        stack.extend(reversed(entries))

    height = (rendered_max_depth + 1) * row_height + 80

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
