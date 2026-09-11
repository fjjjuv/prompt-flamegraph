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

"""prompt_flamegraph: lightweight prompt context flamegraph generator for LLMs."""

from .adapters import from_messages, normalize
from .core import build_tree, count_tokens, profile_prompt
from .diff import diff_prompts
from .waste import detect_waste, WasteReport, Finding

__version__ = "0.2.4"

_LAZY = {
    "ModelSpec": ".models",
    "list_models": ".models",
    "resolve_model": ".models",
    "to_json": ".export",
}


def __getattr__(name: str):
    module = _LAZY.get(name)
    if module is not None:
        import importlib

        return getattr(importlib.import_module(module, __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "build_tree",
    "count_tokens",
    "diff_prompts",
    "detect_waste",
    "Finding",
    "from_messages",
    "list_models",
    "ModelSpec",
    "normalize",
    "profile_prompt",
    "resolve_model",
    "to_json",
    "WasteReport",
]
