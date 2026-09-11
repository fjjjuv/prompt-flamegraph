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

import re

import pytest

from prompt_flamegraph.core import Node, build_tree
from prompt_flamegraph.render import _aggregate_node, _money, to_html
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
    assert "width: 100%; max-width: 900px" in out
    assert "max-height: 300px" in out


def test_graph_height_is_auto_capped_by_max_height():
    out = to_html(_tree(), height=300)
    graph_css = re.search(r"\.pf-graph \{([^}]*)\}", out).group(1)
    assert "height: auto" in graph_css
    assert "max-height: 300px" in graph_css
    # No fixed height remains on the graph box.
    assert "height: 300px" not in graph_css.replace("max-height: 300px", "")


def test_tiny_siblings_aggregated_into_more_bucket():
    children = [Node(name="big", tokens=980)]
    children += [Node(name=f"tiny_{i}", tokens=1) for i in range(20)]
    tree = Node(name="root", tokens=1000, children=children)
    out = to_html(tree)
    assert "· 20 more ·" in out
    # Summed tokens land on the aggregate's data attributes.
    assert 'data-tokens="20" data-pct-total="2.00"' in out
    # Hidden children are not rendered as their own bars…
    assert 'data-name="tiny_0"' not in out
    # …but the top few are listed in the aggregate tooltip payload.
    assert "tiny_0: 1 tokens" in out
    assert "and 15 more" in out
    # The visible sibling still renders normally.
    assert 'data-name="big"' in out


def test_aggregate_node_counts_everything_below_max_depth():
    # A chain one node wide and 15 levels deep: nothing is ever below the
    # sibling threshold, so only max_depth can collapse it.
    node = Node(name="deep_leaf", tokens=5)
    for i in range(15):
        node = Node(name=f"d{i}", tokens=5, children=[node])
    tree = Node(name="root", tokens=5, children=[node])
    out = to_html(tree, max_depth=3)
    # root + 3 rendered levels + 1 aggregate bar.
    assert out.count('<div class="pf-bar"') == 4
    assert out.count('<div class="pf-bar pf-bar--agg"') == 1
    assert "· 1 more ·" in out
    # Deepest names survive only inside the aggregate tooltip, not as bars.
    assert 'data-name="deep_leaf"' not in out
    assert "d11: 5 tokens" in out
    # Tokens still add up through the bucket.
    assert 'data-tokens="5"' in out


def test_deep_chain_default_max_depth_stays_bounded():
    node = Node(name="leaf", tokens=3)
    for i in range(50):
        node = Node(name=f"lvl{i}", tokens=3, children=[node])
    tree = Node(name="root", tokens=3, children=[node])
    out = to_html(tree)
    # root + 8 levels + aggregate bars — never 50 rows tall.
    assert out.count('<div class="pf-bar') < 15


def test_wide_bar_label_includes_tokens():
    tree = Node(name="root", tokens=100, children=[Node(name="sys", tokens=100)])
    out = to_html(tree, width=1200)
    assert "sys — 100" in out


def test_narrow_bar_label_truncated_to_width():
    # ~5% of ~1136px ≈ 56px → about 8 chars fit, so the label is clipped
    # relative to the bar rather than at a fixed character count.
    children = [Node(name="big", tokens=950), Node(name="a_very_long_name", tokens=50)]
    tree = Node(name="root", tokens=1000, children=children)
    out = to_html(tree, width=1200)
    assert "a_very_long_name —" not in out
    assert "a_very_…" in out
    # The full name still survives in the tooltip attributes.
    assert 'data-name="a_very_long_name"' in out


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


def test_aggregate_false_draws_every_node():
    children = [Node(name="big", tokens=980)]
    children += [Node(name=f"tiny_{i}", tokens=1) for i in range(20)]
    tree = Node(name="root", tokens=1000, children=children)
    out = to_html(tree, aggregate=False)
    assert "more ·" not in out
    assert 'data-name="tiny_0"' in out
    assert 'data-name="tiny_19"' in out


def test_aggregate_false_ignores_max_depth():
    node = Node(name="deep_leaf", tokens=5)
    for i in range(15):
        node = Node(name=f"d{i}", tokens=5, children=[node])
    tree = Node(name="root", tokens=5, children=[node])
    out = to_html(tree, max_depth=3, aggregate=False)
    assert 'data-name="deep_leaf"' in out


