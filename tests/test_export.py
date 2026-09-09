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

from prompt_flamegraph.core import build_tree
from prompt_flamegraph.export import to_markdown, to_svg


def test_to_svg_contains_rects():
    data = {"system_prompt": "hello", "tools": [{"name": "a"}]}
    tree = build_tree(data)
    svg = to_svg(tree, title="Test SVG")
    assert svg.startswith("<?xml")
    assert "<rect" in svg
    assert "Test SVG" in svg


def test_to_markdown_contains_table():
    data = {"system_prompt": "hello", "tools": [{"name": "a"}]}
    tree = build_tree(data)
    md = to_markdown(tree, title="Test MD", cost_per_token=1e-6)
    assert md.startswith("# Test MD")
    assert "| Path |" in md
    assert "system_prompt" in md
