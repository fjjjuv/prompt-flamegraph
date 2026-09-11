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

import io
import json
import sys
from pathlib import Path

import pytest

from prompt_flamegraph.cli import main


class _TTY(io.StringIO):
    def isatty(self) -> bool:
        return True


def _needs_to_json():
    import prompt_flamegraph.export as export

    if not hasattr(export, "to_json"):
        pytest.skip("export.to_json not available")


def test_no_input_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", _TTY(""))
    assert main([]) == 1
    assert "usage" in capsys.readouterr().out.lower()


def test_list_models(capsys):
    pytest.importorskip("prompt_flamegraph.models")
    assert main(["--list-models"]) == 0
    assert capsys.readouterr().out.strip()


def test_model_and_tokenizer_conflict():
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", "--model", "gpt-4o", "--tokenizer", "words"])
    assert excinfo.value.code != 0


def test_format_json(tmp_path: Path):
    _needs_to_json()
    src = tmp_path / "prompt.json"
    src.write_text(
        json.dumps({"system_prompt": "sys", "chat_history": ["hi", "hello"]}),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    assert main([str(src), "--format", "json", "-o", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(report, dict)


def test_format_json_no_waste(tmp_path: Path):
    _needs_to_json()
    src = tmp_path / "prompt.json"
    src.write_text(json.dumps({"chat_history": ["same", "same"]}), encoding="utf-8")
    out = tmp_path / "report.json"
    assert main([str(src), "--format", "json", "--no-waste", "-o", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report.get("waste") is None


def test_stdin_dash(monkeypatch, tmp_path: Path):
    _needs_to_json()
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    out = tmp_path / "o.json"
    assert main(["-", "--format", "json", "-o", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))


def test_stdin_implicit(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"system_prompt": "x"})))
    out = tmp_path / "o.svg"
    assert main(["--format", "svg", "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<?xml")


def test_demo_html(tmp_path: Path):
    out = tmp_path / "demo.html"
    assert main(["--demo", "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8").startswith("<!DOCTYPE html>")


def test_model_without_tiktoken(tmp_path: Path, capsys):
    models = pytest.importorskip("prompt_flamegraph.models")
    _needs_to_json()
    name = models.list_models()[0]
    out = tmp_path / "o.json"
    assert main(["--demo", "--model", name, "--format", "json", "-o", str(out)]) == 0
    err = capsys.readouterr().err
    assert "total:" in err and "model:" in err


def test_unknown_model_errors():
    pytest.importorskip("prompt_flamegraph.models")
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", "--model", "no-such-model-xyz"])
    assert excinfo.value.code != 0
