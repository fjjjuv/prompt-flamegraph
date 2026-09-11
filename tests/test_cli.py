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


def test_terminal_and_diff_conflict():
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", "--terminal", "--diff", "other.json"])
    assert excinfo.value.code != 0


def test_terminal_and_format_conflict():
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", "--terminal", "--format", "json"])
    assert excinfo.value.code != 0


def test_terminal_and_output_conflict(tmp_path: Path):
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", "--terminal", "-o", str(tmp_path / "o.html")])
    assert excinfo.value.code != 0


def test_terminal_flag_runs(capsys):
    assert main(["--demo", "--terminal"]) == 0
    out = capsys.readouterr().out
    assert "system_prompt" in out


def test_bad_diff_file_reports_diff(tmp_path: Path):
    src = tmp_path / "p.json"
    src.write_text(json.dumps({"a": "hi"}), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        main([str(src), "--diff", str(bad)])
    assert "Invalid JSON in --diff file" in str(excinfo.value)


def test_missing_input_file_reports_not_found(tmp_path: Path):
    missing = tmp_path / "nope.json"
    with pytest.raises(SystemExit) as excinfo:
        main([str(missing), "--format", "json", "-o", str(tmp_path / "o.json")])
    assert "not found" in str(excinfo.value)


def test_invalid_json_input_labels_input(tmp_path: Path):
    src = tmp_path / "bad.json"
    src.write_text("{oops", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        main([str(src)])
    assert "Invalid JSON in INPUT" in str(excinfo.value)


def test_non_utf8_input_clean_error(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"\xff\xfe\x00{}")
    with pytest.raises(SystemExit) as excinfo:
        main([str(bad)])
    assert "UTF-8" in str(excinfo.value)


def test_unwritable_output_clean_error(tmp_path: Path):
    _needs_to_json()
    src = tmp_path / "p.json"
    src.write_text(json.dumps({"a": "hi"}), encoding="utf-8")
    out = tmp_path / "missing-dir" / "o.json"
    with pytest.raises(SystemExit) as excinfo:
        main([str(src), "--format", "json", "-o", str(out)])
    assert "cannot write output file" in str(excinfo.value)


def test_empty_stdin_reports_no_input(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    with pytest.raises(SystemExit) as excinfo:
        main(["-"])
    assert "no input on stdin" in str(excinfo.value)


@pytest.mark.parametrize(
    "extra",
    [
        ["ignored.json"],
        ["-o", "out.html"],
        ["--terminal"],
        ["--demo"],
        ["--diff", "other.json"],
        ["--budget", "10"],
        ["--list-models"],
        ["--format", "json"],
    ],
)
def test_update_models_rejects_combinations(extra):
    with pytest.raises(SystemExit) as excinfo:
        main(["--update-models", *extra])
    assert excinfo.value.code != 0


def test_list_models_rejects_output(tmp_path):
    pytest.importorskip("prompt_flamegraph.models")
    with pytest.raises(SystemExit) as excinfo:
        main(["--list-models", "-o", str(tmp_path / "o.txt")])
    assert excinfo.value.code != 0


def test_demo_rejects_positional_input(tmp_path):
    src = _write_tokens_file(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        main([str(src), "--demo"])
    assert excinfo.value.code != 0


def _write_tokens_file(tmp_path: Path, n_words: int = 3) -> Path:
    src = tmp_path / "p.json"
    src.write_text(
        json.dumps({"system_prompt": " ".join(f"w{i}" for i in range(n_words))}),
        encoding="utf-8",
    )
    return src


def test_budget_under_passes(tmp_path: Path, capsys):
    src = _write_tokens_file(tmp_path)
    out = tmp_path / "o.html"
    assert (
        main([str(src), "--tokenizer", "words", "--budget", "10", "-o", str(out)]) == 0
    )
    assert "BUDGET EXCEEDED" not in capsys.readouterr().err
    assert out.exists()


def test_budget_over_exit_3_and_writes_report(tmp_path: Path, capsys):
    _needs_to_json()
    src = _write_tokens_file(tmp_path)  # 3 tokens with the words tokenizer
    out = tmp_path / "o.json"
    assert (
        main(
            [str(src), "--tokenizer", "words", "--budget", "2",
             "--format", "json", "-o", str(out)]
        )
        == 3
    )
    err = capsys.readouterr().err
    assert "BUDGET EXCEEDED: 3 > 2" in err
    assert out.exists()  # report is still written before enforcement


def test_budget_boundary_equal_passes(tmp_path: Path, capsys):
    _needs_to_json()
    src = _write_tokens_file(tmp_path)  # exactly 3 tokens
    out = tmp_path / "o.json"
    assert (
        main(
            [str(src), "--tokenizer", "words", "--budget", "3",
             "--format", "json", "-o", str(out)]
        )
        == 0
    )
    assert "BUDGET EXCEEDED" not in capsys.readouterr().err


def test_budget_terminal_over(capsys):
    assert main(["--demo", "--terminal", "--budget", "1"]) == 3
    assert "BUDGET EXCEEDED" in capsys.readouterr().err


def test_budget_terminal_under(capsys):
    assert main(["--demo", "--terminal", "--budget", "10_000_000"]) == 0
    assert "BUDGET EXCEEDED" not in capsys.readouterr().err


def test_budget_svg_format(tmp_path: Path, capsys):
    src = _write_tokens_file(tmp_path)
    out = tmp_path / "o.svg"
    assert (
        main([str(src), "--tokenizer", "words", "--budget", "1",
              "--format", "svg", "-o", str(out)])
        == 3
    )
    assert "BUDGET EXCEEDED" in capsys.readouterr().err
    assert out.read_text(encoding="utf-8").startswith("<?xml")


def test_html_builds_tree_once(monkeypatch, tmp_path: Path):
    import prompt_flamegraph.core as core

    calls = []
    orig = core.build_tree

    def counting(*a, **k):
        calls.append(1)
        return orig(*a, **k)

    monkeypatch.setattr(core, "build_tree", counting)
    out = tmp_path / "o.html"
    assert main(["--demo", "-o", str(out)]) == 0
    assert len(calls) == 1


def test_no_aggregate_flag_renders_all_nodes(tmp_path: Path):
    payload = {"big": " ".join(f"w{i}" for i in range(100))}
    for i in range(10):
        payload[f"tiny_{i}"] = "x"
    src = tmp_path / "p.json"
    src.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "o.html"
    assert main([str(src), "--tokenizer", "words", "--no-aggregate", "-o", str(out)]) == 0
    html = out.read_text(encoding="utf-8")
    assert 'data-name="tiny_9"' in html
    assert "more ·" not in html


def test_stdin_non_utf8_clean_error(monkeypatch):
    class _BinaryStdin:
        def read(self):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", _BinaryStdin())
    with pytest.raises(SystemExit) as excinfo:
        main(["-"])
    assert "UTF-8" in str(excinfo.value)


def test_broken_pipe_exits_cleanly(monkeypatch, tmp_path: Path):
    class _BrokenStdout:
        def write(self, *args, **kwargs):
            raise BrokenPipeError()

        def flush(self):
            pass

        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdout", _BrokenStdout())
    src = _write_tokens_file(tmp_path)
    out = tmp_path / "o.html"
    assert main([str(src), "-o", str(out)]) == 1
    assert out.exists()  # report is written before the broken stdout print


def test_missing_tiktoken_clean_error(monkeypatch, tmp_path: Path):
    import prompt_flamegraph.core as core

    monkeypatch.setattr(core, "_load_tiktoken", lambda *a, **k: None)
    src = _write_tokens_file(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        main([str(src), "--tokenizer", "tiktoken", "-o", str(tmp_path / "o.html")])
    assert "tiktoken" in str(excinfo.value)


@pytest.mark.parametrize("value", ["-1", "nan", "inf"])
def test_cost_invalid_values_error(value):
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", "--cost", value])
    assert excinfo.value.code != 0


@pytest.mark.parametrize("flag", ["--width", "--height"])
def test_dimension_below_one_errors(flag):
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", flag, "0"])
    assert excinfo.value.code != 0


def test_budget_negative_errors():
    with pytest.raises(SystemExit) as excinfo:
        main(["--demo", "--budget", "-1"])
    assert excinfo.value.code != 0


def test_budget_zero_allowed_and_fails_gate(tmp_path: Path, capsys):
    _needs_to_json()
    src = _write_tokens_file(tmp_path)  # 3 tokens with the words tokenizer
    out = tmp_path / "o.json"
    assert (
        main([str(src), "--tokenizer", "words", "--budget", "0",
              "--format", "json", "-o", str(out)])
        == 3
    )
    assert "BUDGET EXCEEDED: 3 > 0" in capsys.readouterr().err


def test_bare_name_reports_file_not_found():
    with pytest.raises(SystemExit) as excinfo:
        main(["definitely-missing-prompt"])
    assert "not found" in str(excinfo.value)


def test_inline_json_string_still_works(tmp_path: Path):
    _needs_to_json()
    out = tmp_path / "o.json"
    assert main(['{"a": "hi"}', "--format", "json", "-o", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))


def test_inline_invalid_json_reports_invalid():
    with pytest.raises(SystemExit) as excinfo:
        main(["{oops"])
    assert "Invalid JSON" in str(excinfo.value)


def test_invalid_json_file_names_the_file(tmp_path: Path):
    src = tmp_path / "bad.json"
    src.write_text("{oops", encoding="utf-8")
    with pytest.raises(SystemExit) as excinfo:
        main([str(src)])
    assert "Invalid JSON" in str(excinfo.value)
    assert "bad.json" in str(excinfo.value)


def test_cost_zero_appears_in_summary(tmp_path: Path, capsys):
    src = _write_tokens_file(tmp_path)
    out = tmp_path / "o.html"
    assert main([str(src), "--cost", "0", "-o", str(out)]) == 0
    assert "est. cost: $0.000000" in capsys.readouterr().err


def test_diff_budget_checks_new_prompt_tokens(tmp_path: Path, capsys):
    old = tmp_path / "old.json"
    old.write_text(
        json.dumps({"a": " ".join(f"w{i}" for i in range(10))}),
        encoding="utf-8",
    )
    new = tmp_path / "new.json"
    new.write_text(json.dumps({"a": "w0"}), encoding="utf-8")
    out = tmp_path / "o.html"
    # diff_tree.tokens would be max(old, new) > 5, but the gate applies
    # to the NEW prompt (~1 token), so it passes.
    assert (
        main([str(old), "--diff", str(new), "--tokenizer", "words",
              "--budget", "5", "-o", str(out)])
        == 0
    )
    assert "BUDGET EXCEEDED" not in capsys.readouterr().err


def test_diff_budget_fails_when_new_prompt_grows(tmp_path: Path, capsys):
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"a": "w0"}), encoding="utf-8")
    new = tmp_path / "new.json"
    new.write_text(
        json.dumps({"a": " ".join(f"w{i}" for i in range(10))}),
        encoding="utf-8",
    )
    out = tmp_path / "o.html"
    assert (
        main([str(old), "--diff", str(new), "--tokenizer", "words",
              "--budget", "5", "-o", str(out)])
        == 3
    )
    assert "BUDGET EXCEEDED" in capsys.readouterr().err
