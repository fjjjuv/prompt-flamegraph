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

"""prompt_flamegraph: lightweight prompt context flamegraph generator for LLMs."""

from .adapters import from_messages, normalize
from .core import (
    Node,
    Tokenizer,
    build_tree,
    count_tokens,
    flatten_tree,
    get_tokenizer,
    profile_prompt,
)
from .diff import build_diff_tree, diff_prompts
from .export import to_json, to_markdown, to_svg
from .integrations import from_langchain, from_litellm_messages, profile_any
from .models import ModelSpec, cache_age_days, list_models, resolve_model, update_models
from .render import to_html
from .terminal import to_terminal
from .waste import Finding, WasteReport, detect_waste

__version__ = "0.3.1"

__all__ = [
    "build_diff_tree",
    "build_tree",
    "cache_age_days",
    "count_tokens",
    "detect_waste",
    "diff_prompts",
    "Finding",
    "flatten_tree",
    "from_langchain",
    "from_litellm_messages",
    "from_messages",
    "get_tokenizer",
    "list_models",
    "ModelSpec",
    "Node",
    "normalize",
    "profile_any",
    "profile_prompt",
    "resolve_model",
    "to_html",
    "to_json",
    "to_markdown",
    "to_svg",
    "to_terminal",
    "Tokenizer",
    "update_models",
    "WasteReport",
]
