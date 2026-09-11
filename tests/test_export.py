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
import xml.etree.ElementTree as ET

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


def test_to_svg_ampersand_name_produces_valid_xml():
    tree = Node(
        name="root",
        tokens=10,
        children=[Node(name="&" * 30, tokens=10)],
    )
    svg = to_svg(tree, width=1000)
    # Truncating the *escaped* name could split "&amp;" into malformed XML.
    ET.fromstring(svg.encode("utf-8"))  # must not raise
    assert "&amp;" * 22 + "…" in svg  # truncated raw, then escaped


def test_to_svg_deep_tree_no_recursion_error():
    root = node = Node(name="n0", tokens=1)
    for i in range(1, 2000):
        child = Node(name=f"n{i}", tokens=1)
        node.children = [child]
        node = child
    svg = to_svg(root)
    assert svg.startswith("<?xml")


def test_to_svg_aggregates_tiny_children():
    tree = Node(
        name="root",
        tokens=1000,
        children=[
            Node(name="big", tokens=900),
            Node(name="tiny_a", tokens=5),
            Node(name="mid", tokens=90),
            Node(name="tiny_b", tokens=5),
        ],
    )
    svg = to_svg(tree, width=1000)
    # 5px children (< 2% of the parent's 1000px) merge into one bucket.
    assert "· 2 more ·" in svg
    assert "· 2 more ·: 10 tokens" in svg  # summed tokens
    # Aggregated children are listed in the bucket's hover title...
    assert "tiny_a: 5 tokens" in svg
    assert "tiny_b: 5 tokens" in svg
    # ...but they get no bar/title of their own (real titles carry a pct).
    assert "tiny_a: 5 tokens (0.50%)" not in svg
    assert "tiny_b: 5 tokens (0.50%)" not in svg
    rects = [
        (float(x), float(w))
        for x, w in re.findall(r'<rect x="([\d.]+)" y="\d+" width="([\d.]+)"', svg)
    ]
    assert len(rects) == 4  # root + big + mid + aggregate bucket
    # The bucket trails at the right edge of the parent's span.
    assert any(x == pytest.approx(990) and w == pytest.approx(10) for x, w in rects)


def test_to_svg_max_depth_aggregates_deeper_nodes():
    root = node = Node(name="n0", tokens=100)
    for i in range(1, 20):
        child = Node(name=f"n{i}", tokens=100)
        node.children = [child]
        node = child
    svg = to_svg(root, max_depth=3)
    # Real bars for n0..n3 only; everything deeper collapses into one bucket.
    assert len(re.findall(r'<rect x="', svg)) == 5
    assert "· 1 more ·" in svg
    for i in range(4, 20):
        assert f"<title>n{i}:" not in svg  # no per-node hover title
    # Height is capped too: 4 real rows + 1 aggregate row.
    assert 'height="250"' in svg


def test_to_svg_labels_fit_width():
    tree = Node(
        name="root",
        tokens=1000,
        children=[
            Node(name="wide_child", tokens=700),  # 700px
            Node(name="medium_node", tokens=100),  # 100px
            # 27px: drawn (>= 26px floor, >= 2% of parent) but too narrow
            # for a label (< 30px _MIN_LABEL_PX).
            Node(name="sliver", tokens=27),
            Node(name="rest", tokens=173),  # 173px
        ],
    )
    svg = to_svg(tree, width=1000)
    texts = re.findall(r"<text[^>]*>([^<]*)</text>", svg)
    # Wide bar: "name — tokens" fits.
    assert "wide_child — 700" in texts
    # Medium bar: name only (full label wouldn't fit).
    assert "medium_node" in texts
    assert not any("medium_node —" in t for t in texts)
    # Sliver: own bar + full hover title, but no text label.
    assert "<title>sliver: 27 tokens" in svg
    assert not any("sliver" in t for t in texts)


def test_to_markdown_escapes_pipes_and_newlines():
    tree = Node(
        name="root",
        tokens=10,
        children=[
            Node(name="a|b", tokens=5),
            Node(name="line\nbreak", tokens=5),
        ],
    )
    md = to_markdown(tree, title="T|X\nY")
    assert md.startswith("# T\\|X Y")
    rows = [l for l in md.splitlines() if l.startswith("|") and not l.startswith("|-")]
    assert len(rows) == 3  # header + exactly one row per node
    assert "| a\\|b |" in md
    assert "| line break |" in md
    assert "a|b" not in md.replace("a\\|b", "")  # no unescaped pipe left


def test_to_markdown_zero_cost_per_token():
    tree = Node(name="root", tokens=10, children=[Node(name="a", tokens=10)])
    md = to_markdown(tree, cost_per_token=0.0)
    assert "- **Estimated cost:** $0.000000" in md
    assert "| a |" in md and "$0.000000" in md.split("| a |")[1]


def test_to_markdown_deep_tree_no_recursion_error():
    root = node = Node(name="n0", tokens=1)
    for i in range(1, 2000):
        child = Node(name=f"n{i}", tokens=1)
        node.children = [child]
        node = child
    md = to_markdown(root)
    assert md.count("\n|") >= 1999


def test_to_json_includes_leaf_text():
    tree = Node(
        name="root",
        tokens=5,
        children=[Node(name="leaf", tokens=5, text="hello world")],
    )
    payload = json.loads(to_json(tree))
    assert payload["tree"]["children"][0]["text"] == "hello world"
    assert "text" not in payload["tree"]


def test_to_json_zero_cost_per_token():
    tree = Node(name="root", tokens=10, children=[Node(name="a", tokens=10)])
    payload = json.loads(to_json(tree, cost_per_token=0.0))
    assert payload["cost_usd"] == 0.0


def test_to_json_deep_tree_no_recursion_error():
    root = node = Node(name="n0", tokens=1)
    for i in range(1, 2000):
        child = Node(name=f"n{i}", tokens=1)
        node.children = [child]
        node = child
    payload = json.loads(to_json(root))
    assert payload["tree"]["children"][0]["name"] == "n1"


def test_format_number_negative():
    from prompt_flamegraph.export import _format_number

    assert _format_number(-1500) == "-1.5k"
    assert _format_number(-2_500_000) == "-2.50M"
    assert _format_number(-5) == "-5"


def test_to_svg_aggregate_false_draws_slivers():
    tree = Node(
        name="root",
        tokens=1000,
        children=[Node(name="big", tokens=975), Node(name="tiny", tokens=25)],
    )
    svg = to_svg(tree, width=1000, aggregate=False)
    assert "<title>tiny: 25 tokens" in svg
    assert "· 1 more ·" not in svg
