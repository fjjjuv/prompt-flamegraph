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

"""Detect token waste in a prompt tree."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .core import Node


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


def detect_waste(tree: Node) -> WasteReport:
    """Analyze a prompt tree and report token waste and suspicious categories."""
    leaves = _collect_leaves(tree, ())
    findings: list[Finding] = []

    findings.extend(_find_duplicates(leaves))
    _check_category(tree, tree.tokens, findings)

    wasted = sum(f.tokens_wasted for f in findings)
    return WasteReport(total_tokens=tree.tokens, wasted_tokens=wasted, findings=findings)
