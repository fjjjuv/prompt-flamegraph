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

#!/usr/bin/env python3
"""Demo: generate a prompt flamegraph for a typical agent prompt."""

from pathlib import Path

from prompt_flamegraph import profile_prompt


def main() -> None:
    prompt = {
        "system_prompt": (
            "You are an expert Python software engineer. "
            "You write clean, tested, and well-documented code. "
            "Always think through the problem step by step."
        ),
        "tools": [
            {
                "name": "read_file",
                "description": "Read the contents of a file at a given path.",
                "schema": "{\"type\": \"object\", \"properties\": {\"path\": {\"type\": \"string\"}}}",
            },
            {
                "name": "list_files",
                "description": "List files in a directory.",
                "schema": "{\"type\": \"object\", \"properties\": {\"dir\": {\"type\": \"string\"}}}",
            },
            {
                "name": "run_command",
                "description": "Run a shell command and return its output.",
                "schema": "{\"type\": \"object\", \"properties\": {\"command\": {\"type\": \"string\"}}}",
            },
        ],
        "rag_context": {
            "architecture.md": "## Architecture\n\nThe project uses a layered architecture...",
            "api_reference.md": "## API\n\n- `profile_prompt(data, output, ...)`\n- `build_tree(data)`",
            "troubleshooting.md": "## FAQ\n\nQ: Why are my tokens high? A: check your tool schemas.",
        },
        "chat_history": [
            {"role": "user", "content": "Help me build a new Python package."},
            {"role": "assistant", "content": "Sure, what problem are you trying to solve?"},
            {"role": "user", "content": "I want to profile my LLM prompt context."},
        ],
    }

    output = Path(__file__).with_name("demo_flamegraph.html")
    profile_prompt(
        prompt,
        output=str(output),
        title="Agent Prompt Flamegraph",
        cost_per_token=2.5e-6,
    )
    print(f"Demo flamegraph written to: {output}")


if __name__ == "__main__":
    main()
