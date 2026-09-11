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

"""Detect token waste in a prompt tree."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from .core import Node

_NGRAM_MAX_LEAVES = 300
_SHINGLE_K = 5
_SHINGLE_THRESHOLD = 0.9


@dataclass
class Finding:
    kind: str
    path: str
    message: str
    tokens_wasted: int


@dataclass
class WasteReport:
    total_tokens: int
    wasted_tokens: int
    findings: list[Finding]

    @property
    def waste_ratio(self) -> float:
        if self.total_tokens <= 0:
            return 0.0
        return self.wasted_tokens / self.total_tokens


def _collect_leaves(node: Node, path: list[str]) -> list[tuple[str, ...]]:
    leaves: list[tuple[str, ...]] = []
    current = (*path, node.name)
    if node.is_leaf:
        leaves.append((current, node.text or "", node.tokens))
    else:
        for child in node.children:
            leaves.extend(_collect_leaves(child, current))
    return leaves


def _find_duplicates(leaves: list[tuple[tuple[str, ...], str, int]]) -> list[Finding]:
    groups: dict[str, list[tuple[tuple[str, ...], int]]] = defaultdict(list)
    for path, text, tokens in leaves:
        if tokens < 2:
            continue
        groups[text].append((path, tokens))

    findings: list[Finding] = []
    for text, items in groups.items():
        if len(items) < 2:
            continue
        total_wasted = sum(tokens for _, tokens in items[:-1])
        paths = " / ".join("/".join(p) for p, _ in items)
        snippet = text[:80].replace("\n", " ")
        if len(text) > 80:
            snippet += "…"
        findings.append(
            Finding(
                kind="duplicate",
                path=paths,
                message=f"{len(items)}× duplicate text ({snippet!r}) — keep only one",
                tokens_wasted=total_wasted,
            )
        )
    return findings


def _normalize(text: str) -> str:
    """Collapse whitespace, lowercase and strip punctuation."""
    text = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE)
    return " ".join(text.split())


def _shingles(text: str) -> set[tuple[str, ...]]:
    """Word-level 5-gram shingle set of a normalized text."""
    words = _normalize(text).split()
    if len(words) < _SHINGLE_K:
        return {tuple(words)} if words else set()
    return {tuple(words[i : i + _SHINGLE_K]) for i in range(len(words) - _SHINGLE_K + 1)}


def _near_dup_finding(items: list[tuple[tuple[str, ...], str, int]]) -> Finding:
    total_wasted = sum(t for _, _, t in items) - max(t for _, _, t in items)
    paths = " / ".join("/".join(p) for p, _, _ in items)
    snippet = items[0][1][:80].replace("\n", " ")
    if len(items[0][1]) > 80:
        snippet += "…"
    return Finding(
        kind="near_duplicate",
        path=paths,
        message=f"{len(items)}× near-duplicate text ({snippet!r}) — keep only one",
        tokens_wasted=total_wasted,
    )


def _find_near_duplicates(
    leaves: list[tuple[tuple[str, ...], str, int]],
) -> list[Finding]:
    findings: list[Finding] = []
    flagged: set[int] = set()

    # Identical after normalization (whitespace, case, punctuation differences).
    groups: dict[str, list[int]] = defaultdict(list)
    for i, (_, text, tokens) in enumerate(leaves):
        if tokens < 2:
            continue
        key = _normalize(text)
        if key:
            groups[key].append(i)
    for idxs in groups.values():
        if len(idxs) < 2:
            continue
        flagged.update(idxs)
        if len({leaves[i][1] for i in idxs}) > 1:
            findings.append(_near_dup_finding([leaves[i] for i in idxs]))

    # Shared 5-gram shingles; skipped when there are too many leaves to compare.
    if len(leaves) <= _NGRAM_MAX_LEAVES:
        shingle_sets = [
            _shingles(text) if i not in flagged and tokens >= 2 else set()
            for i, (_, text, tokens) in enumerate(leaves)
        ]
        parent = list(range(len(leaves)))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        candidates = [i for i, s in enumerate(shingle_sets) if s]
        for pos, i in enumerate(candidates):
            for j in candidates[pos + 1 :]:
                a, b = shingle_sets[i], shingle_sets[j]
                shared = len(a & b)
                if shared and shared / len(a | b) >= _SHINGLE_THRESHOLD:
                    parent[find(i)] = find(j)

        unions: dict[int, list[int]] = defaultdict(list)
        for i in candidates:
            unions[find(i)].append(i)
        for idxs in unions.values():
            if len(idxs) >= 2:
                findings.append(_near_dup_finding([leaves[i] for i in idxs]))

    return findings


def _check_category(node: Node, total: int, findings: list[Finding]) -> None:
    if total <= 0:
        return
    for child in node.children:
        pct = (child.tokens / total) * 100
        if child.name == "system_prompt" and pct > 35:
            findings.append(
                Finding(
                    kind="large_system_prompt",
                    path="/system_prompt",
                    message=f"system prompt is {pct:.1f}% of the total context ({child.tokens} tokens)",
                    tokens_wasted=0,
                )
            )
        elif child.name == "chat_history" and pct > 30:
            findings.append(
                Finding(
                    kind="long_history",
                    path="/chat_history",
                    message=f"chat history is {pct:.1f}% of the total context ({child.tokens} tokens) — consider truncation",
                    tokens_wasted=0,
                )
            )
        elif child.name == "tools" and len(child.children) > 5:
            findings.append(
                Finding(
                    kind="too_many_tools",
                    path="/tools",
                    message=f"{len(child.children)} tools defined — only declare the ones the model actually calls",
                    tokens_wasted=0,
                )
            )
        elif child.name == "rag_context" and pct > 50:
            findings.append(
                Finding(
                    kind="huge_rag",
                    path="/rag_context",
                    message=f"RAG context is {pct:.1f}% of the total context ({child.tokens} tokens) — trim chunks",
                    tokens_wasted=0,
                )
            )


def detect_waste(tree: Node, context_window: int | None = None) -> WasteReport:
    """Analyze a prompt tree and report token waste and suspicious categories."""
    leaves = _collect_leaves(tree, ())
    findings: list[Finding] = []

    findings.extend(_find_duplicates(leaves))
    findings.extend(_find_near_duplicates(leaves))
    _check_category(tree, tree.tokens, findings)

    if context_window and context_window > 0:
        pct = (tree.tokens / context_window) * 100
        if pct > 95:
            findings.append(
                Finding(
                    kind="context_window",
                    path=f"/{tree.name}",
                    message=f"prompt uses {pct:.1f}% of the {context_window}-token context window — hard truncation risk",
                    tokens_wasted=0,
                )
            )
        elif pct > 80:
            findings.append(
                Finding(
                    kind="context_window",
                    path=f"/{tree.name}",
                    message=f"prompt uses {pct:.1f}% of the {context_window}-token context window — consider trimming",
                    tokens_wasted=0,
                )
            )

    wasted = sum(f.tokens_wasted for f in findings)
    return WasteReport(total_tokens=tree.tokens, wasted_tokens=wasted, findings=findings)
