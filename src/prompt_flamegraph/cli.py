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


def _parse_json(raw: str) -> dict | list:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON input: {exc}") from exc
    if not isinstance(data, (dict, list)):
        raise SystemExit("Input JSON must be a dict or a list.")
    return data


def _load_input(value: str) -> dict | list:
    path = Path(value)
    raw = path.read_text(encoding="utf-8") if path.exists() else value
    return _parse_json(raw)


def _detect_output(args: argparse.Namespace) -> str:
    if args.output:
        return args.output
    ext = {"html": ".html", "svg": ".svg", "md": ".md", "json": ".json"}.get(args.format, ".html")
    return f"prompt_flamegraph{ext}"


def _list_models() -> int:
    from .models import list_models, resolve_model

    print(f"{'Model':<28} {'Encoding':<14} {'$/Mtok in':>10} {'$/Mtok out':>10} {'Context':>10}")
    for name in list_models():
        spec = resolve_model(name)
        print(
            f"{spec.name:<28} {spec.encoding:<14} "
            f"{spec.input_per_mtok:>10.3f} {spec.output_per_mtok:>10.3f} {spec.context_window:>10}"
        )
    return 0


def _print_summary(tokens: int, cost_per_token: float | None, spec=None) -> None:
    parts = [f"total: {tokens} tokens"]
    if cost_per_token:
        parts.append(f"est. cost: ${tokens * cost_per_token:.6f}")
    if spec is not None:
        pct = (tokens / spec.context_window * 100) if spec.context_window else 0.0
        parts.append(f"model: {spec.name} ({pct:.1f}% of {spec.context_window} context window)")
    print(" | ".join(parts), file=sys.stderr)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prompt-flamegraph",
        description="Generate a lightweight flamegraph of your LLM prompt tokens.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="JSON file (or JSON string) representing the prompt structure. '-' reads stdin.",
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
        choices=["html", "svg", "md", "json"],
        default="html",
        help="Output format (default: html).",
    )
    parser.add_argument(
        "--tokenizer",
        default=None,
        help="Tokenizer to use: 'tiktoken', 'words', or a callable.",
    )
    parser.add_argument(
        "--model",
        default=None,
        metavar="NAME",
        help="Model name: selects tokenizer encoding, pricing and context window.",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List supported models and exit.",
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
    return parser


def _resolve_model(parser: argparse.ArgumentParser, args: argparse.Namespace):
    """Return (spec, tokenizer) for --model, or (None, args.tokenizer)."""
    if not args.model:
        return None, args.tokenizer
    from .core import get_tokenizer
    from .models import resolve_model

    try:
        spec = resolve_model(args.model)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        tokenizer = get_tokenizer(f"model:{spec.name}")
    except ImportError:
        print(
            f"warning: tiktoken is not installed; using the default tokenizer "
            f"for '{spec.name}' (counts will be approximate)",
            file=sys.stderr,
        )
        tokenizer = None
    return spec, tokenizer


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.model and args.tokenizer:
        parser.error("--model and --tokenizer cannot be used together")

    if args.list_models:
        return _list_models()

    spec, tokenizer = _resolve_model(parser, args)
    context_window = spec.context_window if spec is not None else None

    cost = args.cost
    if cost is None and spec is not None:
        cost = spec.input_per_mtok / 1e6

    from .adapters import normalize

    if args.demo:
        data = normalize(SAMPLE_PROMPT)
    elif args.input and args.input != "-":
        data = normalize(_load_input(args.input))
    elif args.input == "-" or (sys.stdin is not None and not sys.stdin.isatty()):
        data = normalize(_parse_json(sys.stdin.read()))
    else:
        parser.print_help()
        return 1

    output = _detect_output(args)

    if args.terminal:
        from .core import build_tree
        from .terminal import to_terminal

        tree = build_tree(data, tokenizer=tokenizer)
        title = args.title or "Prompt Flamegraph"
        if spec is not None:
            title = f"{title} — {spec.name}"
        to_terminal(tree, title=title, cost_per_token=cost)
        _print_summary(tree.tokens, cost, spec)
        return 0

    if args.diff:
        from .core import build_tree
        from .diff import build_diff_tree
        from .export import to_json, to_markdown, to_svg
        from .render import to_html

        v2 = normalize(_load_input(args.diff))
        t1 = build_tree(data, tokenizer=tokenizer)
        t2 = build_tree(v2, tokenizer=tokenizer)
        diff_tree = build_diff_tree(t1, t2)
        title = args.title or "Prompt Diff"

        if args.format == "json":
            payload = to_json(diff_tree, title=title, cost_per_token=cost, waste_report=None)
        elif args.format == "html":
            payload = to_html(diff_tree, title=title, cost_per_token=cost, width=args.width, height=args.height)
        elif args.format == "svg":
            payload = to_svg(diff_tree, title=title, width=args.width)
        elif args.format == "md":
            payload = to_markdown(diff_tree, title=title, cost_per_token=cost)

        with open(output, "w", encoding="utf-8") as f:
            f.write(payload)

        print(f"Diff written to: {output}")
        _print_summary(diff_tree.tokens, cost, spec)
        return 0

    if args.format == "html":
        from .core import build_tree, profile_prompt

        tree = build_tree(data, tokenizer=tokenizer)
        profile_prompt(
            data,
            output=output,
            title=args.title,
            tokenizer=tokenizer,
            cost_per_token=cost,
            detect_waste=not args.no_waste,
            width=args.width,
            height=args.height,
            context_window=context_window,
        )
    else:
        from .core import build_tree

        tree = build_tree(data, tokenizer=tokenizer)
        title = args.title or "Prompt Flamegraph"

        if args.format == "json":
            from .export import to_json
            from .waste import detect_waste

            waste_report = None if args.no_waste else detect_waste(tree, context_window=context_window)
            payload = to_json(tree, title=title, cost_per_token=cost, waste_report=waste_report)
        elif args.format == "svg":
            from .export import to_svg

            payload = to_svg(tree, title=title, width=args.width)
        elif args.format == "md":
            from .export import to_markdown

            payload = to_markdown(tree, title=title, cost_per_token=cost)

        with open(output, "w", encoding="utf-8") as f:
            f.write(payload)

    print(f"Flamegraph written to: {output}")
    _print_summary(tree.tokens, cost, spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
