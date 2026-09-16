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

"""Core logic: token counting and tree building."""

from __future__ import annotations

import json
import re
import sys
import threading
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator


@dataclass
class Node:
    name: str
    tokens: int
    children: list[Node] = field(default_factory=list)
    text: str | None = None
    change: str | None = None  # 'added', 'removed', 'same', 'changed'
    delta: int = 0

    def __repr__(self) -> str:
        parts = (
            f"name={self.name!r}, tokens={self.tokens}, "
            f"children={len(self.children)}"
        )
        if self.change is not None:
            parts += f", change={self.change!r}"
        return f"Node({parts})"

    @property
    def is_leaf(self) -> bool:
        return not self.children


Tokenizer = Callable[[str], int]


def _run_deep(fn: Callable[[], Any], depth: int) -> Any:
    """Call ``fn()`` when its recursion scales with ``depth`` tree levels.

    Recursive encoders/renderers (the C ``json`` accelerator, the HTML
    renderer with aggregation off) consume real C stack per level. The
    default ~1MB thread stack dies around a few thousand levels — and on
    Python <3.12 every Python frame also eats C stack. A fatal stack
    overflow kills the whole process, so deep work runs in a worker
    thread given a stack sized for the depth.
    """
    # The C JSON encoder spends several recursion units per level (~7 seen
    # on 3.13) — leave a fat margin so the limit never binds before the
    # (huge) worker stack does.
    needed = depth * 50 + 10_000
    if needed <= sys.getrecursionlimit():
        return fn()
    old_limit = sys.getrecursionlimit()
    old_stack = threading.stack_size()
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            box["r"] = fn()
        except BaseException as exc:  # re-raised in the caller thread
            box["e"] = exc

    sys.setrecursionlimit(needed)
    try:
        # ~64KB of stack per level comfortably covers the worst encoder.
        try:
            threading.stack_size(min(1024 << 20, max(128 << 20, depth * 64 << 10)))
        except (ValueError, RuntimeError):
            pass  # platform refused the size — the default stack still helps
        t = threading.Thread(target=work, daemon=True)
        t.start()
        t.join()
    finally:
        threading.stack_size(old_stack)
        sys.setrecursionlimit(old_limit)
    if "e" in box:
        raise box["e"]
    return box["r"]


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

    try:
        enc = tiktoken.get_encoding(encoding)
    except ValueError as e:
        raise ValueError(f"unknown tiktoken encoding: {encoding}") from e

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

    if not isinstance(tokenizer, str):
        raise TypeError(
            f"tokenizer must be a string name or a callable, "
            f"got {type(tokenizer).__name__}"
        )

    name = tokenizer.strip().lower()

    if name.startswith("model:"):
        from .models import resolve_model

        spec = resolve_model(name[len("model:"):])
        if spec.encoding == "estimate":
            return _default_count
        tiktoken_count = _load_tiktoken(spec.encoding)
        if tiktoken_count is None:
            raise ImportError(
                f"tiktoken is not installed but model {spec.name!r} uses the "
                f"{spec.encoding} encoding. Run 'pip install prompt-flamegraph[tiktoken]'"
            )
        return tiktoken_count

    if name == "tiktoken" or name in ("cl100k", "cl100k_base"):
        tiktoken_count = _load_tiktoken()
        if tiktoken_count is None:
            raise ImportError(
                "tiktoken is not installed. Run 'pip install prompt-flamegraph[tiktoken]'"
            )
        return tiktoken_count

    if name in ("o200k", "o200k_base"):
        tiktoken_count = _load_tiktoken("o200k_base")
        if tiktoken_count is None:
            raise ImportError(
                "tiktoken is not installed. Run 'pip install prompt-flamegraph[tiktoken]'"
            )
        return tiktoken_count

    if name == "words":
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
        # OpenAI tool shape: {"type": "function", "function": {"name": ...}}
        nested = value.get("function")
        if isinstance(nested, dict):
            candidate = nested.get("name")
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    return f"item_{index}"


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (set, frozenset)):
        # Sets are unordered and not JSON-serializable; emit a sorted
        # JSON list of reprs so output is deterministic.
        return json.dumps(sorted(repr(v) for v in value), ensure_ascii=False)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)


