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


def test_update_models_flag(monkeypatch, tmp_path, capsys):
    import urllib.request

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("PROMPT_FLAMEGRAPH_OFFLINE", raising=False)

    class _Resp:
        def read(self):
            return json.dumps(
                {
                    "cli-remote-model": {
                        "input_cost_per_token": 1e-6,
                        "output_cost_per_token": 2e-6,
                        "max_tokens": 32_000,
                    }
                }
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: _Resp())
    assert main(["--update-models"]) == 0
    out = capsys.readouterr().out
    assert "1 models cached" in out
    assert "models.json" in out


def test_list_models_cache_footer(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.delenv("PROMPT_FLAMEGRAPH_OFFLINE", raising=False)

    assert main(["--list-models"]) == 0
    assert "bundled prices only" in capsys.readouterr().out

    cache = tmp_path / "prompt-flamegraph" / "models.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"fetched_at": 0, "models": {}}), encoding="utf-8")
    assert main(["--list-models"]) == 0
    assert "prices cached 0 days ago" in capsys.readouterr().out


def test_offline_flag_hides_cache(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    # Register teardown so the env var set by --offline does not leak.
    monkeypatch.delenv("PROMPT_FLAMEGRAPH_OFFLINE", raising=False)
    cache = tmp_path / "prompt-flamegraph" / "models.json"
    cache.parent.mkdir(parents=True)
    cache.write_text(
        json.dumps(
            {
                "fetched_at": 0,
                "models": {
                    "hidden-model": {
                        "encoding": "estimate",
                        "input_per_mtok": 1.0,
                        "output_per_mtok": 2.0,
                        "context_window": 32_000,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    assert main(["--offline", "--list-models"]) == 0
    out = capsys.readouterr().out
    assert "hidden-model" not in out
    assert "bundled prices only" in out
