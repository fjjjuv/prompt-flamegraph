# prompt-flamegraph

[![PyPI version](https://img.shields.io/pypi/v/prompt-flamegraph)](https://pypi.org/project/prompt-flamegraph/)
[![Python versions](https://img.shields.io/pypi/pyversions/prompt-flamegraph)](https://pypi.org/project/prompt-flamegraph/)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![Website](https://img.shields.io/badge/website-fjjjuv.github.io/prompt--flamegraph-orange)](https://fjjjuv.github.io/prompt-flamegraph/index.html)

Lightweight, zero-dependency Python package to profile LLM prompt tokens with interactive flamegraphs, waste detection, prompt diffs and HTML/SVG/Markdown/JSON/terminal exports. Works with raw OpenAI/Anthropic request payloads.

## What it does

`prompt-flamegraph` takes a structured prompt (system prompt, tools, RAG context, chat history) and shows you **where the tokens go**, in an interactive flamegraph.

It is intentionally lightweight: **no proxy, no server, no dashboard, no telemetry**. One function call, one output file.

![Interactive HTML flamegraph](https://raw.githubusercontent.com/fjjjuv/prompt-flamegraph/main/docs/images/flamegraph_demo.png)

## Install

```bash
pip install prompt-flamegraph
```

Extras:

```bash
pip install prompt-flamegraph[tiktoken]   # accurate OpenAI-style token counts
pip install prompt-flamegraph[rich]       # prettier terminal output
```

## Quick start

```python
from prompt_flamegraph import profile_prompt

prompt = {
    "system_prompt": "You are a helpful coding assistant.",
    "tools": ["..."],
    "rag_context": {"doc_1": "..."},
    "chat_history": ["..."],
}

profile_prompt(prompt, output="context.html")
```

Open `context.html` in your browser.

## Works with OpenAI/Anthropic payloads

You don't have to restructure your data first. `normalize()` auto-detects common API request bodies — OpenAI `{"messages": [...], "tools": [...]}`, Anthropic `{"system": "...", "messages": [...]}`, or a bare message list — and converts them:

```python
from prompt_flamegraph import normalize, profile_prompt

payload = {
    "system": "You are a helpful assistant.",
    "messages": [{"role": "user", "content": "Hello!"}],
}

profile_prompt(normalize(payload), output="context.html")
```

Or build the structure yourself with `from_messages(messages, tools=..., system_prompt=...)`. The CLI applies `normalize()` automatically to any input.

## Waste detection

Identify token waste before sending the prompt to an API:

```python
from prompt_flamegraph import build_tree, detect_waste

prompt = {
    "system_prompt": "You are a helpful coding assistant.",
    "tools": ["read_file", "write_file", "run_command", "search_web", "send_email", "create_ticket"],
    "rag_context": {
        "doc_1.py": "def helper():\n    return 'value'\n",
        "doc_2.py": "def helper():\n    return 'value'\n",
        "doc_3.py": "def helper():\n    return 'value'\n",
    },
    "chat_history": ["Hi!"] * 10,
}

tree = build_tree(prompt, name="prompt")
report = detect_waste(tree)

print(f"Wasted: {report.wasted_tokens} / {report.total_tokens} tokens ({report.waste_ratio:.1%})")
for finding in report.findings:
    print(f"- {finding.kind}: {finding.message}")
```

Example output:

```text
Wasted: 26 / 88 tokens (29.5%)
- duplicate: 3× duplicate text ('def helper():     return 'value' ') — keep only one
- duplicate: 5× duplicate text ('Hi!') — keep only one
- too_many_tools: 6 tools defined — only declare the ones the model actually calls
```

Pass `detect_waste=True` to `profile_prompt()` to include findings directly in the HTML report.

## CLI

```bash
# HTML flamegraph
prompt-flamegraph prompt.json -o context.html --cost 1.5e-6

# Terminal bar chart
prompt-flamegraph prompt.json --terminal

# Diff between two prompts (green = added, red = removed, orange = changed)
prompt-flamegraph v1.json --diff v2.json -o diff.html

# SVG, Markdown or JSON export
prompt-flamegraph prompt.json --format svg -o context.svg
prompt-flamegraph prompt.json --format md -o context.md
prompt-flamegraph prompt.json --format json -o report.json

# Read from stdin (a raw API request body works too)
cat openai_request.json | prompt-flamegraph - --terminal
cat anthropic_request.json | prompt-flamegraph

# Model-aware: tokenizer encoding, pricing and context-window usage
prompt-flamegraph prompt.json --model gpt-4o

# List supported models
prompt-flamegraph --list-models

# Demo
prompt-flamegraph --demo --cost 1.5e-6
```

### Terminal example

```text
────────────────────────────── Prompt Flamegraph ──────────────────────────────
Total: 102 tokens
 Category         Tokens      %  Visual
 system_prompt        18  17.6%  ████
 tools                41  40.2%  ██████████
 rag_context          22  21.6%  █████
 chat_history         21  20.6%  █████
```

## Features

- Pure Python, no required dependencies.
- Optional `tiktoken` support.
- Pluggable tokenizer.
- Cost estimation.
- **Token waste detection**: duplicates, oversized RAG, long history, too many tools, context-window usage.
- **Prompt diff**: compare two prompts and visualize token changes.
- **Terminal output**: colored ASCII/Rich bar chart.
- **Export formats**: HTML, SVG, Markdown, JSON.
- **API adapters**: feed raw OpenAI/Anthropic request payloads or message lists directly.
- **Model presets**: `--model` selects the tokenizer encoding, pricing and context window.
- **stdin input**: pipe payloads straight into the CLI.
- Works with nested `dict`, `list` and `str` structures.

## API

### `profile_prompt(data, output, title, tokenizer, cost_per_token, detect_waste, width, height, context_window)`

Build and render a prompt flamegraph to HTML.

### `diff_prompts(v1, v2, output, title, ...)`

Render a diff flamegraph between two prompts.

### `detect_waste(tree, context_window=None)`

Analyze a tree and return a `WasteReport` with findings.

### `build_tree(data, name, tokenizer)`

Build the internal token tree without rendering.

### `from_messages(messages, tools=None, system_prompt=None)`

Convert an OpenAI/Anthropic-style message list into the structured prompt dict. `role == "system"` messages are merged into `system_prompt`; the rest become `chat_history` entries.

### `normalize(data)`

Auto-detect common API payload shapes (OpenAI chat body, Anthropic body, bare message list) and convert to the structured prompt dict. Anything else is returned unchanged.

### `resolve_model(name)` / `list_models()`

Look up a `ModelSpec` (encoding, $/Mtok pricing, context window) by model name, or list all supported models.

### `to_json(tree, title, cost_per_token, waste_report)`

Render a token tree as a machine-readable JSON report string.

## Resources

- **Website / documentation**: https://fjjjuv.github.io/prompt-flamegraph/index.html
- **Dev.to article** with a step-by-step walkthrough: [Stop Guessing Where Your LLM Prompt Tokens Go: prompt-flamegraph](https://dev.to/fjjjuv/stop-guessing-where-your-llm-prompt-tokens-go-prompt-flamegraph-52nf)
- **PyPI package page**: https://pypi.org/project/prompt-flamegraph/
- **Companion optimizer**: [prompt-optimizer](https://github.com/fjjjuv/prompt-optimizer) — generate optimization recommendations and trim your prompts automatically.

## Source

<https://github.com/fjjjuv/prompt-flamegraph>

## License

This project is licensed under the **GNU General Public License v3.0 or later**.

See the [LICENSE](LICENSE) file for details.
