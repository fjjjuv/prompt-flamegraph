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

"""Render a prompt token tree in the terminal."""

from __future__ import annotations

import hashlib
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import Node


def _hsl_to_ansi(h: int, s: int, l: int) -> str:
    """Convert HSL to an RGB ANSI foreground code (approximate)."""
    # Quick HSL->RGB for terminal use
    s /= 100
    l /= 100
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

    r = int((r1 + m) * 255)
    g = int((g1 + m) * 255)
    b = int((b1 + m) * 255)
    return f"\x1b[38;2;{r};{g};{b}m"


def _color_for_node(name: str, depth: int) -> tuple[str, str]:
    h = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16) % 360
    s = 65 + (depth % 3) * 8
    l = max(35, 70 - depth * 12)
    color = _hsl_to_ansi(h, s, l)
    reset = "\x1b[0m"
    return color, reset


def _ascii_bar(tokens: int, total: int, max_width: int) -> str:
    if total <= 0:
        return ""
    width = max(1, int(tokens / total * max_width))
    return "█" * width


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)


def _rich_render(node: "Node", title: str, cost_per_token: float | None, max_width: int) -> None:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

    console = Console()
    console.rule(f"[bold]{title}[/bold]")
    console.print(f"[dim]Total: {_format_number(node.tokens)} tokens[/dim]")
    if cost_per_token:
        total_cost = node.tokens * cost_per_token
        console.print(f"[dim]Estimated cost: ${total_cost:.6f}[/dim]")

    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Category", no_wrap=False, ratio=2)
    table.add_column("Tokens", justify="right")
    table.add_column("%", justify="right")
    table.add_column("Visual", ratio=3)

    def walk(n: "Node", depth: int, parent_tokens: int) -> None:
        pct = (n.tokens / parent_tokens * 100) if parent_tokens > 0 else 0
        bar_len = int(pct / 100 * max_width) if parent_tokens > 0 else 0
        bar_len = max(1, bar_len) if n.tokens > 0 else 0
        h = int(hashlib.md5(n.name.encode("utf-8")).hexdigest()[:8], 16) % 360
        color_hex = _hsl_to_hex(h, 70 - depth * 12, 65 + (depth % 3) * 8)
        bar = Text("█" * bar_len, style=f"#{color_hex[1:]}" if color_hex else "white")
        table.add_row(
            "  " * depth + n.name,
            _format_number(n.tokens),
            f"{pct:.1f}%",
            bar,
        )
        for child in n.children:
            walk(child, depth + 1, n.tokens if n.tokens > 0 else 1)

    for child in node.children:
        walk(child, 0, node.tokens)

    console.print(table)


def _hsl_to_hex(h: int, l: int, s: int) -> str:
    s /= 100
    l /= 100
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

    r = int((r1 + m) * 255)
    g = int((g1 + m) * 255)
    b = int((b1 + m) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


def _ascii_render(node: "Node", title: str, cost_per_token: float | None, max_width: int) -> None:
    print(f"\n{'=' * (max_width // 2)} {title} {'=' * (max_width // 2)}")
    print(f"Total tokens: {_format_number(node.tokens)}")
    if cost_per_token:
        total_cost = node.tokens * cost_per_token
        print(f"Estimated cost: ${total_cost:.6f}")
    print()

    def walk(n: "Node", depth: int, parent_tokens: int) -> None:
        pct = (n.tokens / parent_tokens * 100) if parent_tokens > 0 else 0
        bar_len = int(pct / 100 * max_width) if parent_tokens > 0 else 0
        bar_len = max(1, bar_len) if n.tokens > 0 else 0
        color, reset = _color_for_node(n.name, depth)
        bar = color + "█" * bar_len + reset
        indent = "  " * depth
        print(f"{indent}{n.name:<25} {_format_number(n.tokens):>8} ({pct:5.1f}%) {bar}")
        for child in n.children:
            walk(child, depth + 1, n.tokens if n.tokens > 0 else 1)

    for child in node.children:
        walk(child, 0, node.tokens)


def to_terminal(
    tree: "Node",
    title: str = "Prompt Flamegraph",
    cost_per_token: float | None = None,
    use_rich: bool = True,
    width: int | None = None,
) -> None:
    """Print the prompt tree as a colored bar chart in the terminal."""
    term_width = width or shutil.get_terminal_size().columns
    # Reserve space for name, tokens, pct and padding
    max_bar = max(20, term_width - 55)

    if use_rich:
        try:
            _rich_render(tree, title, cost_per_token, max_bar)
            return
        except ImportError:
            pass

    _ascii_render(tree, title, cost_per_token, max_bar)
