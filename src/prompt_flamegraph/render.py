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

# Accepted values for the ``theme`` parameter of ``to_html``.
_THEMES = ("auto", "light", "dark")

# Theme custom properties as (name, light_value, dark_value) triples.
# Light values double as the :root defaults; dark values apply under
# ``prefers-color-scheme: dark`` or an explicit ``body[data-theme]``.
_THEME_VARS: tuple[tuple[str, str, str], ...] = (
    ("--pf-bg", "#f3f4f6", "#0f172a"),
    ("--pf-text", "#111827", "#f8fafc"),
    ("--pf-container-bg", "#ffffff", "#1f2937"),
    ("--pf-header-bg", "#111827", "#020617"),
    ("--pf-header-text", "#f8fafc", "#f8fafc"),
    ("--pf-graph-border", "#e5e7eb", "#374151"),
    ("--pf-ruler-text", "#9ca3af", "#6b7280"),
    ("--pf-footer-text", "#4b5563", "#9ca3af"),
    ("--pf-waste-bg", "#fffbeb", "#2a1b0a"),
    ("--pf-waste-border", "#fcd34d", "#b45309"),
    ("--pf-waste-text", "#78350f", "#fef3c7"),
    ("--pf-waste-heading", "#92400e", "#fbbf24"),
    ("--pf-waste-summary", "#b45309", "#fcd34d"),
    ("--pf-tooltip-bg", "#111827", "#111827"),
    ("--pf-tooltip-text", "#f8fafc", "#f8fafc"),
    ("--pf-tooltip-accent", "#fbbf24", "#fbbf24"),
    ("--pf-cost", "#fbbf24", "#fbbf24"),
    ("--pf-added-bg", "#22c55e", "#4ade80"),
    ("--pf-added-text", "#0f172a", "#0f172a"),
    ("--pf-removed-bg", "#ef4444", "#f87171"),
    ("--pf-removed-text", "#f8fafc", "#0f172a"),
    ("--pf-changed-bg", "#f59e0b", "#fbbf24"),
    ("--pf-changed-text", "#0f172a", "#0f172a"),
    ("--pf-same-bg", "#94a3b8", "#94a3b8"),
    ("--pf-same-text", "#0f172a", "#0f172a"),
    ("--pf-agg-bg", "#cbd5e1", "#475569"),
    ("--pf-agg-text", "#334155", "#f8fafc"),
    ("--pf-agg-stripe-1", "rgba(255,255,255,0.35)", "rgba(255,255,255,0.10)"),
    ("--pf-agg-stripe-2", "rgba(0,0,0,0.04)", "rgba(15,23,42,0.40)"),
    ("--pf-bar-text-dark", "#0f172a", "#0f172a"),
    ("--pf-bar-text-light", "#f8fafc", "#f8fafc"),
    ("--pf-bar-border", "rgba(255,255,255,0.18)", "rgba(255,255,255,0.18)"),
    ("--pf-shadow", "rgba(0,0,0,0.1)", "rgba(0,0,0,0.4)"),
    ("--pf-focus-outline", "#111827", "#f8fafc"),
    ("--pf-toggle-bg", "#ffffff", "#1f2937"),
    ("--pf-toggle-border", "#d1d5db", "#4b5563"),
    ("--pf-toggle-text", "#111827", "#f8fafc"),
)

# Fixed top-right sun/moon button, rendered only for theme="auto".
_THEME_TOGGLE_BUTTON = """\
          <button id="pf-theme-toggle" class="pf-theme-toggle" type="button" aria-label="Toggle theme">
            <svg class="pf-icon-sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
            <svg class="pf-icon-moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          </button>"""

