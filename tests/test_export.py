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

import json
import re

import pytest

from prompt_flamegraph.core import Node, build_tree
from prompt_flamegraph.export import to_json, to_markdown, to_svg
from prompt_flamegraph.waste import detect_waste


def test_to_svg_contains_rects():
    data = {"system_prompt": "hello", "tools": [{"name": "a"}]}
    tree = build_tree(data)
    svg = to_svg(tree, title="Test SVG")
    assert svg.startswith("<?xml")
    assert "<rect" in svg
    assert "Test SVG" in svg


def test_to_svg_rect_widths_proportional():
    tree = Node(
        name="root",
        tokens=100,
        children=[
            Node(name="half", tokens=50),
            Node(name="quarter_a", tokens=25),
            Node(name="quarter_b", tokens=25),
        ],
    )
    width = 1000
    svg = to_svg(tree, width=width)
    rects = [
        (float(x), float(w))
        for x, w in re.findall(r'<rect x="([\d.]+)" y="\d+" width="([\d.]+)"', svg)
    ]
    assert len(rects) == 4
    root = rects[0]
    assert root[1] == pytest.approx(width)
    widths = sorted(w for _, w in rects[1:])
    assert widths[0] == pytest.approx(width / 4, abs=1)
    assert widths[2] == pytest.approx(width / 2, abs=1)
    # children tile horizontally within their parent's span
    assert all(0 <= x and x + w <= width + 0.01 for x, w in rects)


def test_to_json_structure():
    data = {"system_prompt": "hello", "tools": [{"name": "a"}]}
    tree = build_tree(data)
    payload = json.loads(to_json(tree, title="T", cost_per_token=1e-6))
    assert payload["title"] == "T"
    assert payload["total_tokens"] == tree.tokens
    assert payload["cost_usd"] == pytest.approx(tree.tokens * 1e-6)
    assert payload["waste"] is None
    assert payload["tree"]["name"] == tree.name
    assert payload["tree"]["tokens"] == tree.tokens
    names = {c["name"] for c in payload["tree"]["children"]}
    assert names == {"system_prompt", "tools"}


def test_to_json_waste_report():
    data = {
        "system_prompt": "hello world",
        "rag_context": {"doc_1": "hello world", "doc_2": "hello world"},
    }
    tree = build_tree(data)
    report = detect_waste(tree)
    payload = json.loads(to_json(tree, waste_report=report))
    assert payload["cost_usd"] is None
    assert payload["waste"]["total_tokens"] == report.total_tokens
    assert payload["waste"]["wasted_tokens"] == report.wasted_tokens
    assert payload["waste"]["findings"][0]["kind"] == "duplicate"


def test_to_markdown_contains_table():
    data = {"system_prompt": "hello", "tools": [{"name": "a"}]}
    tree = build_tree(data)
    md = to_markdown(tree, title="Test MD", cost_per_token=1e-6)
    assert md.startswith("# Test MD")
    assert "| Path |" in md
    assert "system_prompt" in md
