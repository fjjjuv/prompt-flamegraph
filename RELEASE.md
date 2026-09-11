# Release checklist

## Prerequisites

- `python3 -m pip install build twine` (or the `dev` extra: `pip install -e ".[dev]"`)
- A PyPI API token configured in `~/.pypirc` or exported as
  `TWINE_USERNAME=__token__` / `TWINE_PASSWORD=pypi-...`.
  Without a token, stop after `twine check` — do not attempt the upload.

## Steps

```bash
# 1. Clean previous artifacts and build
rm -rf dist/
python3 -m build

# 2. Validate metadata (README rendering, long description, etc.)
twine check dist/*

# 3. Sanity-check the wheel contents
python3 -m zipfile -l dist/*.whl

# 4. Smoke-test a clean install
python3 -m venv /tmp/pfg-venv
/tmp/pfg-venv/bin/pip install dist/*.whl
/tmp/pfg-venv/bin/prompt-flamegraph --demo --terminal
/tmp/pfg-venv/bin/prompt-flamegraph --list-models

# 5. Upload to PyPI (requires API token)
twine upload dist/*

# 6. Tag and push
git tag -a v0.3.1 -m "Release 0.3.1"
git push origin v0.3.1

# 7. GitHub release (requires gh CLI, authenticated)
gh release create v0.3.1 dist/* --title "0.3.1" --notes-file CHANGELOG.md
```

## Release notes — 0.3.1

### Added

- Refreshable model pricing: `--update-models` fetches LiteLLM's community pricing table into a local cache (`$XDG_CACHE_HOME/prompt-flamegraph/models.json`).
- `resolve_model` / `list_models` now include cached remote models; bundled entries still win on conflicts.
- New `--offline` flag and `PROMPT_FLAMEGRAPH_OFFLINE=1` env var for bundled-only, network-free operation.
- `--list-models` now reports the pricing cache age.
- New `model=` keyword argument on `profile_prompt` / `build_tree` that derives the tokenizer, per-token pricing and context window from the model registry.
- `to_html`, `to_svg`, `to_markdown` and `get_tokenizer` are now exported at the top level (all renderers available directly from `prompt_flamegraph`); the lazy-attribute indirection was removed in favor of eager imports.

### Fixed

- Stored XSS via unescaped node names in the HTML tooltip.
- `normalize()` silently dropping unknown keys of recognized API payloads.
- Crashes on deeply nested or circular input — now reported as clean errors.
- Double-counting of wasted tokens in waste detection.
- SVG bar widths and empty-graph rendering in diff output.
- Model-pricing cache hardening: atomic cache writes, memoized cache reads and sanitized remote model names.
- CLI error-path cleanup.
