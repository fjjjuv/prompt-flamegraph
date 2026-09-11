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

from prompt_flamegraph.core import build_tree
from prompt_flamegraph.terminal import to_terminal


def _tree(data):
    return build_tree(data, tokenizer="words")


def test_ascii_render_contains_names_tokens_pct(capsys):
    tree = _tree({"alpha": "one two three", "beta": "four five"})
    to_terminal(tree, title="Test", use_rich=False, width=120)
    out = capsys.readouterr().out
    assert "alpha" in out and "beta" in out
    assert "Total tokens" in out
    assert re.search(r"\(\s*\d+\.\d%\)", out)


def test_ascii_render_no_ansi_when_piped(capsys):
    # capsys is not a tty, so no ANSI escapes should be emitted.
    tree = _tree({"alpha": "one two", "beta": "three"})
    to_terminal(tree, use_rich=False, width=120)
    assert "\x1b[" not in capsys.readouterr().out


def test_ascii_render_truncates_long_names(capsys):
    tree = _tree({"x" * 40: "hello world"})
    to_terminal(tree, use_rich=False, width=120)
    out = capsys.readouterr().out
    assert "x" * 25 in out
    assert "x" * 26 not in out


def test_ascii_render_percent_of_total_not_parent(capsys):
    # 'only' is the sole child of 'a' (100% of parent) but ~0.5% of total.
    tree = _tree({"a": {"only": "x"}, "b": "y " * 100})
    to_terminal(tree, use_rich=False, width=120)
    out = capsys.readouterr().out
    line = next(ln for ln in out.splitlines() if "only" in ln)
    pct = float(re.search(r"\((\s*\d+\.\d)%\)", line).group(1))
    assert pct < 5.0


def test_ascii_render_strips_ansi_from_names(capsys):
    tree = _tree({"evil\x1b[31mname": "hi there"})
    to_terminal(tree, use_rich=False, width=120)
    out = capsys.readouterr().out
    assert "\x1b" not in out
    assert "evil" in out


def test_ascii_render_empty_tree(capsys):
    to_terminal(_tree({}), use_rich=False, width=120)
    out = capsys.readouterr().out
    assert "(no categories)" in out


def test_ascii_render_tiny_width(capsys):
    tree = _tree({"a": "one two", "b": "three"})
    to_terminal(tree, use_rich=False, width=10)
    assert "a" in capsys.readouterr().out


def test_rich_render_smoke(capsys):
    pytest.importorskip("rich")
    tree = _tree({"a": "one two", "b": {"c": "three four"}})
    to_terminal(tree, use_rich=True, width=120)
    out = capsys.readouterr().out
    assert "a" in out and "Total" in out


def test_rich_render_strips_control_chars(capsys):
    pytest.importorskip("rich")
    tree = _tree({"bad\x1b[31mname": "hi there"})
    to_terminal(tree, use_rich=True, width=120)
    assert "\x1b" not in capsys.readouterr().out


def test_rich_render_empty_tree(capsys):
    pytest.importorskip("rich")
    to_terminal(_tree({}), use_rich=True, width=120)
    assert "(no categories)" in capsys.readouterr().out