_MAX_DEPTH = 500
_CONTAINER_TYPES = (dict, list, tuple)


def _resolve_count_fn(
    tokenizer: Tokenizer | str | None,
    model: str | None,
    _count_fn: Callable[[str], int] | None,
) -> Callable[[str], int]:
    if _count_fn is not None:
        return _count_fn
    if model is not None:
        if tokenizer is not None:
            raise ValueError("model and tokenizer are mutually exclusive")
        from .models import resolve_model

        spec = resolve_model(model)
        try:
            return get_tokenizer(f"model:{spec.name}")
        except ImportError:
            warnings.warn(
                f"tiktoken is not installed; using the default estimator for "
                f"model {spec.name!r} (counts will be approximate)",
                stacklevel=3,
            )
            return _default_count
    return get_tokenizer(tokenizer)


def _child_items(value: Any) -> Iterator[tuple[Any, Any]]:
    """Yield (child_name, child_value) pairs for a dict/list/tuple."""
    if isinstance(value, dict):
        return iter(value.items())
    return iter((_guess_name(item, i), item) for i, item in enumerate(value))


def build_tree(
    data: Any,
    name: str = "prompt",
    tokenizer: Tokenizer | str | None = None,
    model: str | None = None,
    _count_fn: Callable[[str], int] | None = None,
) -> Node:
    """Build a token tree from a nested dict/list/string (iterative).

    Raises ValueError for nesting deeper than 500 levels or circular
    references in dict/list/tuple containers."""
    count_fn = _resolve_count_fn(tokenizer, model, _count_fn)
    root = Node(name=name, tokens=0)
    active: set[int] = set()  # ids of containers on the current path
    # Stack frames: [value, node, depth, child-iterator].
    stack: list[list[Any]] = []

    def push(value: Any, node: Node, depth: int) -> None:
        if depth > _MAX_DEPTH:
            raise ValueError("input nested deeper than 500 levels")
        if isinstance(value, _CONTAINER_TYPES):
            vid = id(value)
            if vid in active:
                raise ValueError("circular reference in prompt data")
            active.add(vid)
            stack.append([value, node, depth, _child_items(value)])
        else:
            node.text = _to_text(value)
            tokens = count_fn(node.text)
            if isinstance(tokens, bool) or not isinstance(tokens, (int, float)):
                raise TypeError(
                    f"tokenizer returned {type(tokens).__name__} "
                    f"({tokens!r}); expected a numeric token count"
                )
            node.tokens = max(0, int(tokens))

    push(data, root, 1)
    while stack:
        value, node, depth, items = stack[-1]
        try:
            child_name, child_value = next(items)
        except StopIteration:
            active.discard(id(value))
            node.tokens = sum(child.tokens for child in node.children)
            stack.pop()
            continue
        child = Node(
            name=child_name if isinstance(child_name, str) else str(child_name),
            tokens=0,
        )
        node.children.append(child)
        push(child_value, child, depth + 1)
    return root


def flatten_tree(node: Node) -> list[Node]:
    """Return a flat list of all nodes in depth-first order (iterative)."""
    out: list[Node] = []
    stack = [node]
    while stack:
        current = stack.pop()
        out.append(current)
        stack.extend(reversed(current.children))
    return out


def profile_prompt(
    data: Any,
    output: str | None = "prompt_flamegraph.html",
    title: str | None = None,
    tokenizer: Tokenizer | str | None = None,
    model: str | None = None,
    cost_per_token: float | None = None,
    detect_waste: bool = True,
    context_window: int | None = None,
    width: int = 1200,
    height: int = 720,
) -> str:
    """Build a prompt token tree and render it to a standalone HTML flamegraph."""
    from . import render

    if model is not None:
        if tokenizer is not None:
            raise ValueError("model and tokenizer are mutually exclusive")
        from .models import resolve_model

        spec = resolve_model(model)
        if cost_per_token is None:
            cost_per_token = spec.input_per_mtok / 1e6
        if context_window is None:
            context_window = spec.context_window

    tree = build_tree(data, tokenizer=tokenizer, model=model)
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
