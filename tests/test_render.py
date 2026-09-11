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

import re

import pytest

from prompt_flamegraph.core import Node, build_tree
from prompt_flamegraph.render import _money, to_html
from prompt_flamegraph.waste import Finding, WasteReport


def _script_section(html: str) -> str:
    m = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert m is not None
    return m.group(1)


def _tree() -> Node:
    return Node(name="root", tokens=10, children=[Node(name="a", tokens=10)])


def test_to_html_basic_structure():
    out = to_html(build_tree({"system_prompt": "hello"}))
    assert out.startswith("<!DOCTYPE html>")
    assert 'class="pf-flamegraph"' in out
    assert "system_prompt" in out


def test_tooltip_name_xss_escaped():
    evil = "<img src=x onerror=alert(1)>"
    tree = Node(name="root", tokens=10, children=[Node(name=evil, tokens=10)])
    out = to_html(tree)
    # The raw payload must never reach the document unescaped.
    assert evil not in out
    assert "&lt;img src=x onerror=alert(1)&gt;" in out  # escaped data-name
    script = _script_section(out)
    # The tooltip is built with DOM APIs, never innerHTML with user text.
    assert "onerror" not in script
    assert "innerHTML" not in script
    assert "textContent" in script


def test_data_change_attribute_escaped():
    tree = Node(
        name="root",
        tokens=10,
        children=[Node(name="c", tokens=10, change='"><script>alert(1)</script>')],
    )
    out = to_html(tree)
    assert '"><script>' not in out
    assert "data-change=\"&quot;&gt;&lt;script&gt;" in out


def test_finding_kind_escaped_in_class():
    report = WasteReport(
        total_tokens=10,
        wasted_tokens=0,
        findings=[Finding(kind='"><b>', path="/x", message="m", tokens_wasted=0)],
    )
    out = to_html(_tree(), waste_report=report)
    assert 'pf-finding--"><b>' not in out
    assert "pf-finding--&quot;&gt;" in out


def test_nan_cost_per_token_emits_null():
    out = to_html(_tree(), cost_per_token=float("nan"))
    script = _script_section(out)
    assert "const costPerToken = null;" in script
    assert "nan" not in script.lower()
    assert "Estimated cost" not in out


def test_inf_cost_per_token_emits_null():
    out = to_html(_tree(), cost_per_token=float("inf"))
    script = _script_section(out)
    assert "const costPerToken = null;" in script
    assert "Estimated cost" not in out


def test_zero_cost_per_token_still_emit():
    out = to_html(_tree(), cost_per_token=0.0)
    assert "const costPerToken = 0.0;" in _script_section(out)
    assert "Estimated cost:" in out


def test_width_height_str_coerced():
    out = to_html(_tree(), width="900", height="300")
    assert "max-width: 900px" in out
    assert "height: 300px" in out


def test_child_width_capped_at_100():
    # Diff trees can produce children summing past 100% of the parent.
    tree = Node(
        name="root",
        tokens=100,
        children=[Node(name="big", tokens=150, change="added", delta=150)],
    )
    out = to_html(tree)
    assert "width:150" not in out
    assert "width:100.0%" in out


def test_leaf_text_data_attr_truncated_and_escaped():
    tree = Node(
        name="root",
        tokens=10,
        children=[Node(name="leaf", tokens=10, text="x" * 300)],
    )
    out = to_html(tree)
    assert 'data-text="' + "x" * 200 + "…" in out
    assert "x" * 201 not in out

    tree2 = Node(
        name="root",
        tokens=10,
        children=[Node(name="leaf", tokens=10, text="<b>bold</b>")],
    )
    out2 = to_html(tree2)
    assert 'data-text="&lt;b&gt;bold&lt;/b&gt;"' in out2
    assert 'data-text="<b>' not in out2


def test_money_edge_cases():
    assert _money(0) == "$0.00"
    assert _money(1e-9) == "$<0.000001"
    assert _money(-0.005) == "-$0.005"
    assert _money(-1234.5) == "-$1,234.5"
    assert _money(float("nan")) == "-"
    assert _money(float("inf")) == "-"
    assert _money(2.0) == "$2"
    assert _money(0.5) == "$0.5"
