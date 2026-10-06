"""Regenerate the changelog table in about.html from GitHub releases.

Usage: python update-changelog.py

Fetches https://api.github.com/repos/fjjjuv/prompt-flamegraph/releases,
rebuilds the <tbody> of the #changelog table in about.html, and bumps
the current version in llms.txt and the JSON-LD softwareVersion in
index.html. No token needed (public repo); set GITHUB_TOKEN to raise
the rate limit.

French translations for new highlight texts must be added to i18n.js
manually — the script prints any untranslated English strings it wrote.
"""

import json
import os
import re
import urllib.request

REPO = "fjjjuv/prompt-flamegraph"
HERE = os.path.dirname(os.path.abspath(__file__))

# Highlights for releases whose GitHub notes are too long for a one-line
# summary. Key: version without leading "v".
HIGHLIGHTS = {
    "0.4.1": "Windows console and redirected-stream robustness, BOM-tolerant JSON input, CI matrix and trusted PyPI publishing.",
    "0.4.0": 'Dark mode: theme="auto|light|dark" and --theme CLI flag, CSS custom properties, persisted sun/moon toggle.',
    "0.3.3": "Hardening release: token-accuracy fixes, error handling, security.",
    "0.3.2": "OpenAI Responses API payloads, top-level exports, Markdown waste report, accessible tooltips, token-accuracy and CLI fixes.",
    "0.3.1": "README redesign, PyPI/GitHub version alignment.",
    "0.3.0": "API payload adapters, model presets and dynamic pricing, CI budget gate, framework adapters, JSON export, aggregation buckets, LGPL-3.0-or-later license.",
    "0.2.4": "Website link in README and PyPI metadata.",
    "0.2.3": "Version sync, README updates with PyPI and Dev.to links.",
    "0.2.2": "README badges, waste detection example, copyright year updates.",
    "0.2.1": "Demo screenshot in README.",
    "0.2.0": "Initial release with HTML/SVG/Markdown flamegraphs, waste detection, diff, terminal output and CLI.",
}

# Versions present on PyPI but without a GitHub release — keep them in
# the table between GitHub releases by published date.
EXTRA_VERSIONS = {"0.2.3", "0.2.2", "0.2.1", "0.2.0"}
EXTRA_DATES = {"0.2.3": "2026-09-10", "0.2.2": "2026-09-09", "0.2.1": "2026-09-08", "0.2.0": "2026-09-07"}


def fetch_releases():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases?per_page=50",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "update-changelog",
            **({"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else {}),
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def first_line_summary(body):
    for line in (body or "").splitlines():
        line = line.strip().lstrip("#- *").strip()
        if line and not line.startswith("**"):
            return re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", line)
    return "See release notes on GitHub."


def main():
    releases = fetch_releases()
    rows = []
    for rel in releases:
        if rel.get("draft"):
            continue
        ver = rel["tag_name"].lstrip("v")
        date = rel["published_at"][:10]
        hl = HIGHLIGHTS.get(ver) or first_line_summary(rel.get("body"))
        rows.append((date, ver, hl))
        if ver not in HIGHLIGHTS:
            print(f"note: {ver} uses an auto summary — add it to HIGHLIGHTS and i18n.js")

    for ver in EXTRA_VERSIONS:
        rows.append((EXTRA_DATES[ver], ver, HIGHLIGHTS[ver]))

    rows.sort(key=lambda r: r[0], reverse=True)
    tbody = "\n".join(
        f'            <tr><td><code>{escape(v)}</code></td><td>{escape(h)}</td></tr>'
        for _, v, h in rows
    )

    about = os.path.join(HERE, "about.html")
    src = open(about, encoding="utf-8").read()
    src = re.sub(
        r"(<thead><tr><th>Version</th><th>Highlights</th></tr></thead>\s*<tbody>).*?(</tbody>)",
        lambda m: m.group(1) + "\n" + tbody + "\n          " + m.group(2),
        src,
        flags=re.S,
    )
    open(about, "w", encoding="utf-8", newline="\n").write(src)

    latest = rows[0][1]
    for fname, pat in [
        ("llms.txt", r"Current version: [\d.]+"),
        ("index.html", r'"softwareVersion": "[\d.]+"'),
    ]:
        path = os.path.join(HERE, fname)
        s = open(path, encoding="utf-8").read()
        repl = f"Current version: {latest}" if fname == "llms.txt" else f'"softwareVersion": "{latest}"'
        open(path, "w", encoding="utf-8", newline="\n").write(re.sub(pat, repl, s))

    print(f"Updated changelog: latest = {latest}, {len(rows)} rows")


if __name__ == "__main__":
    main()
