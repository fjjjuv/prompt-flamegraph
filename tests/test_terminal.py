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
import sys

import pytest

from prompt_flamegraph.core import Node, build_tree
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


def test_ascii_render_cost_per_token_zero(capsys):
    # 0.0 is a valid per-token price, not "no price given".
    tree = _tree({"a": "one two"})
    to_terminal(tree, use_rich=False, width=120, cost_per_token=0.0)
    assert "Estimated cost: $0.000000" in capsys.readouterr().out


def test_format_number_negative():
    from prompt_flamegraph.terminal import _format_number

    assert _format_number(-1_500_000) == "-1.50M"
    assert _format_number(-1500) == "-1.5k"
    assert _format_number(-5) == "-5"
    assert _format_number(1500) == "1.5k"


def test_ascii_render_strips_format_chars(capsys):
    # Zero-width and bidi format chars (category Cf) are stripped too.
    tree = _tree({"evil\u200bname\u202e": "hi there"})
    to_terminal(tree, use_rich=False, width=120)
    out = capsys.readouterr().out
    assert "\u200b" not in out and "\u202e" not in out
    assert "evilname" in out


def test_ascii_render_truncates_by_display_cells(capsys):
    # CJK chars are 2 cells each: 13 chars = 26 cells > 25-cell column.
    tree = _tree({"界" * 13: "hello world"})
    to_terminal(tree, use_rich=False, width=120)
    out = capsys.readouterr().out
    assert "界" * 12 in out
    assert "界" * 13 not in out


def test_ascii_render_wide_name_column_alignment(capsys):
    # A wide name is padded to the same token column as an ASCII name.
    from prompt_flamegraph.terminal import _disp_width

    tree = _tree({"界": "a b c", "xx": "d e f"})
    to_terminal(tree, use_rich=False, width=120)
    lines = {
        ln.split()[0]: ln
        for ln in capsys.readouterr().out.splitlines()
        if "界" in ln or ln.strip().startswith("xx")
    }
    wide_col = _disp_width(lines["界"][: lines["界"].index("3")])
    ascii_col = _disp_width(lines["xx"][: lines["xx"].index("3")])
    assert wide_col == ascii_col


def test_ascii_render_indent_capped(capsys):
    # Beyond 10 levels the indent stops growing and gets a '… ' marker.
    data = {}
    cur = data
    for i in range(15):
        cur[f"d{i}"] = {}
        cur = cur[f"d{i}"]
    cur["leaf"] = "hello world"
    to_terminal(_tree(data), use_rich=False, width=200)
    out = capsys.readouterr().out
    leaf = next(ln for ln in out.splitlines() if "leaf" in ln)
    assert leaf.startswith("  " * 10 + "… ")
    d10 = next(ln for ln in out.splitlines() if "d10" in ln)
    assert "…" not in d10
    d11 = next(ln for ln in out.splitlines() if "d11" in ln)
    assert "… " in d11


def test_ascii_render_bar_capped_on_huge_terminal(capsys):
    tree = _tree({"a": "one two", "b": "three four five"})
    to_terminal(tree, use_rich=False, width=10000)
    line = next(
        ln for ln in capsys.readouterr().out.splitlines() if "█" in ln
    )
    assert line.count("█") <= 100


def test_ascii_render_zero_token_bar_no_color(capsys, monkeypatch):
    # With color on, an empty bar must not emit stray color/reset codes.
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    tree = Node(
        name="root",
        tokens=10,
        children=[Node(name="empty", tokens=0), Node(name="full", tokens=10)],
    )
    to_terminal(tree, use_rich=False, width=120)
    out = capsys.readouterr().out
    empty = next(ln for ln in out.splitlines() if "empty" in ln)
    assert "\x1b[" not in empty
    full = next(ln for ln in out.splitlines() if "full" in ln)
    assert "\x1b[" in full


def test_ascii_render_diff_shows_delta_and_removed(capsys):
    from prompt_flamegraph.diff import build_diff_tree

    v1 = _tree({"keep": "a b c", "gone": "x y z"})
    v2 = _tree({"keep": "a b c", "new": "p q r s"})
    to_terminal(build_diff_tree(v1, v2), use_rich=False, width=120)
    out = capsys.readouterr().out
    assert "(+4)" in out  # 'new' added
    assert "(-3)" in out  # 'gone' removed
    removed = next(ln for ln in out.splitlines() if "gone" in ln)
    assert "- gone" in removed


def test_rich_render_cost_per_token_zero(capsys):
    pytest.importorskip("rich")
    to_terminal(_tree({"a": "one two"}), use_rich=True, cost_per_token=0.0)
    assert "$0.000000" in capsys.readouterr().out
