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
from prompt_flamegraph.diff import build_diff_tree, diff_prompts
from tempfile import TemporaryDirectory
from pathlib import Path


def test_build_diff_tree_detects_added():
    v1 = {"system_prompt": "hello", "tools": [{"name": "a"}]}
    v2 = {"system_prompt": "hello", "tools": [{"name": "a"}, {"name": "b"}]}
    t1 = build_tree(v1, name="prompt")
    t2 = build_tree(v2, name="prompt")
    diff = build_diff_tree(t1, t2)
    assert diff.tokens > 0
    names = {c.name: c.change for c in diff.children}
    assert names.get("tools") in ("changed", "same")


def test_diff_prompts_writes_html():
    with TemporaryDirectory() as tmp:
        out = Path(tmp) / "diff.html"
        v1 = {"system_prompt": "hello"}
        v2 = {"system_prompt": "hello", "extra": "world"}
        html = diff_prompts(v1, v2, output=str(out), title="Diff")
        assert out.exists()
        assert "Diff" in html
