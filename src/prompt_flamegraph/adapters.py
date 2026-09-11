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

"""Adapters: convert common LLM API payload shapes into structured prompt dicts."""

from __future__ import annotations

import json
from typing import Any

# Content-block types whose payloads are binary/URL data, not text. Emitting
# the payload (e.g. a base64 image) would massively inflate token counts.
_IMAGE_BLOCK_TYPES = {"image", "image_url", "input_image"}

# API request parameters that accompany a prompt but are not prompt content,
# so they must not be counted as prompt tokens.
_REQUEST_PARAMS = {
    "model",
    "temperature",
    "max_tokens",
    "max_output_tokens",
    "top_p",
    "top_k",
    "n",
    "stop",
    "stop_sequences",
    "seed",
    "stream",
    "stream_options",
    "tool_choice",
    "response_format",
    "text",
    "reasoning_effort",
    "metadata",
    "user",
    "service_tier",
    "logit_bias",
    "presence_penalty",
    "frequency_penalty",
    "parallel_tool_calls",
    "audio",
    "modalities",
    "prediction",
    "store",
}


def _content_to_text(content: Any) -> str:
    """Flatten message content (string or content-block list) into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") in _IMAGE_BLOCK_TYPES
            ):
                # Image payloads are not text; keep a cheap placeholder.
                parts.append("[image]")
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if text is not None:
                    parts.append(str(text))
                extra = {
                    k: v for k, v in block.items() if k not in ("type", "text")
                }
                if extra:
                    parts.append(
                        json.dumps(
                            extra,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                    )
            elif isinstance(block, dict) and block.get("type") == "tool_result":
                # Emit wrapper metadata plus the flattened content so
                # tool_use_id/is_error/cache_control are not dropped.
                meta = {k: v for k, v in block.items() if k != "content"}
                if meta:
                    parts.append(
                        json.dumps(
                            meta,
                            ensure_ascii=False,
                            separators=(",", ":"),
                            sort_keys=True,
                        )
                    )
                parts.append(_content_to_text(block.get("content")))
            else:
                parts.append(json.dumps(block, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        return "\n".join(part for part in parts if part)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False, sort_keys=True)
    return str(content)


def _extras_to_parts(entry: dict) -> list[str]:
    """JSON-serialize message-level keys other than role/content; they are
    sent to the API (tool_call_id, refusal, name, tool_calls, custom keys...)
    and cost tokens."""
    return [
        json.dumps({key: value}, ensure_ascii=False, sort_keys=True)
        for key, value in entry.items()
        if key not in ("role", "content") and value is not None
    ]


def _entry_to_message(entry: Any) -> dict:
    """Convert one message entry into {"role", "content"}; weird entries are stringified."""
    if isinstance(entry, dict):
        role = entry.get("role")
        parts = [_content_to_text(entry.get("content"))]
        parts.extend(_extras_to_parts(entry))
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
            parts = [_content_to_text(entry.get("content"))]
            parts.extend(_extras_to_parts(entry))
            text = "\n".join(part for part in parts if part)
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
    - {"instructions": "...", "input": [...]} (OpenAI Responses API body)
    - a bare list of {"role","content"} dicts
    Anything else is returned unchanged. Genuinely unknown extra top-level keys
    on a request dict are preserved; known request parameters (model,
    temperature, max_tokens, ...) are dropped — they are not prompt tokens."""
    if isinstance(data, dict):
        messages = data.get("messages")
        if not isinstance(messages, list):
            # OpenAI Responses API carries the conversation in "input".
            messages = data.get("input")
        if not isinstance(messages, list):
            return data
        system_parts = [
            text
            for key in ("system", "system_prompt", "instructions")
            if (text := _content_to_text(data.get(key)))
        ]
        tools = data.get("tools")
        result = from_messages(
            messages,
            tools=tools if isinstance(tools, list) else None,
            system_prompt="\n\n".join(system_parts) or None,
        )
        consumed = (
            {"messages", "input", "system", "system_prompt", "instructions", "tools"}
            | _REQUEST_PARAMS
        )
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
