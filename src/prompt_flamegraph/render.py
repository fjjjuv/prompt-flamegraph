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

"""Render a prompt token tree as a standalone, interactive HTML flamegraph."""

from __future__ import annotations

import html as html_module
import math
import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Node
    from .waste import WasteReport


# Children whose rendered width is below this percentage of their parent's
# width — or below _MIN_PX absolute pixels — are merged into a trailing
# "· N more ·" aggregate bar.
_MIN_PCT = 2.0
_MIN_PX = 26.0

# Rough pixel width of one label character at the bar font size (12px).
_CHAR_PX = 7.0

# Horizontal chrome (container + graph padding) subtracted from `width` when
# estimating how many label characters fit inside a bar.
_GRAPH_HPAD_PX = 64

# How many member names the aggregate tooltip lists before "… and K more".
_AGG_TOP_NAMES = 5


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return (part / whole) * 100


def _style(node: "Node", depth: int) -> tuple[str, str]:
    """Return (background_color, text_color) for a flamegraph block."""
    if node.change == "added":
        return "#22c55e", "#0f172a"
    if node.change == "removed":
        return "#ef4444", "#f8fafc"
    if node.change == "changed":
        return "#f59e0b", "#0f172a"
    if node.change == "same":
        return "#94a3b8", "#0f172a"

    import hashlib

    h = int(hashlib.md5(node.name.encode("utf-8")).hexdigest()[:8], 16) % 360
    # Moderate saturation and a lightness band that cycles with depth instead
    # of collapsing to black, so deep bars stay readable and distinguishable.
    saturation = 55 + (depth % 3) * 7  # 55-69%
    lightness = 58 - (depth % 4) * 6  # 40-58%, cycles every 4 levels
    bg = f"hsl({h}, {saturation}%, {lightness}%)"
    text = "#0f172a" if lightness >= 52 else "#f8fafc"
    return bg, text


def _money(amount: float) -> str:
    if not math.isfinite(amount):
        return "-"
    if amount == 0:
        return "$0.00"
    sign = "-" if amount < 0 else ""
    mag = abs(amount)
    if mag < 1e-6:
        return f"{sign}$<0.000001"
    if mag < 0.001:
        return f"{sign}${mag:.6f}".rstrip("0").rstrip(".")
    if mag < 0.01:
        return f"{sign}${mag:.4f}".rstrip("0").rstrip(".")
    return f"{sign}${mag:,.4f}".rstrip("0").rstrip(".")


def _format_number(n: int) -> str:
    sign = "-" if n < 0 else ""
    a = abs(n)
    if a >= 1_000_000:
        return f"{sign}{a / 1_000_000:.2f}M"
    if a >= 1_000:
        return f"{sign}{a / 1_000:.1f}k"
    return str(n)