def test_max_depth_zero_or_negative_clamped_to_one():
    node = Node(name="leaf", tokens=5)
    for i in range(5):
        node = Node(name=f"d{i}", tokens=5, children=[node])
    tree = Node(name="root", tokens=5, children=[node])
    # Without the clamp, depth 0 >= max_depth collapses every child at once.
    assert to_html(tree, max_depth=0) == to_html(tree, max_depth=1)
    assert to_html(tree, max_depth=-3) == to_html(tree, max_depth=1)
    assert 'data-name="d4"' in to_html(tree, max_depth=0)


def test_width_zero_or_negative_clamped():
    assert "max-width: 200px" in to_html(_tree(), width=0)
    assert "max-width: 200px" in to_html(_tree(), width=-50)
    assert "max-width: 0px" not in to_html(_tree(), width=-50)


def test_width_capped_at_16384():
    out = to_html(_tree(), width=10**6)
    assert "max-width: 16384px" in out
    assert "max-width: 1000000px" not in out


def test_height_zero_or_negative_clamped():
    out = to_html(_tree(), height=0)
    assert "max-height: 100px" in re.search(r"\.pf-graph \{([^}]*)\}", out).group(1)
    out = to_html(_tree(), height=-10)
    assert "max-height: 100px" in re.search(r"\.pf-graph \{([^}]*)\}", out).group(1)


def test_aggregate_node_empty_members_raises():
    with pytest.raises(ValueError, match="empty member list"):
        _aggregate_node([])


def test_decimal_cost_per_token_coerced_to_float():
    from decimal import Decimal

    out = to_html(_tree(), cost_per_token=Decimal("0.1"))
    script = _script_section(out)
    # repr(Decimal) would emit Decimal('0.1') — invalid JS.
    assert "const costPerToken = 0.1;" in script
    assert "Decimal(" not in script
    assert "Estimated cost:" in out


def test_non_numeric_cost_per_token_emits_null():
    out = to_html(_tree(), cost_per_token=object())
    assert "const costPerToken = null;" in _script_section(out)
    assert "Estimated cost" not in out


def test_huge_int_cost_per_token_emits_null():
    out = to_html(_tree(), cost_per_token=10**400)
    assert "const costPerToken = null;" in _script_section(out)


def test_tooltip_position_clamped_to_viewport():
    script = _script_section(to_html(_tree()))
    assert "innerWidth" in script
    assert "innerHeight" in script
    assert "Math.min" in script
    assert "Math.max" in script


def test_tooltip_dataset_reads_have_defaults():
    script = _script_section(to_html(_tree()))
    assert "dataset.tokens || '0'" in script
    assert "dataset.pctTotal || '0'" in script
    assert "dataset.name || ''" in script


def test_bars_are_keyboard_focusable():
    out = to_html(_tree())
    assert 'tabindex="0"' in out
    assert 'aria-label="a, 10 tokens"' in out
    script = _script_section(out)
    assert "addEventListener('focus'" in script
    assert "addEventListener('blur'" in script


def test_children_row_allows_horizontal_overflow():
    out = to_html(_tree())
    css = re.search(r"\.pf-children \{([^}]*)\}", out).group(1)
    assert "overflow-x: auto" in css


def test_pct_total_clamped_to_100():
    # Diff trees can produce children larger than the total.
    tree = Node(
        name="root",
        tokens=100,
        children=[Node(name="big", tokens=150, change="added", delta=150)],
    )
    out = to_html(tree)
    assert 'data-pct-total="150.00"' not in out
    assert 'data-pct-total="100.00"' in out


def test_line_separators_stripped_from_data_attrs():
    tree = Node(
        name="root",
        tokens=10,
        children=[Node(name="a\u2028b\u2029c", tokens=10, text="x\u2028y")],
    )
    out = to_html(tree)
    assert "\u2028" not in out
    assert "\u2029" not in out
    assert 'data-name="a b c"' in out
    assert 'data-text="x y"' in out


def test_waste_rows_rendered_in_order():
    report = WasteReport(
        total_tokens=10,
        wasted_tokens=5,
        findings=[
            Finding(kind="dup", path="/a", message="first", tokens_wasted=3),
            Finding(kind="dup", path="/b", message="second", tokens_wasted=2),
        ],
    )
    out = to_html(_tree(), waste_report=report)
    assert out.count('class="pf-finding pf-finding--dup"') == 2
    assert out.index("first") < out.index("second")
