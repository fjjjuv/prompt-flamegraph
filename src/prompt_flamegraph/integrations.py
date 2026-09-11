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

"""Framework integrations via duck-typing: no framework is ever imported."""

from __future__ import annotations

from typing import Any

from .adapters import _content_to_text, from_messages, normalize

# LangChain BaseMessage.type → chat role.
_TYPE_TO_ROLE = {
    "system": "system",
    "human": "user",
    "ai": "assistant",
    "tool": "tool",
    "function": "tool",
}


def _is_message_like(obj: Any) -> bool:
    """Duck-type check for a BaseMessage-like object (.type str + .content)."""
    return (
        not isinstance(obj, (str, bytes, dict))
        and isinstance(getattr(obj, "type", None), str)
        and hasattr(obj, "content")
    )


def _message_to_dict(msg: Any) -> dict:
    """Convert one message (dict, message-like object, or ("role", text) tuple)
    into a {"role", "content"} dict for adapters.from_messages."""
    if isinstance(msg, dict):
        return msg
    if _is_message_like(msg):
        mtype = str(msg.type)
        return {
            "role": _TYPE_TO_ROLE.get(mtype, mtype or "unknown"),
            "content": _content_to_text(msg.content),
        }
    if isinstance(msg, (list, tuple)) and len(msg) == 2 and isinstance(msg[0], str):
        # LangChain shorthand inside message lists: ("human", "text").
        return {
            "role": _TYPE_TO_ROLE.get(msg[0], msg[0]),
            "content": _content_to_text(msg[1]),
        }
    return {"role": "unknown", "content": _content_to_text(msg)}


def _extract_messages(obj: Any) -> list:
    """Pull a message list out of a LangChain-style object by duck-typing."""
    to_messages = getattr(obj, "to_messages", None)
    if callable(to_messages):
        result = to_messages()
        return list(result) if isinstance(result, (list, tuple)) else [result]
    messages = getattr(obj, "messages", None)
    if isinstance(messages, (list, tuple)):
        return list(messages)
    if _is_message_like(obj):
        return [obj]
    if isinstance(obj, (list, tuple)):
        return list(obj)
    raise TypeError(f"cannot extract messages from {type(obj).__name__}")


def from_langchain(obj: Any) -> dict:
    """Convert LangChain-style objects into the structured prompt dict.

    Pure duck-typing — langchain is never imported. Handles objects with a
    ``.to_messages()`` method (ChatPromptValue / rendered prompt templates),
    objects with a ``.messages`` list, single BaseMessage-like objects
    (``.type`` in "system"/"human"/"ai"/"tool" and a ``.content`` attr), and
    plain lists of any of those. Returns the
    {system_prompt, chat_history, ...} dict build_tree/profile_prompt expect.
    """
    messages = [_message_to_dict(m) for m in _extract_messages(obj)]
    return from_messages(messages)


def from_litellm_messages(messages: list[dict], **kwargs) -> dict:
    """Alias for adapters.from_messages (litellm uses the OpenAI shape)."""
    return from_messages(messages, **kwargs)


def profile_any(obj: Any, output: str | None = None, model: str | None = None, **profile_kwargs) -> str:
    """Best-effort profiler: accepts a structured dict, an OpenAI/Anthropic
    request body, a message list, or a LangChain-style object (prompt value,
    template, or message). Tries adapters.normalize() first, then falls back
    to the LangChain duck-typing adapter. Extra kwargs go to profile_prompt.
    """
    from .core import profile_prompt

    data = normalize(obj)
    if data is obj:
        # normalize() did not recognize the shape — try LangChain duck-typing.
        try:
            data = from_langchain(obj)
        except Exception:
            data = obj
    return profile_prompt(data, output=output, model=model, **profile_kwargs)
