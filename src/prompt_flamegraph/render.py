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
    saturation = 65 + (depth % 3) * 8
    lightness = max(28, 62 - depth * 12)
    bg = f"hsl({h}, {saturation}%, {lightness}%)"
    text = "#0f172a" if lightness > 55 else "#f8fafc"
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


def _render_node(node: Node, parent_tokens: int, total_tokens: int, depth: int) -> str:
    pct_parent = min(_pct(node.tokens, parent_tokens), 100.0)
    pct_total = _pct(node.tokens, total_tokens)
    bg, text = _style(node, depth)
    safe_name = html_module.escape(node.name)
    short_raw = node.name if len(node.name) < 35 else node.name[:32] + "…"
    display = (
        f'<span class="pf-label" title="{safe_name}">'
        f"{html_module.escape(short_raw)}</span>"
    )

    children_html = ""
    if node.children:
        child_blocks = "".join(
            _render_node(child, node.tokens, total_tokens, depth + 1)
            for child in node.children
        )
        children_html = f'<div class="pf-children">{child_blocks}</div>'

    change_attr = (
        f' data-change="{html_module.escape(node.change)}"' if node.change else ""
    )
    delta_attr = f' data-delta="{node.delta}"' if node.delta != 0 else ""
    text_attr = ""
    if node.text is not None:
        snippet = node.text[:200] + ("…" if len(node.text) > 200 else "")
        text_attr = f' data-text="{html_module.escape(snippet)}"'

    return (
        f'<div class="pf-node" style="width:{pct_parent}%" data-tokens="{node.tokens}" '
        f'data-pct-total="{pct_total:.2f}"{change_attr}{delta_attr}>'
        f'<div class="pf-bar" style="background-color:{bg};color:{text}" '
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
) -> str:
    """Render a Node tree as a self-contained HTML string."""
    width = int(width)
    height = int(height)
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

    flame_html = _render_node(tree, tree.tokens, tree.tokens, 0)

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
            body {{ margin: 0; background: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #111827; }}
            .pf-container {{ max-width: {width}px; margin: 2rem auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); overflow: hidden; }}
            .pf-header {{ padding: 1.25rem 1.5rem; background: #111827; color: #f8fafc; }}
            .pf-header h1 {{ margin: 0 0 0.5rem; font-size: 1.5rem; }}
            .pf-meta {{ display: flex; gap: 2rem; flex-wrap: wrap; font-size: 0.95rem; opacity: 0.9; }}
            .pf-cost {{ margin: 0.5rem 0 0; font-weight: 600; color: #fbbf24; }}
            .pf-graph {{ padding: 1.5rem; height: {height}px; overflow: auto; border-bottom: 1px solid #e5e7eb; }}
            .pf-flamegraph {{ display: flex; flex-direction: column; min-width: 100%; }}
            .pf-node {{ display: flex; flex-direction: column; min-width: 2px; }}
            .pf-bar {{ height: 34px; display: flex; align-items: center; justify-content: center; padding: 0 4px; overflow: hidden; white-space: nowrap; font-size: 12px; font-weight: 500; border: 1px solid rgba(255,255,255,0.18); cursor: default; transition: filter 0.1s; }}
            .pf-bar:hover {{ filter: brightness(1.15); z-index: 10; }}
            .pf-label {{ overflow: hidden; text-overflow: ellipsis; }}
            .pf-children {{ display: flex; flex-direction: row; width: 100%; }}
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
              .pf-graph {{ height: auto; }}
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
