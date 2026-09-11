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

from prompt_flamegraph.adapters import from_messages, normalize


def test_from_messages_merges_system():
    messages = [
        {"role": "system", "content": "Be nice."},
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    out = from_messages(messages)
    assert "Be nice." in out["system_prompt"]
    assert "Be concise." in out["system_prompt"]
    assert [m["role"] for m in out["chat_history"]] == ["user", "assistant"]
    assert all(m["role"] != "system" for m in out["chat_history"])


def test_from_messages_explicit_system_prompt():
    out = from_messages(
        [{"role": "system", "content": "B"}, {"role": "user", "content": "hi"}],
        system_prompt="A",
    )
    assert out["system_prompt"].startswith("A")
    assert "B" in out["system_prompt"]
    assert len(out["chat_history"]) == 1


def test_from_messages_tools_and_roles():
    tools = [{"name": "read_file"}]
    out = from_messages([{"role": "tool", "content": "result"}], tools=tools)
    assert out["tools"] == tools
    assert out["chat_history"][0]["role"] == "tool"


def test_from_messages_content_blocks():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": "world"},
                {"type": "image_url", "image_url": {"url": "https://x/y.png"}},
            ],
        }
    ]
    out = from_messages(messages)
    content = out["chat_history"][0]["content"]
    assert "Hello" in content
    assert "world" in content
    assert "image_url" in content


def test_from_messages_weird_entries():
    out = from_messages(["just a string", {"role": "user"}])
    assert out["chat_history"][0]["content"] == "just a string"
    assert out["chat_history"][1]["role"] == "user"


def test_normalize_openai_body():
    body = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
        ],
        "tools": [{"type": "function", "function": {"name": "f"}}],
    }
    out = normalize(body)
    assert out["system_prompt"] == "sys"
    assert out["chat_history"] == [{"role": "user", "content": "hi"}]
    assert out["tools"] == body["tools"]


def test_normalize_anthropic_body():
    body = {
        "system": "You are helpful.",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1024,
    }
    out = normalize(body)
    assert out["system_prompt"] == "You are helpful."
    assert out["chat_history"] == [{"role": "user", "content": "hi"}]


def test_normalize_anthropic_system_blocks():
    body = {
        "system": [{"type": "text", "text": "block system"}],
        "messages": [{"role": "user", "content": "hi"}],
    }
    out = normalize(body)
    assert out["system_prompt"] == "block system"


def test_normalize_bare_message_list():
    out = normalize([{"role": "user", "content": "hi"}, {"role": "assistant", "content": "yo"}])
    assert [m["role"] for m in out["chat_history"]] == ["user", "assistant"]


def test_normalize_passthrough():
    structured = {"system_prompt": "x", "chat_history": ["y"]}
    assert normalize(structured) is structured
    other = {"rag_context": {"doc": "text"}}
    assert normalize(other) is other
    strings = ["a", "b"]
    assert normalize(strings) is strings
    assert normalize(42) == 42


def test_normalize_preserves_extra_top_level_keys():
    body = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "hi"}],
        "blob": "a very large pasted blob " * 10,
        "context": {"doc": "retrieved text"},
        "metadata": {"request_id": "abc"},
        "max_tokens": 512,
    }
    out = normalize(body)
    assert out["blob"] == body["blob"]
    assert out["context"] == body["context"]
    assert out["metadata"] == body["metadata"]
    assert out["max_tokens"] == 512
    assert "model" not in out
    assert out["chat_history"] == [{"role": "user", "content": "hi"}]


def test_normalize_merges_system_and_system_prompt():
    body = {
        "system": "sys A",
        "system_prompt": "sys B",
        "messages": [{"role": "user", "content": "hi"}],
    }
    out = normalize(body)
    assert "sys A" in out["system_prompt"]
    assert "sys B" in out["system_prompt"]


def test_from_messages_developer_role_merged():
    out = from_messages(
        [
            {"role": "developer", "content": "dev rules"},
            {"role": "user", "content": "hi"},
        ]
    )
    assert "dev rules" in out["system_prompt"]
    assert [m["role"] for m in out["chat_history"]] == ["user"]


def test_entry_tool_calls_counted():
    out = from_messages(
        [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}
                ],
            },
            {"role": "assistant", "content": "ok", "name": "helper"},
            {"role": "assistant", "function_call": {"name": "f", "arguments": "{}"}},
        ]
    )
    first, second, third = out["chat_history"]
    assert "tool_calls" in first["content"]
    assert "read_file" in first["content"]
    assert "helper" in second["content"]
    assert "function_call" in third["content"]


def test_normalize_messy_list():
    data = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "yo"},
        {"role": "tool", "content": "res"},
        "a stray string",
        {"no_role": True},
    ]
    out = normalize(data)
    assert [m["role"] for m in out["chat_history"]] == [
        "user",
        "assistant",
        "tool",
        "unknown",
        "unknown",
    ]
    assert out["chat_history"][3]["content"] == "a stray string"
    assert "no_role" in out["chat_history"][4]["content"]


def test_normalize_mostly_junk_list_passthrough():
    data = [{"role": "user", "content": "hi"}, "junk", 42, {"x": 1}, None]
    assert normalize(data) is data


def test_content_tool_result_nested_blocks():
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "t1",
                    "content": [
                        {"type": "text", "text": "inner result text"},
                    ],
                }
            ],
        }
    ]
    out = from_messages(messages)
    assert "inner result text" in out["chat_history"][0]["content"]
