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

"""Adapters: convert common LLM API payload shapes into structured prompt dicts."""

from __future__ import annotations

import json
from typing import Any


def _content_to_text(content: Any) -> str:
    """Flatten message content (string or content-block list) into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
            elif (
                isinstance(block, dict)
                and block.get("type") == "tool_result"
                and isinstance(block.get("content"), list)
            ):
                # tool_result blocks may nest a list of content blocks.
                parts.append(_content_to_text(block["content"]))
            else:
                parts.append(json.dumps(block, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False, sort_keys=True)
    return str(content)


def _entry_to_message(entry: Any) -> dict:
    """Convert one message entry into {"role", "content"}; weird entries are stringified."""
    if isinstance(entry, dict):
        role = entry.get("role")
        parts = [_content_to_text(entry.get("content"))]
        # name/tool_calls/function_call are sent to the API and cost tokens.
        for key in ("name", "tool_calls", "function_call"):
            value = entry.get(key)
            if value is not None:
                parts.append(
                    json.dumps({key: value}, ensure_ascii=False, sort_keys=True)
                )
        return {
            "role": str(role) if role else "unknown",
            "content": "\n".join(part for part in parts if part),
        }
    return {"role": "unknown", "content": _content_to_text(entry)}


def from_messages(
    messages: list[dict],
    tools: list | None = None,
    system_prompt: str | None = None,
) -> dict:
    """Convert an OpenAI/Anthropic-style message list into the structured dict
    {system_prompt, tools, chat_history} that build_tree/profile_prompt expect.
    role==system/developer messages are merged into system_prompt; the rest become chat_history
    entries {"role": ..., "content": ...}."""
    system_parts = [system_prompt] if system_prompt else []
    history: list[dict] = []
    for entry in messages or []:
        if isinstance(entry, dict) and entry.get("role") in ("system", "developer"):
            text = _content_to_text(entry.get("content"))
            if text:
                system_parts.append(text)
            continue
        history.append(_entry_to_message(entry))

    result: dict[str, Any] = {"system_prompt": "\n\n".join(system_parts)}
    if tools:
        result["tools"] = tools
    result["chat_history"] = history
    return result


def normalize(data: Any) -> Any:
    """Auto-detect common payload shapes and convert to the structured dict:
    - {"messages": [...], "tools": [...]?} (OpenAI chat completions body)
    - {"system": "...", "messages": [...]} (Anthropic body)
    - a bare list of {"role","content"} dicts
    Anything else is returned unchanged. Extra top-level keys on a messages
    dict are preserved; "model" is dropped (it is not sent as prompt tokens)."""
    if isinstance(data, dict):
        messages = data.get("messages")
        if not isinstance(messages, list):
            return data
        system_parts = [
            text
            for key in ("system", "system_prompt")
            if (text := _content_to_text(data.get(key)))
        ]
        tools = data.get("tools")
        result = from_messages(
            messages,
            tools=tools if isinstance(tools, list) else None,
            system_prompt="\n\n".join(system_parts) or None,
        )
        consumed = {"messages", "system", "system_prompt", "tools", "model"}
        for key, value in data.items():
            if key not in consumed:
                result[key] = value
        return result
    if isinstance(data, list):
        conforming = [
            isinstance(m, dict) and ("role" in m or "content" in m) for m in data
        ]
        if not data or sum(conforming) * 2 > len(data):
            cleaned = [
                m if ok else {"role": "unknown", "content": str(m)}
                for m, ok in zip(data, conforming)
            ]
            return from_messages(cleaned)
    return data
