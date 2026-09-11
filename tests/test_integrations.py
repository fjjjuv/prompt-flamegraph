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


class _BrokenPromptValue:
    """to_messages() raises (e.g. unrendered template); .messages may still work."""

    def __init__(self, messages):
        self.messages = messages

    def to_messages(self):
        raise RuntimeError("missing template inputs")


class _RichMsg(_Msg):
    """AIMessage/ToolMessage-like object carrying extra metadata."""

    def __init__(
        self,
        type_,
        content,
        name=None,
        tool_call_id=None,
        tool_calls=None,
        additional_kwargs=None,
    ):
        super().__init__(type_, content)
        self.name = name
        self.tool_call_id = tool_call_id
        self.tool_calls = tool_calls
        self.additional_kwargs = additional_kwargs or {}


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


def test_from_langchain_to_messages_falls_back_to_messages():
    obj = _BrokenPromptValue([_Msg("human", "fallback works")])
    out = from_langchain(obj)
    assert out["chat_history"] == [{"role": "user", "content": "fallback works"}]


def test_from_langchain_to_messages_failure_still_typeerror():
    import pytest

    with pytest.raises(TypeError):
        from_langchain(_BrokenPromptValue(42))


def test_from_langchain_messages_none_is_empty():
    out = from_langchain(_Template(None))
    assert out["system_prompt"] == ""
    assert out["chat_history"] == []


def test_from_langchain_dict_type_mapped_to_role():
    out = from_langchain(
        [
            {"type": "system", "content": "sys dict"},
            {"type": "human", "content": "typed human"},
            {"type": "ai", "content": "typed ai"},
        ]
    )
    assert out["system_prompt"] == "sys dict"
    assert [m["role"] for m in out["chat_history"]] == ["user", "assistant"]


def test_from_langchain_dict_role_wins_over_type():
    out = from_langchain([{"role": "assistant", "type": "human", "content": "x"}])
    assert out["chat_history"][0]["role"] == "assistant"


def test_from_langchain_dict_unknown_type_kept():
    out = from_langchain([{"type": "custom", "content": "x"}])
    assert out["chat_history"][0]["role"] == "custom"


def test_message_to_dict_copies_metadata():
    from prompt_flamegraph.integrations import _message_to_dict

    msg = _RichMsg(
        "ai",
        "calling",
        name="bot",
        tool_call_id="call_1",
        additional_kwargs={"tool_calls": [{"name": "f"}], "custom": 7},
    )
    entry = _message_to_dict(msg)
    assert entry["role"] == "assistant"
    assert entry["name"] == "bot"
    assert entry["tool_call_id"] == "call_1"
    assert entry["tool_calls"] == [{"name": "f"}]
    assert entry["custom"] == 7


def test_message_to_dict_additional_kwargs_no_clobber():
    from prompt_flamegraph.integrations import _message_to_dict

    msg = _RichMsg(
        "human", "real", additional_kwargs={"role": "system", "content": "fake"}
    )
    entry = _message_to_dict(msg)
    assert entry["role"] == "user"
    assert entry["content"] == "real"


def test_from_langchain_metadata_reaches_content():
    msg = _RichMsg(
        "ai",
        "with tools",
        name="bot",
        tool_call_id="call_9",
        additional_kwargs={"tool_calls": [{"name": "f"}]},
    )
    content = from_langchain([msg])["chat_history"][0]["content"]
    assert '"name": "bot"' in content
    assert '"tool_call_id": "call_9"' in content
    assert '"tool_calls": [{"name": "f"}]' in content


def test_from_litellm_single_dict_wrapped():
    out = from_litellm_messages({"role": "user", "content": "solo"})
    assert out["chat_history"] == [{"role": "user", "content": "solo"}]


def test_from_litellm_invalid_type_raises():
    import pytest

    with pytest.raises(TypeError):
        from_litellm_messages("not a list")
    with pytest.raises(TypeError):
        from_litellm_messages(42)


def test_profile_any_plain_string():
    html = profile_any("just a plain string", output=None)
    assert "just a plain string" in html


def test_profile_any_plain_dict_short_circuits():
    html = profile_any({"custom_key": "custom value"}, output=None)
    assert "custom value" in html


def test_profile_any_bare_string_list():
    html = profile_any(["alpha text", "beta text"], output=None)
    assert "alpha text" in html
    assert "beta text" in html
    # profiled as data, not wrapped into "unknown" role messages
    assert "unknown" not in html


def test_profile_any_shorthand_tuples_still_dispatch():
    html = profile_any(
        [("system", "tuple sys"), ("human", "tuple human")], output=None
    )
    assert "tuple sys" in html
    assert "tuple human" in html
