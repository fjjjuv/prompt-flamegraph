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

"""Core logic: token counting and tree building."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass
class Node:
    name: str
    tokens: int
    children: list[Node] = field(default_factory=list)
    text: str | None = None
    change: str | None = None  # 'added', 'removed', 'same', 'changed'
    delta: int = 0

    @property
    def is_leaf(self) -> bool:
        return not self.children


Tokenizer = Callable[[str], int]


def _default_count(text: str) -> int:
    """Fallback token estimator when tiktoken is not installed."""
    text = text.strip()
    if not text:
        return 0
    # Word-ish tokens plus isolated punctuation. Rough but stable and fast.
    return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


def _load_tiktoken(encoding: str = "cl100k_base") -> Tokenizer | None:
    try:
        import tiktoken
    except ImportError:
        return None

    enc = tiktoken.get_encoding(encoding)

    def count(text: str) -> int:
        return len(enc.encode(text))

    return count


def get_tokenizer(
    tokenizer: Tokenizer | str | None = None,
) -> Tokenizer:
    """Resolve a tokenizer from a name, callable, or default."""
    if tokenizer is None:
        tiktoken_count = _load_tiktoken()
        if tiktoken_count is not None:
            return tiktoken_count
        return _default_count

    if callable(tokenizer):
        return tokenizer

    if tokenizer.startswith("model:"):
        from .models import resolve_model

        spec = resolve_model(tokenizer[len("model:"):])
        if spec.encoding == "estimate":
            return _default_count
        tiktoken_count = _load_tiktoken(spec.encoding)
        if tiktoken_count is None:
            raise ImportError(
                f"tiktoken is not installed but model {spec.name!r} uses the "
                f"{spec.encoding} encoding. Run 'pip install prompt-flamegraph[tiktoken]'"
            )
        return tiktoken_count

    if tokenizer == "tiktoken" or tokenizer.startswith("cl100k"):
        tiktoken_count = _load_tiktoken()
        if tiktoken_count is None:
            raise ImportError(
                "tiktoken is not installed. Run 'pip install prompt-flamegraph[tiktoken]'"
            )
        return tiktoken_count

    if tokenizer.startswith("o200k"):
        tiktoken_count = _load_tiktoken("o200k_base")
        if tiktoken_count is None:
            raise ImportError(
                "tiktoken is not installed. Run 'pip install prompt-flamegraph[tiktoken]'"
            )
        return tiktoken_count

    if tokenizer == "words":
        return _default_count

    raise ValueError(f"Unknown tokenizer: {tokenizer}")


def count_tokens(text: str, tokenizer: Tokenizer | str | None = None) -> int:
    """Count tokens in a string using the selected tokenizer."""
    return get_tokenizer(tokenizer)(text)


def _guess_name(value: Any, index: int) -> str:
    if isinstance(value, dict):
        for key in ("name", "title", "id", "role", "filename", "file", "source"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    return f"item_{index}"


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_tree(
    data: Any,
    name: str = "prompt",
    tokenizer: Tokenizer | str | None = None,
    _count_fn: Callable[[str], int] | None = None,
) -> Node:
    """Recursively build a token tree from a nested dict/list/string."""
    count_fn = _count_fn or get_tokenizer(tokenizer)

    if isinstance(data, dict):
        children = [
            build_tree(value, name=key, _count_fn=count_fn)
            for key, value in data.items()
        ]
        return Node(name=name, tokens=sum(c.tokens for c in children), children=children)

    if isinstance(data, (list, tuple)):
        children = [
            build_tree(value, name=_guess_name(value, i), _count_fn=count_fn)
            for i, value in enumerate(data)
        ]
        return Node(name=name, tokens=sum(c.tokens for c in children), children=children)

    text = _to_text(data)
    return Node(name=name, tokens=count_fn(text), text=text)


def flatten_tree(node: Node) -> list[Node]:
    """Return a flat list of all nodes in depth-first order."""
    out = [node]
    for child in node.children:
        out.extend(flatten_tree(child))
    return out


def profile_prompt(
    data: Any,
    output: str | None = "prompt_flamegraph.html",
    title: str | None = None,
    tokenizer: Tokenizer | str | None = None,
    cost_per_token: float | None = None,
    detect_waste: bool = True,
    context_window: int | None = None,
    width: int = 1200,
    height: int = 720,
) -> str:
    """Build a prompt token tree and render it to a standalone HTML flamegraph."""
    from . import render

    tree = build_tree(data, tokenizer=tokenizer)
    waste_report = None
    if detect_waste:
        from .waste import detect_waste

        waste_report = detect_waste(tree, context_window=context_window)

    html = render.to_html(
        tree,
        title=title or "Prompt Flamegraph",
        cost_per_token=cost_per_token,
        waste_report=waste_report,
        width=width,
        height=height,
    )
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(html)
    return html