def _label_html(name: str, tokens: int, px: float) -> str:
    """Label fitted to the estimated pixel width of the bar.

    Wide bars get "name — tokens", medium bars get the (possibly truncated)
    name, and slivers get nothing — truncation is relative to the bar width,
    not a fixed character count.
    """
    fit = int(px // _CHAR_PX)
    if fit < 4:
        return ""
    safe_name = html_module.escape(name)
    full = f"{name} — {_format_number(tokens)}"
    if len(full) <= fit:
        shown = full
    elif len(name) <= fit:
        shown = name
    else:
        shown = name[: fit - 1].rstrip() + "…"
    return (
        f'<span class="pf-label" title="{safe_name}">'
        f"{html_module.escape(shown)}</span>"
    )


def _aggregate_node(members: "list[Node]") -> "Node":
    """Build a synthetic leaf node summarizing hidden children."""
    from .core import Node

    total = sum(m.tokens for m in members)
    ordered = sorted(members, key=lambda m: m.tokens, reverse=True)
    lines = [
        f"{m.name}: {_format_number(m.tokens)} tokens"
        for m in ordered[:_AGG_TOP_NAMES]
    ]
    if len(ordered) > _AGG_TOP_NAMES:
        lines.append(f"… and {len(ordered) - _AGG_TOP_NAMES} more")
    change = members[0].change
    if not all(m.change == change for m in members):
        change = None
    return Node(
        name=f"· {len(members)} more ·",
        tokens=total,
        text="\n".join(lines),
        change=change,
        delta=sum(m.delta for m in members),
    )


def _render_node(
    node: "Node",
    parent_tokens: int,
    total_tokens: int,
    depth: int,
    max_depth: int,
    avail_px: float,
    aggregate: bool = False,
) -> str:
    pct_parent = min(_pct(node.tokens, parent_tokens), 100.0)
    pct_total = _pct(node.tokens, total_tokens)
    if aggregate and not node.change:
        bg, text = "#cbd5e1", "#334155"
    else:
        bg, text = _style(node, depth)
    safe_name = html_module.escape(node.name)
    bar_px = pct_total / 100.0 * avail_px
    display = _label_html(node.name, node.tokens, bar_px)

    children_html = ""
    if node.children:
        if depth >= max_depth:
            # Beyond the depth cap everything collapses into one bucket so
            # the token count is preserved without rendering slivers.
            blocks = [
                _render_node(
                    _aggregate_node(node.children),
                    node.tokens,
                    total_tokens,
                    depth + 1,
                    max_depth,
                    avail_px,
                    aggregate=True,
                )
            ]
        else:
            visible = []
            hidden = []
            for child in node.children:
                child_px = child.tokens / total_tokens * avail_px if total_tokens else 0.0
                if _pct(child.tokens, node.tokens) >= _MIN_PCT and child_px >= _MIN_PX:
                    visible.append(child)
                else:
                    hidden.append(child)
            blocks = [
                _render_node(
                    child, node.tokens, total_tokens, depth + 1, max_depth, avail_px
                )
                for child in visible
            ]
            if hidden:
                blocks.append(
                    _render_node(
                        _aggregate_node(hidden),
                        node.tokens,
                        total_tokens,
                        depth + 1,
                        max_depth,
                        avail_px,
                        aggregate=True,
                    )
                )
        children_html = f'<div class="pf-children">{"".join(blocks)}</div>'

    change_attr = (
        f' data-change="{html_module.escape(node.change)}"' if node.change else ""
    )
    delta_attr = f' data-delta="{node.delta}"' if node.delta != 0 else ""
    text_attr = ""
    if node.text is not None:
        snippet = node.text[:200] + ("…" if len(node.text) > 200 else "")
        text_attr = f' data-text="{html_module.escape(snippet)}"'

    bar_class = "pf-bar pf-bar--agg" if aggregate else "pf-bar"
    return (
        f'<div class="pf-node" style="width:{pct_parent}%" data-tokens="{node.tokens}" '
        f'data-pct-total="{pct_total:.2f}"{change_attr}{delta_attr}>'
        f'<div class="{bar_class}" style="background-color:{bg};color:{text}" '
        f'data-name="{safe_name}"{text_attr}>{display}</div>{children_html}</div>'
    )


def _waste_html(waste_report: WasteReport | None) -> str:
    if waste_report is None or not waste_report.findings:
        return ""

    rows = ""
    for f in waste_report.findings:
        wasted = f"<b>{f.tokens_wasted}</b> tokens wasted — " if f.tokens_wasted else ""
        rows += f"<li class=\"pf-finding pf-finding--{html_module.escape(f.kind)}\">{wasted}{html_module.escape(f.message)}</li>"

    return f"""
    <div class="pf-waste">
      <h3>Token waste findings</h3>
      <ul>{rows}</ul>
      <p class="pf-waste-summary">Waste: <b>{_format_number(waste_report.wasted_tokens)}</b> of <b>{_format_number(waste_report.total_tokens)}</b> tokens ({waste_report.waste_ratio*100:.1f}%)</p>
    </div>
    """


def to_html(
    tree: Node,
    title: str = "Prompt Flamegraph",
    cost_per_token: float | None = None,
    waste_report: WasteReport | None = None,
    width: int = 1200,
    height: int = 720,
    max_depth: int = 8,
) -> str:
    """Render a Node tree as a self-contained HTML string."""
    width = int(width)
    height = int(height)
    max_depth = int(max_depth)
    cost = (
        cost_per_token
        if cost_per_token is not None and math.isfinite(cost_per_token)
        else None
    )
    cost_js = repr(cost) if cost is not None else "null"
    total_tokens = tree.tokens
    total_cost = (total_tokens * cost) if cost is not None else None
    top_children = sorted(tree.children, key=lambda c: c.tokens, reverse=True)[:5]
    top_summary = " · ".join(
        f"{_format_number(c.tokens)} {html_module.escape(c.name)} ({_pct(c.tokens, total_tokens):.1f}%)"
        for c in top_children
    )

    # Estimated pixel width available to the flamegraph inside the container.
    avail_px = max(64.0, float(width) - _GRAPH_HPAD_PX)
    flame_html = _render_node(tree, tree.tokens, tree.tokens, 0, max_depth, avail_px)

    cost_line = ""
    if total_cost is not None:
        cost_line = f"<p class=\"pf-cost\">Estimated cost: {_money(total_cost)}</p>"

    waste_html = _waste_html(waste_report)

    return textwrap.dedent(
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{html_module.escape(title)}</title>
          <style>
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; padding: 0 0.75rem; background: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #111827; }}
            .pf-container {{ width: 100%; max-width: {width}px; margin: 2rem auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); overflow: hidden; }}
            .pf-header {{ padding: 1.25rem 1.5rem; background: #111827; color: #f8fafc; }}
            .pf-header h1 {{ margin: 0 0 0.5rem; font-size: 1.5rem; }}
            .pf-meta {{ display: flex; gap: 2rem; flex-wrap: wrap; font-size: 0.95rem; opacity: 0.9; }}
            .pf-cost {{ margin: 0.5rem 0 0; font-weight: 600; color: #fbbf24; }}
            .pf-graph {{ padding: 1.25rem 1.5rem; height: auto; max-height: {height}px; overflow: auto; border-bottom: 1px solid #e5e7eb; }}
            .pf-ruler {{ display: flex; justify-content: space-between; margin-bottom: 0.5rem; padding-bottom: 0.25rem; border-bottom: 1px solid #e5e7eb; font-size: 0.72rem; color: #9ca3af; letter-spacing: 0.02em; }}
            .pf-flamegraph {{ display: flex; flex-direction: column; min-width: 100%; }}
            .pf-node {{ display: flex; flex-direction: column; min-width: 2px; gap: 2px; }}
            .pf-bar {{ height: 30px; display: flex; align-items: center; justify-content: flex-start; padding: 0 6px; overflow: hidden; white-space: nowrap; font-size: 12px; font-weight: 500; border-radius: 4px; border: 1px solid rgba(255,255,255,0.18); cursor: default; transition: filter 0.1s; }}
            .pf-bar:hover {{ filter: brightness(1.15); z-index: 10; }}
            .pf-bar--agg {{ background-image: repeating-linear-gradient(45deg, rgba(255,255,255,0.35) 0 6px, rgba(0,0,0,0.04) 6px 12px); font-style: italic; }}
            .pf-label {{ overflow: hidden; text-overflow: ellipsis; }}
            .pf-children {{ display: flex; flex-direction: row; width: 100%; gap: 2px; }}
            .pf-footer {{ padding: 1rem 1.5rem; font-size: 0.85rem; color: #4b5563; }}
            .pf-waste {{ padding: 1rem 1.5rem; background: #fffbeb; border-bottom: 1px solid #fcd34d; color: #78350f; }}
            .pf-waste h3 {{ margin: 0 0 0.75rem; font-size: 1.1rem; color: #92400e; }}
            .pf-waste ul {{ margin: 0; padding-left: 1.25rem; line-height: 1.6; }}
            .pf-waste li {{ margin-bottom: 0.25rem; }}
            .pf-waste-summary {{ margin: 0.75rem 0 0; font-size: 0.9rem; color: #b45309; }}
            .pf-tooltip {{ position: fixed; display: none; background: #111827; color: #f8fafc; padding: 8px 12px; border-radius: 4px; font-size: 13px; pointer-events: none; z-index: 1000; max-width: 320px; line-height: 1.4; box-shadow: 0 4px 6px rgba(0,0,0,0.2); }}
            .pf-tooltip b {{ color: #fbbf24; }}
            .pf-tooltip-text {{ display: block; margin-top: 4px; opacity: 0.75; white-space: pre-wrap; word-break: break-word; }}
            @media (max-width: 640px) {{
              .pf-meta {{ flex-direction: column; gap: 0.5rem; }}
              .pf-graph {{ max-height: none; }}
            }}
          </style>
        </head>
        <body>
          <div class="pf-container">
            <header class="pf-header">
              <h1>{html_module.escape(title)}</h1>
              <div class="pf-meta">
                <span><b>{_format_number(total_tokens)}</b> tokens</span>
                <span><b>{len(tree.children)}</b> top categories</span>
                <span>Top: {top_summary}</span>
              </div>
              {cost_line}
            </header>
            {waste_html}
            <div class="pf-graph">
              <div class="pf-ruler"><span>0</span><span>{_format_number(total_tokens)} tokens — 100%</span></div>
              <div class="pf-flamegraph">
                {flame_html}
              </div>
            </div>
            <footer class="pf-footer">
              Generated by <a href="https://github.com/fjjjuv/prompt-flamegraph" target="_blank">prompt-flamegraph</a>.
            </footer>
          </div>
          <div id="pf-tooltip" class="pf-tooltip"></div>
          <script>
            const tooltip = document.getElementById('pf-tooltip');
            const bars = document.querySelectorAll('.pf-bar');

            const addLine = (value) => {{
              tooltip.appendChild(document.createElement('br'));
              tooltip.appendChild(document.createTextNode(value));
            }};

            bars.forEach(bar => {{
              bar.addEventListener('mouseenter', (e) => {{
                const node = bar.closest('.pf-node');
                const tokens = parseInt(node.dataset.tokens, 10);
                const pctTotal = parseFloat(node.dataset.pctTotal);
                const name = bar.dataset.name;
                const costPerToken = {cost_js};

                const change = node.dataset.change;
                const delta = parseInt(node.dataset.delta || '0', 10);
                const text = bar.dataset.text;

                tooltip.textContent = '';
                const title = document.createElement('b');
                title.textContent = name;
                tooltip.appendChild(title);
                addLine(`${{tokens.toLocaleString()}} tokens`);
                addLine(`${{pctTotal.toFixed(2)}}% du total`);
                if (change) {{
                  const deltaSign = delta > 0 ? '+' : '';
                  addLine(`Change: ${{change}} (${{deltaSign}}${{delta}} tokens)`);
                }}
                if (costPerToken !== null) {{
                  const nodeCost = (tokens * costPerToken).toFixed(6).replace(/\\.?0+$/, '');
                  addLine(`Coût : $${{nodeCost}}`);
                }}
                if (text) {{
                  tooltip.appendChild(document.createElement('br'));
                  const snippet = document.createElement('span');
                  snippet.className = 'pf-tooltip-text';
                  snippet.textContent = text;
                  tooltip.appendChild(snippet);
                }}

                tooltip.style.display = 'block';
              }});

              bar.addEventListener('mousemove', (e) => {{
                tooltip.style.left = (e.clientX + 12) + 'px';
                tooltip.style.top = (e.clientY + 12) + 'px';
              }});

              bar.addEventListener('mouseleave', () => {{
                tooltip.style.display = 'none';
              }});
            }});
          </script>
        </body>
        </html>
        """
    ).strip()
