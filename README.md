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

![Terminal demo](https://raw.githubusercontent.com/fjjjuv/prompt-flamegraph/main/docs/images/demo_terminal.gif)

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

## Works with LangChain & friends

Framework objects are converted **by duck-typing — LangChain is never imported** and is not a dependency:

```python
from prompt_flamegraph import profile_any

# ChatPromptValue, rendered prompt templates, BaseMessage lists...
profile_any(chat_prompt_value, output="context.html", model="gpt-4o")
```

`profile_any()` auto-detects the shape: LangChain-style objects (`to_messages()`, `.messages`, `.type`/`.content`) go through `from_langchain()`, API payloads go through `normalize()`. LiteLLM message lists work via `from_litellm_messages()` (OpenAI shape).

## CI budget gate

Fail a pipeline when a prompt grows past a token budget — exit code `3` when exceeded:

```bash
prompt-flamegraph prompt.json --budget 100000 --format json -o report.json
```

A ready-to-copy GitHub Actions workflow lives in [`.github/workflows/prompt-budget.yml.example`](.github/workflows/prompt-budget.yml.example).

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
Wasted: 36 / 60 tokens (60.0%)
- duplicate: 3× duplicate text ("def helper():     return 'value' ") — keep only one
- duplicate: 10× duplicate text ('Hi!') — keep only one
- too_many_tools: 6 tools defined — only declare the ones the model actually calls
- long_history: chat history is 33.3% of the total context (20 tokens) — consider truncation
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

# Draw every node, even sub-pixel ones (default groups them into "· N more ·" buckets)
prompt-flamegraph prompt.json --no-aggregate -o context.html

# Read from stdin (a raw API request body works too)
cat openai_request.json | prompt-flamegraph - --terminal
cat anthropic_request.json | prompt-flamegraph

# Model-aware: tokenizer encoding, pricing and context-window usage
prompt-flamegraph prompt.json --model gpt-4o

# List supported models
prompt-flamegraph --list-models

# CI gate: exit 3 when over budget
prompt-flamegraph prompt.json --budget 100000 --format json -o report.json

# Demo
prompt-flamegraph --demo --cost 1.5e-6
```

### Terminal example

```text
────────────────────────────── Prompt Flamegraph ───────────────────────────────
Total: 102 tokens
 Category         Tokens  % of total  Visual
 system_prompt        18       17.6%  █████
 tools                41       40.2%  ████████████
   read_file          21       20.6%  ██████
   run_command        20       19.6%  █████
 rag_context          22       21.6%  ██████
   doc_1.py           11       10.8%  ███
   doc_2.py           11       10.8%  ███
 chat_history         21       20.6%  ██████
   …                  (nested rows truncated)
```

Real output also lists each leaf (`name`, `description`, `schema`, `role`, `content`, …) indented under its category — shown here truncated.

## Model pricing

`--model` prices and context windows ship as a **bundled snapshot**, so cost estimates work offline out of the box. To refresh them, fetch LiteLLM's crowd-updated pricing table into your user cache (`$XDG_CACHE_HOME/prompt-flamegraph/models.json`):

```bash
prompt-flamegraph --update-models
```

The cache extends `--model` and `--list-models` to hundreds of additional models — bundled entries always win on name conflicts, and `--list-models` shows the cache age. Normal runs never touch the network; only `--update-models` does. Set `PROMPT_FLAMEGRAPH_OFFLINE=1` (or pass `--offline`) to ignore the cache entirely and use bundled data only.

All prices — bundled and cached — are community-sourced estimates (via LiteLLM's table), not official provider quotes; check your provider's pricing page for billing-grade numbers.

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
- **Framework adapters**: LangChain-style objects via `from_langchain`/`profile_any` (duck-typed — langchain is never imported).
- **CI budget gate**: `--budget N` exits with code 3 when the prompt exceeds N tokens.
- **Model presets**: `--model` selects the tokenizer encoding, pricing and context window.
- **stdin input**: pipe payloads straight into the CLI.
- Works with nested `dict`, `list` and `str` structures.

## API

### `profile_prompt(data, output=..., title=None, tokenizer=None, model=None, cost_per_token=None, detect_waste=True, context_window=None, width=1200, height=720)`

Build a prompt token tree and render it to a standalone HTML flamegraph; returns the HTML string and also writes it to `output` (pass `output=None` to skip the file).

- `data` — nested `dict`/`list`/`str` prompt structure (run `normalize()` first for raw API payloads).
- `output` — output file path.
- `title` — report title.
- `tokenizer` — `None` (auto: tiktoken when installed, else a built-in estimator), a `str -> int` callable, or a name: `"tiktoken"`, `"words"`, `"cl100k…"`, `"o200k…"`, `"model:<name>"`.
- `cost_per_token` — USD per token for cost estimates.
- `detect_waste` — include waste findings in the report (default `True`).
- `context_window` — model context size; adds a usage finding above 80%.
- `width` / `height` — graph dimensions in pixels.
- `model` — model name, e.g. `profile_prompt(data, model="gpt-4o")` — auto-derives `tokenizer`, `cost_per_token` and `context_window` from the model registry (mutually exclusive with `tokenizer`; warns and falls back to the estimator when the encoding needs tiktoken).

### `diff_prompts(v1, v2, output="prompt_diff.html", title=None, tokenizer=None, cost_per_token=None, width=1200, height=720)`

Render a diff flamegraph between two prompts; returns the HTML string.

### `detect_waste(tree, context_window=None)`

Analyze a tree and return a `WasteReport` with findings.

### `build_tree(data, name="prompt", tokenizer=None, model=None)`

Build the internal token tree without rendering. `model` resolves the tokenizer the same way as in `profile_prompt` (mutually exclusive with `tokenizer`).

### `to_html` / `to_svg` / `to_markdown` / `to_json`

Render a `build_tree` result to a standalone HTML string, SVG string, Markdown table, or machine-readable JSON report:

```python
from prompt_flamegraph import build_tree, to_json, to_svg

tree = build_tree(prompt)
svg = to_svg(tree, title="Prompt Flamegraph", width=1200)
report = to_json(tree, cost_per_token=2.5e-6)
```

Signatures: `to_html(tree, title=..., cost_per_token=None, waste_report=None, width=1200, height=720, max_depth=8, aggregate=True)`, `to_svg(tree, title=..., width=1200, row_height=34, max_depth=8, aggregate=True)`, `to_markdown(tree, title=..., cost_per_token=None)`, `to_json(tree, title=..., cost_per_token=None, waste_report=None)`. Nodes thinner than 2% of their parent or 26px — or deeper than `max_depth` — are grouped into `"· N more ·"` buckets (their tooltip lists what was folded); pass `aggregate=False` to draw every node.

### `count_tokens(text, tokenizer=None)` / `get_tokenizer(tokenizer=None)`

Count tokens in a string, or resolve a tokenizer argument (callable or name) into a `str -> int` callable.

### `from_messages(messages, tools=None, system_prompt=None)`

Convert an OpenAI/Anthropic-style message list into the structured prompt dict. `role in ("system", "developer")` messages are merged into `system_prompt`; the rest become `chat_history` entries.

### `normalize(data)`

Auto-detect common API payload shapes (OpenAI chat body, Anthropic body, bare message list) and convert to the structured prompt dict. Extra top-level keys on a recognized payload are preserved (`"model"` is dropped — it is not part of the prompt); anything else is returned unchanged.

### `from_langchain(obj)` / `from_litellm_messages(messages, **kwargs)` / `profile_any(obj, output=None, model=None, **kwargs)`

Framework adapters. `from_langchain` converts LangChain-style objects by duck-typing (`to_messages()`, `.messages`, `.type`/`.content` — the framework is never imported). `from_litellm_messages` handles LiteLLM message lists. `profile_any` auto-detects the input shape and renders a flamegraph in one call.

### `resolve_model(name)` / `list_models()`

Look up a `ModelSpec` (encoding, $/Mtok pricing, context window) by model name, or list all supported models.

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


