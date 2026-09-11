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

"""Render a prompt token tree in the terminal."""

from __future__ import annotations

import hashlib
import re
import shutil
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Node

_NONPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _clean_name(name: str) -> str:
    """Strip control characters so names cannot inject ANSI sequences."""
    return _NONPRINTABLE.sub("", name)


def _hsl_to_rgb(h: int, s: int, l: int) -> tuple[int, int, int]:
    """Quick HSL->RGB for terminal use. All params in degrees/percent."""
    s = max(0.0, min(1.0, s / 100))
    l = max(0.0, min(1.0, l / 100))
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2

    if h < 60:
        r1, g1, b1 = c, x, 0
    elif h < 120:
        r1, g1, b1 = x, c, 0
    elif h < 180:
        r1, g1, b1 = 0, c, x
    elif h < 240:
        r1, g1, b1 = 0, x, c
    elif h < 300:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x

    r = max(0, min(255, int((r1 + m) * 255)))
    g = max(0, min(255, int((g1 + m) * 255)))
    b = max(0, min(255, int((b1 + m) * 255)))
    return r, g, b


def _hsl_to_ansi(h: int, s: int, l: int) -> str:
    """Convert HSL (h, s, l) to an RGB ANSI foreground code (approximate)."""
    r, g, b = _hsl_to_rgb(h, s, l)
    return f"\x1b[38;2;{r};{g};{b}m"


def _hsl_to_hex(h: int, s: int, l: int) -> str:
    """Convert HSL (h, s, l) to a #rrggbb hex string (approximate)."""
    r, g, b = _hsl_to_rgb(h, s, l)
    return f"#{r:02x}{g:02x}{b:02x}"


def _color_for_node(name: str, depth: int) -> tuple[str, str]:
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16) % 360
    s = 65 + (depth % 3) * 8
    l = max(35, 70 - depth * 12)
    color = _hsl_to_ansi(h, s, l)
    reset = "\x1b[0m"
    return color, reset


def _max_depth(node: "Node") -> int:
    return max((_max_depth(c) + 1 for c in node.children), default=0)


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def _rich_render(node: "Node", title: str, cost_per_token: float | None, max_width: int) -> None:
    from rich.console import Console
    from rich.markup import escape
    from rich.table import Table
    from rich.text import Text

    console = Console()
    console.rule(f"[bold]{escape(_clean_name(title))}[/bold]")
    console.print(f"[dim]Total: {_format_number(node.tokens)} tokens[/dim]")
    if cost_per_token:
        total_cost = node.tokens * cost_per_token
        console.print(f"[dim]Estimated cost: ${total_cost:.6f}[/dim]")

    if not node.children:
        console.print("[dim](no categories)[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Category", no_wrap=False, ratio=2)
    table.add_column("Tokens", justify="right")
    table.add_column("% of total", justify="right")
    table.add_column("Visual", ratio=3)

    total = node.tokens

    def walk(n: "Node", depth: int) -> None:
        pct = (n.tokens / total * 100) if total > 0 else 0
        bar_len = max(1, int(pct / 100 * max_width)) if n.tokens > 0 else 0
        h = int(hashlib.md5(n.name.encode("utf-8")).hexdigest()[:8], 16) % 360
        s = 65 + (depth % 3) * 8
        l = max(35, 70 - depth * 12)
        bar = Text("█" * bar_len, style=_hsl_to_hex(h, s, l))
        table.add_row(
            escape("  " * depth + _clean_name(n.name)),
            _format_number(n.tokens),
            f"{pct:.1f}%",
            bar,
        )
        for child in n.children:
            walk(child, depth + 1)

    for child in node.children:
        walk(child, 0)

    console.print(table)


def _ascii_render(node: "Node", title: str, cost_per_token: float | None, max_width: int) -> None:
    print(f"\n{'=' * (max_width // 2)} {_clean_name(title)} {'=' * (max_width // 2)}")
    print(f"Total tokens: {_format_number(node.tokens)}")
    if cost_per_token:
        total_cost = node.tokens * cost_per_token
        print(f"Estimated cost: ${total_cost:.6f}")
    print()

    if not node.children:
        print("(no categories)")
        return

    use_color = sys.stdout.isatty()
    total = node.tokens

    def walk(n: "Node", depth: int) -> None:
        pct = (n.tokens / total * 100) if total > 0 else 0
        bar_len = max(1, int(pct / 100 * max_width)) if n.tokens > 0 else 0
        bar = "█" * bar_len
        if use_color:
            color, reset = _color_for_node(n.name, depth)
            bar = color + bar + reset
        indent = "  " * depth
        name = _clean_name(n.name)[:25]
        print(f"{indent}{name:<25} {_format_number(n.tokens):>8} ({pct:5.1f}%) {bar}")
        for child in n.children:
            walk(child, depth + 1)

    for child in node.children:
        walk(child, 0)


def to_terminal(
    tree: "Node",
    title: str = "Prompt Flamegraph",
    cost_per_token: float | None = None,
    use_rich: bool = True,
    width: int | None = None,
) -> None:
    """Print the prompt tree as a colored bar chart in the terminal."""
    term_width = width or shutil.get_terminal_size().columns
    # Reserve space for the fixed columns (25-char name, 8-char token count,
    # 8-char percent, 3 separator spaces) plus two-space indent per depth.
    reserved = 25 + 8 + 8 + 3 + 2 * _max_depth(tree)
    max_bar = max(10, term_width - reserved)

    if use_rich:
        try:
            _rich_render(tree, title, cost_per_token, max_bar)
            return
        except ImportError:
            pass

    _ascii_render(tree, title, cost_per_token, max_bar)
