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

"""Command-line interface for prompt-flamegraph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SAMPLE_PROMPT = {
    "system_prompt": (
        "You are a helpful coding assistant. Be concise. "
        "Always think step by step before answering."
    ),
    "tools": [
        {
            "name": "read_file",
            "description": "Read a file from disk. Accepts a path argument.",
            "schema": "{\"path\": \"string\"}",
        },
        {
            "name": "run_command",
            "description": "Execute a shell command and return stdout/stderr.",
            "schema": "{\"command\": \"string\"}",
        },
    ],
    "rag_context": {
        "doc_1.py": "import os\n\ndef hello():\n    return 'hello'\n",
        "doc_2.py": "import sys\n\ndef world():\n    return 'world'\n",
    },
    "chat_history": [
        {"role": "user", "content": "Help me profile my prompt tokens."},
        {"role": "assistant", "content": "Sure, I can help you understand where your tokens go."},
    ],
}


def _load_input(value: str) -> dict:
    path = Path(value)
    if path.exists():
        raw = path.read_text(encoding="utf-8")
    else:
        raw = value
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON input: {exc}") from exc
    if not isinstance(data, (dict, list)):
        raise SystemExit("Input JSON must be a dict or a list.")
    return data


def _detect_output(args: argparse.Namespace) -> str:
    if args.output:
        return args.output
    ext = {"html": ".html", "svg": ".svg", "md": ".md"}.get(args.format, ".html")
    return f"prompt_flamegraph{ext}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="prompt-flamegraph",
        description="Generate a lightweight flamegraph of your LLM prompt tokens.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="JSON file (or JSON string) representing the prompt structure.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output file (inferred from --format if not given).",
    )
    parser.add_argument(
        "-t",
        "--title",
        default=None,
        help="Title of the output.",
    )
    parser.add_argument(
        "--format",
        choices=["html", "svg", "md"],
        default="html",
        help="Output format (default: html).",
    )
    parser.add_argument(
        "--tokenizer",
        default=None,
        help="Tokenizer to use: 'tiktoken', 'words', or a callable.",
    )
    parser.add_argument(
        "--cost",
        type=float,
        default=None,
        help="Cost per token (e.g. 1.5e-6 for $1.5 per million tokens).",
    )
    parser.add_argument(
        "--diff",
        metavar="FILE",
        default=None,
        help="Compare INPUT with another JSON file and output a diff flamegraph.",
    )
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="Print a terminal bar chart instead of writing a file.",
    )
    parser.add_argument(
        "--no-waste",
        action="store_true",
        help="Disable waste detection for HTML output.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use the built-in sample prompt.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1200,
        help="Graph width in pixels (SVG/HTML).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=720,
        help="Graph max height in pixels (HTML).",
    )

    args = parser.parse_args(argv)

    if args.demo:
        data = SAMPLE_PROMPT
    elif args.input:
        data = _load_input(args.input)
    else:
        parser.print_help()
        return 1

    output = _detect_output(args)

    if args.terminal:
        from .core import build_tree
        from .terminal import to_terminal

        tree = build_tree(data, tokenizer=args.tokenizer)
        to_terminal(tree, title=args.title, cost_per_token=args.cost)
        return 0

    if args.diff:
        from .core import build_tree
        from .diff import build_diff_tree
        from .render import to_html
        from .export import to_svg, to_markdown

        v2 = _load_input(args.diff)
        t1 = build_tree(data, tokenizer=args.tokenizer)
        t2 = build_tree(v2, tokenizer=args.tokenizer)
        diff_tree = build_diff_tree(t1, t2)

        if args.format == "html":
            html = to_html(diff_tree, title=args.title or "Prompt Diff", cost_per_token=args.cost, width=args.width, height=args.height)
            with open(output, "w", encoding="utf-8") as f:
                f.write(html)
        elif args.format == "svg":
            from .export import to_svg
            svg = to_svg(diff_tree, title=args.title or "Prompt Diff", width=args.width)
            with open(output, "w", encoding="utf-8") as f:
                f.write(svg)
        elif args.format == "md":
            from .export import to_markdown
            md = to_markdown(diff_tree, title=args.title or "Prompt Diff", cost_per_token=args.cost)
            with open(output, "w", encoding="utf-8") as f:
                f.write(md)

        print(f"Diff written to: {output}")
        return 0

    if args.format == "html":
        from .core import profile_prompt

        profile_prompt(
            data,
            output=output,
            title=args.title,
            tokenizer=args.tokenizer,
            cost_per_token=args.cost,
            detect_waste=not args.no_waste,
            width=args.width,
            height=args.height,
        )
    elif args.format == "svg":
        from .core import build_tree
        from .export import to_svg

        tree = build_tree(data, tokenizer=args.tokenizer)
        svg = to_svg(tree, title=args.title, width=args.width)
        with open(output, "w", encoding="utf-8") as f:
            f.write(svg)
    elif args.format == "md":
        from .core import build_tree
        from .export import to_markdown

        tree = build_tree(data, tokenizer=args.tokenizer)
        md = to_markdown(tree, title=args.title, cost_per_token=args.cost)
        with open(output, "w", encoding="utf-8") as f:
            f.write(md)

    print(f"Flamegraph written to: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
