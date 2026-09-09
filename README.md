# prompt-flamegraph

Lightweight, zero-dependency Python package to profile LLM prompt tokens with interactive flamegraphs, waste detection, prompt diffs and HTML/SVG/Markdown/terminal exports.

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

## CLI

```bash
# HTML flamegraph
prompt-flamegraph prompt.json -o context.html --cost 1.5e-6

# Terminal bar chart
prompt-flamegraph prompt.json --terminal

# Diff between two prompts (green = added, red = removed, orange = changed)
prompt-flamegraph v1.json --diff v2.json -o diff.html

# SVG or Markdown export
prompt-flamegraph prompt.json --format svg -o context.svg
prompt-flamegraph prompt.json --format md -o context.md

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
- **Token waste detection**: duplicates, oversized RAG, long history, too many tools.
- **Prompt diff**: compare two prompts and visualize token changes.
- **Terminal output**: colored ASCII/Rich bar chart.
- **Export formats**: HTML, SVG, Markdown.
- Works with nested `dict`, `list` and `str` structures.

## API

### `profile_prompt(data, output, title, tokenizer, cost_per_token, detect_waste, width, height)`

Build and render a prompt flamegraph to HTML.

### `diff_prompts(v1, v2, output, title, ...)`

Render a diff flamegraph between two prompts.

### `detect_waste(tree)`

Analyze a tree and return a `WasteReport` with findings.

### `build_tree(data, name, tokenizer)`

Build the internal token tree without rendering.

## Source

<https://github.com/fjjjuv/prompt-flamegraph>

## License

This project is licensed under the **GNU General Public License v3.0 or later**.

See the [LICENSE](LICENSE) file for details.
