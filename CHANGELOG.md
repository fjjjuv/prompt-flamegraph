# Changelog

## 0.3.0

- Refreshable model pricing: `--update-models` fetches LiteLLM's community pricing table into a local cache (`$XDG_CACHE_HOME/prompt-flamegraph/models.json`).
- `resolve_model` / `list_models` now include cached remote models; bundled entries still win on conflicts.
- New `--offline` flag and `PROMPT_FLAMEGRAPH_OFFLINE=1` env var for bundled-only, network-free operation.
- `--list-models` now reports the pricing cache age.

## 0.2.3

- Fixed `__version__` to match package version.
- README updates: added PyPI page and Dev.to article links.

## 0.2.2

- Updated copyright year to 2026 in all source files.
- README badges and waste detection example.

## 0.2.1

- Added demo screenshot to README.
- Updated package metadata author.

## 0.2.0

- Initial release.
- Interactive HTML/SVG/Markdown prompt context flamegraphs.
- Token waste detection.
- Prompt diff with color-coded changes.
- Terminal output (ASCII/Rich).
- CLI with multiple output formats.
- GPLv3 licensed.
