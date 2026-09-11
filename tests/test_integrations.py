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

import sys

from prompt_flamegraph.integrations import (
    from_langchain,
    from_litellm_messages,
    profile_any,
)


class _Msg:
    """BaseMessage-like object: .type + .content, no langchain needed."""

    def __init__(self, type_, content):
        self.type = type_
        self.content = content


class _PromptValue:
    """ChatPromptValue-like object: exposes .to_messages()."""

    def __init__(self, messages):
        self._messages = messages

    def to_messages(self):
        return self._messages


class _Template:
    """BaseChatPromptTemplate-like object: exposes .messages."""

    def __init__(self, messages):
        self.messages = messages


def test_from_langchain_to_messages():
    obj = _PromptValue(
        [
            _Msg("system", "Be nice."),
            _Msg("human", "hi there"),
            _Msg("ai", "hello!"),
        ]
    )
    out = from_langchain(obj)
    assert out["system_prompt"] == "Be nice."
    assert [m["role"] for m in out["chat_history"]] == ["user", "assistant"]
    assert out["chat_history"][0]["content"] == "hi there"


def test_from_langchain_messages_attr():
    obj = _Template(
        [
            _Msg("human", "question"),
            _Msg("ai", "answer"),
            _Msg("tool", "tool output"),
        ]
    )
    out = from_langchain(obj)
    assert [m["role"] for m in out["chat_history"]] == ["user", "assistant", "tool"]


def test_from_langchain_single_message():
    out = from_langchain(_Msg("human", "lonely"))
    assert out["chat_history"] == [{"role": "user", "content": "lonely"}]


def test_from_langchain_plain_list():
    out = from_langchain([_Msg("system", "sys"), _Msg("human", "q")])
    assert out["system_prompt"] == "sys"
    assert [m["role"] for m in out["chat_history"]] == ["user"]


def test_from_langchain_list_of_dicts():
    out = from_langchain(
        [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}]
    )
    assert [m["role"] for m in out["chat_history"]] == ["user", "assistant"]


def test_from_langchain_tuple_shorthand():
    obj = _PromptValue([("system", "sys text"), ("human", "hello")])
    out = from_langchain(obj)
    assert out["system_prompt"] == "sys text"
    assert out["chat_history"] == [{"role": "user", "content": "hello"}]


def test_from_langchain_unknown_type_kept():
    out = from_langchain(_Msg("chat", "some content"))
    assert out["chat_history"][0]["role"] == "chat"


def test_from_langchain_unrecognized_raises():
    import pytest

    with pytest.raises(TypeError):
        from_langchain(42)


def test_from_langchain_never_imports_langchain():
    from_langchain([_Msg("human", "hi")])
    assert "langchain" not in sys.modules
    assert not any(m.startswith("langchain") for m in sys.modules)


def test_from_litellm_messages():
    out = from_litellm_messages(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ],
        tools=[{"name": "f"}],
    )
    assert out["system_prompt"] == "sys"
    assert out["chat_history"] == [{"role": "user", "content": "hi"}]
    assert out["tools"] == [{"name": "f"}]


def test_profile_any_structured_dict():
    html = profile_any({"system_prompt": "some words here"}, output=None)
    assert html.startswith("<!DOCTYPE html>")
    assert "some words here" in html


def test_profile_any_langchainish_dispatch():
    obj = _PromptValue([_Msg("system", "dispatch sys"), _Msg("human", "dispatch human")])
    html = profile_any(obj, output=None)
    assert "dispatch sys" in html
    assert "dispatch human" in html


def test_profile_any_message_list():
    html = profile_any([_Msg("human", "from a list")], output=None)
    assert "from a list" in html


def test_profile_any_fallback_for_unknown():
    # An object nothing recognizes still gets profiled as a string leaf.
    html = profile_any(42, output=None)
    assert html.startswith("<!DOCTYPE html>")


def test_profile_any_writes_output(tmp_path):
    out = tmp_path / "o.html"
    html = profile_any({"system_prompt": "x"}, output=str(out))
    assert out.read_text(encoding="utf-8") == html
