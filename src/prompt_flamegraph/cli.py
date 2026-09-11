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

"""Command-line interface for prompt-flamegraph."""

from __future__ import annotations

import argparse
import json
import os
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


def _parse_json(raw: str, label: str = "INPUT") -> dict | list:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {label}: {exc}") from exc
    if not isinstance(data, (dict, list)):
        raise SystemExit(f"JSON in {label} must be a dict or a list.")
    return data


def _looks_like_path(value: str) -> bool:
    return "/" in value or value.endswith(".json")


def _load_input(value: str, label: str = "INPUT", file_desc: str = "Input file") -> dict | list:
    path = Path(value)
    try:
        exists = path.exists()
    except OSError:
        exists = False  # e.g. an inline JSON string too long to be a filename
    if not exists:
        if _looks_like_path(value):
            raise SystemExit(f"{file_desc} not found: {value}")
        return _parse_json(value, label)
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"cannot decode {file_desc} as UTF-8: {value}") from exc
    except OSError as exc:
        raise SystemExit(f"cannot read {file_desc} {value}: {exc}") from exc
    return _parse_json(raw, label)


def _write_output(output: str, payload: str) -> None:
    try:
        with open(output, "w", encoding="utf-8") as f:
            f.write(payload)
    except OSError as exc:
        raise SystemExit(f"cannot write output file {output}: {exc}") from exc


def _detect_output(args: argparse.Namespace) -> str:
    if args.output:
        return args.output
    ext = {"html": ".html", "svg": ".svg", "md": ".md", "json": ".json"}.get(args.format, ".html")
    return f"prompt_flamegraph{ext}"


def _build(data, tokenizer):
    from .core import build_tree

    try:
        return build_tree(data, tokenizer=tokenizer)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def _list_models() -> int:
    from .models import _all_models, cache_age_days

    print(f"{'Model':<28} {'Encoding':<14} {'$/Mtok in':>10} {'$/Mtok out':>10} {'Context':>10}")
    for name, spec in sorted(_all_models().items()):
        print(
            f"{spec.name:<28} {spec.encoding:<14} "
            f"{spec.input_per_mtok:>10.3f} {spec.output_per_mtok:>10.3f} {spec.context_window:>10}"
        )
    age = cache_age_days()
    if age is None:
        print("bundled prices only — run --update-models for latest")
    else:
        print(f"prices cached {age:.0f} days ago — refresh with --update-models")
    return 0


def _print_summary(tokens: int, cost_per_token: float | None, spec=None) -> None:
    parts = [f"total: {tokens} tokens"]
    if cost_per_token:
        parts.append(f"est. cost: ${tokens * cost_per_token:.6f}")
    if spec is not None:
        pct = (tokens / spec.context_window * 100) if spec.context_window else 0.0
        parts.append(f"model: {spec.name} ({pct:.1f}% of {spec.context_window} context window)")
    print(" | ".join(parts), file=sys.stderr)


def _check_budget(tokens: int, budget: int | None) -> int:
    """CI gate: return 3 (after a stderr message) when tokens exceed budget."""
    if budget is not None and tokens > budget:
        print(f"BUDGET EXCEEDED: {tokens} > {budget}", file=sys.stderr)
        return 3
    return 0


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
        "--update-models",
        action="store_true",
        help="Fetch the latest LiteLLM pricing table into the local cache and exit.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Bundled models only: never read the pricing cache or hit the network.",
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
        "--no-aggregate",
        action="store_true",
        help="Draw every node in HTML/SVG output, however thin (disables "
        "the '· N more ·' aggregation buckets).",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        metavar="TOKENS",
        help="fail with exit code 3 if total tokens exceed TOKENS (CI gate)",
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

    if args.offline:
        os.environ["PROMPT_FLAMEGRAPH_OFFLINE"] = "1"

    if args.update_models:
        if args.offline:
            parser.error("--offline and --update-models cannot be used together")
        if args.input:
            print(
                f"warning: input {args.input!r} is ignored with --update-models",
                file=sys.stderr,
            )
        from .models import _cache_path, update_models

        try:
            count = update_models()
        except Exception as exc:
            parser.error(f"--update-models failed: {exc}")
        print(f"{count} models cached ({_cache_path()})")
        return 0

    if args.model and args.tokenizer:
        parser.error("--model and --tokenizer cannot be used together")

    if args.terminal:
        if args.diff:
            parser.error("--terminal and --diff cannot be used together")
        if args.format != "html":
            parser.error("--terminal does not support --format")
        if args.output:
            parser.error("--terminal prints to stdout; -o/--output is not allowed")

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
        raw = sys.stdin.read()
        if not raw.strip():
            raise SystemExit("no input on stdin")
        data = normalize(_parse_json(raw, "stdin"))
    else:
        parser.print_help()
        return 1

    output = _detect_output(args)

    if args.terminal:
        from .core import build_tree
        from .terminal import to_terminal

        tree = _build(data, tokenizer)
        title = args.title or "Prompt Flamegraph"
        if spec is not None:
            title = f"{title} — {spec.name}"
        to_terminal(tree, title=title, cost_per_token=cost)
        _print_summary(tree.tokens, cost, spec)
        return _check_budget(tree.tokens, args.budget)

    if args.diff:
        from .diff import build_diff_tree
        from .export import to_json, to_markdown, to_svg
        from .render import to_html

        v2 = normalize(_load_input(args.diff, label="--diff file", file_desc="--diff file"))
        t1 = _build(data, tokenizer)
        t2 = _build(v2, tokenizer)
        diff_tree = build_diff_tree(t1, t2)
        title = args.title or "Prompt Diff"

        if args.format == "json":
            payload = to_json(diff_tree, title=title, cost_per_token=cost, waste_report=None)
        elif args.format == "html":
            payload = to_html(
                diff_tree, title=title, cost_per_token=cost,
                width=args.width, height=args.height,
                aggregate=not args.no_aggregate,
            )
        elif args.format == "svg":
            payload = to_svg(diff_tree, title=title, width=args.width, aggregate=not args.no_aggregate)
        elif args.format == "md":
            payload = to_markdown(diff_tree, title=title, cost_per_token=cost)

        _write_output(output, payload)

        print(f"Diff written to: {output}")
        _print_summary(diff_tree.tokens, cost, spec)
        return _check_budget(diff_tree.tokens, args.budget)

    # Build the token tree once, then render in the requested format.
    tree = _build(data, tokenizer)
    title = args.title or "Prompt Flamegraph"

    if args.format == "json":
        from .export import to_json
        from .waste import detect_waste

        waste_report = None if args.no_waste else detect_waste(tree, context_window=context_window)
        payload = to_json(tree, title=title, cost_per_token=cost, waste_report=waste_report)
    elif args.format == "html":
        from .render import to_html
        from .waste import detect_waste

        waste_report = None if args.no_waste else detect_waste(tree, context_window=context_window)
        payload = to_html(
            tree,
            title=title,
            cost_per_token=cost,
            waste_report=waste_report,
            width=args.width,
            height=args.height,
            aggregate=not args.no_aggregate,
        )
    elif args.format == "svg":
        from .export import to_svg

        payload = to_svg(tree, title=title, width=args.width, aggregate=not args.no_aggregate)
    elif args.format == "md":
        from .export import to_markdown

        payload = to_markdown(tree, title=title, cost_per_token=cost)

    _write_output(output, payload)

    print(f"Flamegraph written to: {output}")
    _print_summary(tree.tokens, cost, spec)
    return _check_budget(tree.tokens, args.budget)


if __name__ == "__main__":
    sys.exit(main())