# Theme toggle logic: restore a saved choice, then flip light/dark on
# click and persist it. Only emitted for theme="auto".
_THEME_TOGGLE_JS = """\
            const themeToggle = document.getElementById('pf-theme-toggle');
            if (themeToggle) {
              try {
                const savedTheme = localStorage.getItem('pf-theme');
                if (savedTheme === 'light' || savedTheme === 'dark') {
                  document.body.dataset.theme = savedTheme;
                }
              } catch (err) {}
              themeToggle.addEventListener('click', () => {
                let currentTheme = document.body.dataset.theme;
                if (currentTheme !== 'light' && currentTheme !== 'dark') {
                  currentTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
                }
                const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
                document.body.dataset.theme = nextTheme;
                try { localStorage.setItem('pf-theme', nextTheme); } catch (err) {}
              });
            }"""


def _vars_block(dark: bool, indent: str) -> str:
    """Serialize one set of theme custom-property declarations."""
    pos = 2 if dark else 1
    return "\n".join(
        f"{indent}{entry[0]}: {entry[pos]};" for entry in _THEME_VARS
    )


def _theme_css() -> str:
    """:root defaults plus dark/explicit overrides for the theme vars.

    Every line is indented at least 10 spaces so it survives the
    textwrap.dedent applied to the document it is interpolated into.
    """
    light = _vars_block(dark=False, indent=" " * 14)
    dark_media = _vars_block(dark=True, indent=" " * 16)
    dark_body = _vars_block(dark=True, indent=" " * 14)
    return (
        "            :root {\n"
        f"{light}\n"
        "            }\n"
        "            @media (prefers-color-scheme: dark) {\n"
        "              :root {\n"
        f"{dark_media}\n"
        "              }\n"
        # The `body` prefix makes these selectors outrank the plain
        # `.pf-theme-toggle` icon defaults declared further below.
        "              body .pf-theme-toggle .pf-icon-sun { display: none; }\n"
        "              body .pf-theme-toggle .pf-icon-moon { display: block; }\n"
        "            }\n"
        # Explicit choices live on <body>, which is a closer ancestor than
        # :root, so they always win over the media query above.
        '            body[data-theme="light"] {\n'
        f"{light}\n"
        "            }\n"
        '            body[data-theme="dark"] {\n'
        f"{dark_body}\n"
        "            }"
    )


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return (part / whole) * 100


def _attr(value: str) -> str:
    """Escape a string for an HTML attribute, dropping U+2028/U+2029.

    Line/paragraph separators are legal in attribute values but trip up
    some inline-script and diff tooling, so normalize them to spaces.
    """
    return html_module.escape(value).replace("\u2028", " ").replace("\u2029", " ")


def _style(node: "Node", depth: int) -> tuple[str, str]:
    """Return (background_color, text_color) for a flamegraph block."""
    if node.change == "added":
        return "var(--pf-added-bg)", "var(--pf-added-text)"
    if node.change == "removed":
        return "var(--pf-removed-bg)", "var(--pf-removed-text)"
    if node.change == "changed":
        return "var(--pf-changed-bg)", "var(--pf-changed-text)"
    if node.change == "same":
        return "var(--pf-same-bg)", "var(--pf-same-text)"

    import hashlib

    h = int(hashlib.md5(node.name.encode("utf-8")).hexdigest()[:8], 16) % 360
    # Moderate saturation and a lightness band that cycles with depth instead
    # of collapsing to black, so deep bars stay readable and distinguishable.
    saturation = 55 + (depth % 3) * 7  # 55-69%
    lightness = 58 - (depth % 4) * 6  # 40-58%, cycles every 4 levels
    bg = f"hsl({h}, {saturation}%, {lightness}%)"
    text = (
        "var(--pf-bar-text-dark)" if lightness >= 52 else "var(--pf-bar-text-light)"
    )
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
    safe_name = _attr(name)
    full = f"{name} — {_format_number(tokens)}"
    if len(full) <= fit:
        shown = full
    elif len(name) <= fit:
        shown = name
    else:
        shown = name[: fit - 1].rstrip() + "…"
    return (
        f'<span class="pf-label" title="{safe_name}">'
        f"{_attr(shown)}</span>"
    )


def _aggregate_node(members: "list[Node]") -> "Node":
    """Build a synthetic leaf node summarizing hidden children."""
    from .core import Node

    if not members:
        raise ValueError("cannot aggregate an empty member list")

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
    agg_enabled: bool = True,
) -> str:
    pct_parent = min(_pct(node.tokens, parent_tokens), 100.0)
    pct_total = min(max(_pct(node.tokens, total_tokens), 0.0), 100.0)
    if aggregate and not node.change:
        bg, text = "var(--pf-agg-bg)", "var(--pf-agg-text)"
    else:
        bg, text = _style(node, depth)
    safe_name = _attr(node.name)
    bar_px = pct_total / 100.0 * avail_px
    display = _label_html(node.name, node.tokens, bar_px)

    children_html = ""
    if node.children:
        if not agg_enabled:
            # No aggregation: every child renders, however thin — the
            # tooltip still shows each bar's real name/text on hover.
            blocks = [
                _render_node(
                    child, node.tokens, total_tokens, depth + 1, max_depth,
                    avail_px, agg_enabled=False,
                )
                for child in node.children
            ]
        elif depth >= max_depth:
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
        text_attr = f' data-text="{_attr(snippet)}"'

    bar_class = "pf-bar pf-bar--agg" if aggregate else "pf-bar"
    aria_label = f"{safe_name}, {_format_number(node.tokens)} tokens"
    return (
        f'<div class="pf-node" style="width:{pct_parent}%" data-tokens="{node.tokens}" '
        f'data-pct-total="{pct_total:.2f}"{change_attr}{delta_attr}>'
        f'<div class="{bar_class}" style="background-color:{bg};color:{text}" '
        f'tabindex="0" data-name="{safe_name}" '
        f'aria-label="{aria_label}"{text_attr}>{display}</div>'
        f"{children_html}</div>"
    )


def _waste_html(waste_report: WasteReport | None) -> str:
    if waste_report is None or not waste_report.findings:
        return ""

    rows = []
    for f in waste_report.findings:
        wasted = f"<b>{f.tokens_wasted}</b> tokens wasted — " if f.tokens_wasted else ""
        rows.append(
            f'<li class="pf-finding pf-finding--{html_module.escape(f.kind)}">'
            f"{wasted}{html_module.escape(f.message)}</li>"
        )

    return f"""
    <div class="pf-waste">
      <h3>Token waste findings</h3>
      <ul>{"".join(rows)}</ul>
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
    aggregate: bool = True,
    theme: str = "auto",
) -> str:
    """Render a Node tree as a self-contained HTML string.

    When ``aggregate`` is False every node is drawn, however thin — the
    hover tooltip still shows each bar's real name and text.

    ``theme`` is "auto" (follow ``prefers-color-scheme`` and render a
    manual toggle persisted to localStorage), "light" or "dark" (forced
    via a ``data-theme`` attribute on ``<body>``).
    """
    if theme not in _THEMES:
        raise ValueError(
            f"invalid theme {theme!r}: expected one of {_THEMES}"
        )
    width = min(16384, max(200, int(width)))
    height = max(100, int(height))
    max_depth = max(1, int(max_depth))
    # Coerce to float so Decimals and friends serialize as valid JS numbers.
    try:
        cost = (
            float(cost_per_token)
            if cost_per_token is not None
            and math.isfinite(float(cost_per_token))
            else None
        )
    except (TypeError, ValueError, OverflowError):
        cost = None
    cost_js = repr(cost) if cost is not None else "null"
    total_tokens = tree.tokens
    total_cost = (total_tokens * cost) if cost is not None else None
    top_children = sorted(tree.children, key=lambda c: c.tokens, reverse=True)[:5]
    top_summary = " · ".join(
        f"{_format_number(c.tokens)} {_attr(c.name)} ({_pct(c.tokens, total_tokens):.1f}%)"
        for c in top_children
    )

    # Estimated pixel width available to the flamegraph inside the container.
    avail_px = max(64.0, float(width) - _GRAPH_HPAD_PX)
    flame_html = _render_node(
        tree, tree.tokens, tree.tokens, 0, max_depth, avail_px, agg_enabled=aggregate
    )

    cost_line = ""
    if total_cost is not None:
        cost_line = f"<p class=\"pf-cost\">Estimated cost: {_money(total_cost)}</p>"

    waste_html = _waste_html(waste_report)

    theme_css = _theme_css()
    if theme == "auto":
        # No data-theme attribute: the media query decides until the user
        # picks a side with the toggle (persisted to localStorage).
        body_open = "        <body>\n" + _THEME_TOGGLE_BUTTON
        theme_js = _THEME_TOGGLE_JS
    else:
        body_open = f'        <body data-theme="{theme}">'
        theme_js = ""

    return textwrap.dedent(
        f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <title>{html_module.escape(title)}</title>
          <style>
{theme_css}
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; padding: 0 0.75rem; background: var(--pf-bg); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: var(--pf-text); }}
            .pf-container {{ width: 100%; max-width: {width}px; margin: 2rem auto; background: var(--pf-container-bg); border-radius: 8px; box-shadow: 0 4px 6px -1px var(--pf-shadow); overflow: hidden; }}
            .pf-header {{ padding: 1.25rem 1.5rem; background: var(--pf-header-bg); color: var(--pf-header-text); }}
            .pf-header h1 {{ margin: 0 0 0.5rem; font-size: 1.5rem; }}
            .pf-meta {{ display: flex; gap: 2rem; flex-wrap: wrap; font-size: 0.95rem; opacity: 0.9; }}
            .pf-cost {{ margin: 0.5rem 0 0; font-weight: 600; color: var(--pf-cost); }}
            .pf-graph {{ padding: 1.25rem 1.5rem; height: auto; max-height: {height}px; overflow: auto; border-bottom: 1px solid var(--pf-graph-border); }}
            .pf-ruler {{ display: flex; justify-content: space-between; margin-bottom: 0.5rem; padding-bottom: 0.25rem; border-bottom: 1px solid var(--pf-graph-border); font-size: 0.72rem; color: var(--pf-ruler-text); letter-spacing: 0.02em; }}
            .pf-flamegraph {{ display: flex; flex-direction: column; min-width: 100%; }}
            .pf-node {{ display: flex; flex-direction: column; min-width: 2px; gap: 2px; }}
            .pf-bar {{ height: 30px; display: flex; align-items: center; justify-content: flex-start; padding: 0 6px; overflow: hidden; white-space: nowrap; font-size: 12px; font-weight: 500; border-radius: 4px; border: 1px solid var(--pf-bar-border); cursor: default; transition: filter 0.1s; }}
            .pf-bar:hover, .pf-bar:focus {{ filter: brightness(1.15); z-index: 10; }}
            .pf-bar:focus {{ outline: 2px solid var(--pf-focus-outline); outline-offset: -2px; }}
            .pf-bar--agg {{ background-image: repeating-linear-gradient(45deg, var(--pf-agg-stripe-1) 0 6px, var(--pf-agg-stripe-2) 6px 12px); font-style: italic; }}
            .pf-label {{ overflow: hidden; text-overflow: ellipsis; }}
            .pf-children {{ display: flex; flex-direction: row; width: 100%; gap: 2px; overflow-x: auto; min-width: 0; }}
            .pf-footer {{ padding: 1rem 1.5rem; font-size: 0.85rem; color: var(--pf-footer-text); }}
            .pf-waste {{ padding: 1rem 1.5rem; background: var(--pf-waste-bg); border-bottom: 1px solid var(--pf-waste-border); color: var(--pf-waste-text); }}
            .pf-waste h3 {{ margin: 0 0 0.75rem; font-size: 1.1rem; color: var(--pf-waste-heading); }}
            .pf-waste ul {{ margin: 0; padding-left: 1.25rem; line-height: 1.6; }}
            .pf-waste li {{ margin-bottom: 0.25rem; }}
            .pf-waste-summary {{ margin: 0.75rem 0 0; font-size: 0.9rem; color: var(--pf-waste-summary); }}
            .pf-tooltip {{ position: fixed; display: none; background: var(--pf-tooltip-bg); color: var(--pf-tooltip-text); padding: 8px 12px; border-radius: 4px; font-size: 13px; pointer-events: none; z-index: 1000; max-width: 320px; line-height: 1.4; box-shadow: 0 4px 6px var(--pf-shadow); }}
            .pf-tooltip b {{ color: var(--pf-tooltip-accent); }}
            .pf-tooltip-text {{ display: block; margin-top: 4px; opacity: 0.75; white-space: pre-wrap; word-break: break-word; }}
            .pf-theme-toggle {{ position: fixed; top: 1rem; right: 1rem; z-index: 1100; width: 2.25rem; height: 2.25rem; display: inline-flex; align-items: center; justify-content: center; padding: 0; background: var(--pf-toggle-bg); color: var(--pf-toggle-text); border: 1px solid var(--pf-toggle-border); border-radius: 9999px; cursor: pointer; box-shadow: 0 2px 4px var(--pf-shadow); }}
            .pf-theme-toggle svg {{ width: 1.1rem; height: 1.1rem; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
            .pf-theme-toggle .pf-icon-moon {{ display: none; }}
            body[data-theme="dark"] .pf-theme-toggle .pf-icon-sun {{ display: none; }}
            body[data-theme="dark"] .pf-theme-toggle .pf-icon-moon {{ display: block; }}
            body[data-theme="light"] .pf-theme-toggle .pf-icon-sun {{ display: block; }}
            body[data-theme="light"] .pf-theme-toggle .pf-icon-moon {{ display: none; }}
            @media (max-width: 640px) {{
              .pf-meta {{ flex-direction: column; gap: 0.5rem; }}
              .pf-graph {{ max-height: none; }}
            }}
          </style>
        </head>
{body_open}
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
{theme_js}
            const tooltip = document.getElementById('pf-tooltip');
            const bars = document.querySelectorAll('.pf-bar');

            const addLine = (value) => {{
              tooltip.appendChild(document.createElement('br'));
              tooltip.appendChild(document.createTextNode(value));
            }};

            const showTooltip = (bar) => {{
              const node = bar.closest('.pf-node');
              const tokens = parseInt(node.dataset.tokens || '0', 10);
              const pctTotal = parseFloat(node.dataset.pctTotal || '0');
              const name = bar.dataset.name || '';
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
            }};

            const hideTooltip = () => {{
              tooltip.style.display = 'none';
            }};

            // Keep the tooltip inside the viewport: offset from the anchor
            // point, then clamp against the tooltip's rendered size.
            const positionTooltip = (x, y) => {{
              const margin = 12;
              const tip = tooltip.getBoundingClientRect();
              const maxX = Math.max(margin, window.innerWidth - tip.width - margin);
              const maxY = Math.max(margin, window.innerHeight - tip.height - margin);
              tooltip.style.left = Math.max(margin, Math.min(x + margin, maxX)) + 'px';
              tooltip.style.top = Math.max(margin, Math.min(y + margin, maxY)) + 'px';
            }};

            bars.forEach(bar => {{
              bar.addEventListener('mouseenter', () => showTooltip(bar));
              bar.addEventListener('mousemove', (e) => positionTooltip(e.clientX, e.clientY));
              bar.addEventListener('mouseleave', hideTooltip);
              bar.addEventListener('focus', () => {{
                showTooltip(bar);
                const rect = bar.getBoundingClientRect();
                positionTooltip(rect.left, rect.bottom);
              }});
              bar.addEventListener('blur', hideTooltip);
            }});
          </script>
        </body>
        </html>
        """
    ).strip()
