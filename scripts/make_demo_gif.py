#!/usr/bin/env python3
"""Render animated GIF demos of the prompt-flamegraph CLI for the README.

Self-contained: only needs Pillow + subprocess + stdlib. Runs the real CLI,
captures its (ANSI-colored) terminal output, and draws a fake macOS-style
terminal window with a typewriter / line-reveal animation.

Usage:
    python3 scripts/make_demo_gif.py            # both GIFs
    python3 scripts/make_demo_gif.py terminal   # just docs/images/demo_terminal.gif
    python3 scripts/make_demo_gif.py flow       # just docs/images/demo_flow.gif
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "docs" / "images"

# ---------------------------------------------------------------------------
# Look & feel
# ---------------------------------------------------------------------------

BG = (13, 17, 23)          # #0d1117 github-dark
CHROME_BG = (22, 27, 34)   # #161b22
FG = (201, 209, 217)       # #c9d1d9 default text
FG_DIM = (110, 118, 129)   # dimmed
PROMPT_GREEN = (126, 231, 135)
DOTS = [(255, 95, 87), (254, 188, 46), (40, 200, 64)]

FONT_SIZE = 15
LINE_HEIGHT = 20
PAD_X = 22
PAD_TOP = 16
PAD_BOTTOM = 18
CHROME_H = 36
WINDOW_W = 900

TYPE_MS = 40          # per character while "typing"
TYPE_CHARS_PER_FRAME = 1
PAUSE_AFTER_TYPE_MS = 500
LINE_MS = 80          # per revealed output line
HOLD_MS = 2500        # final frame hold

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
]
BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
]

# Standard ANSI palette (xterm-ish, tuned for the dark bg)
ANSI_COLORS = {
    30: (97, 97, 97), 31: (248, 81, 73), 32: (63, 185, 80), 33: (210, 153, 34),
    34: (88, 166, 255), 35: (188, 140, 255), 36: (57, 197, 207), 37: (177, 186, 196),
    90: (110, 118, 129), 91: (255, 123, 114), 92: (86, 211, 100), 93: (227, 179, 65),
    94: (108, 182, 255), 95: (210, 168, 255), 96: (87, 216, 221), 97: (240, 246, 252),
}

ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")


def _load_font(candidates: list[str]) -> ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, FONT_SIZE)
    # last resort: ask fontconfig
    try:
        out = subprocess.run(
            ["fc-list", ":monospace", "file"], capture_output=True, text=True
        ).stdout.splitlines()
        for line in out:
            p = line.split(":")[0].strip()
            if p and Path(p).exists() and "Mono" in p:
                return ImageFont.truetype(p, FONT_SIZE)
    except OSError:
        pass
    return ImageFont.load_default()


def _dim(c: tuple[int, int, int], factor: float = 0.55) -> tuple[int, int, int]:
    return tuple(int(v * factor) for v in c)


# ---------------------------------------------------------------------------
# ANSI -> styled spans
# ---------------------------------------------------------------------------

Span = tuple[str, tuple[int, int, int] | None, bool, bool]  # text, fg, bold, dim


def parse_ansi_line(line: str) -> list[Span]:
    """Split one output line into (text, color, bold, dim) spans."""
    spans: list[Span] = []
    color: tuple[int, int, int] | None = None
    bold = dim = False
    pos = 0
    for m in ANSI_RE.finditer(line):
        if m.start() > pos:
            spans.append((line[pos:m.start()], color, bold, dim))
        params = [int(p) for p in m.group(1).split(";") if p != ""] or [0]
        i = 0
        while i < len(params):
            p = params[i]
            if p == 0:
                color, bold, dim = None, False, False
            elif p == 1:
                bold = True
            elif p == 2:
                dim = True
            elif p in ANSI_COLORS:
                color = ANSI_COLORS[p]
            elif p == 38 and i + 4 < len(params) and params[i + 1] == 2:
                color = (params[i + 2], params[i + 3], params[i + 4])
                i += 4
            i += 1
        pos = m.end()
    if pos < len(line):
        spans.append((line[pos:], color, bold, dim))
    return spans


def parse_output(text: str) -> list[list[Span]]:
    return [parse_ansi_line(line) for line in text.splitlines()]


# --- fallback colorizer (used only if the CLI emits no ANSI) ----------------

def _hsl_to_rgb(h: int, s: int, l: int) -> tuple[int, int, int]:
    """Same HSL->RGB the package uses to color bars (terminal.py)."""
    s = max(0.0, min(1.0, s / 100))
    l = max(0.0, min(1.0, l / 100))
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if h < 60:
        r1, g1, b1 = c, x, 0
    elif h < 120:
        r1, g1, b1 = x, c, 0
    elif h < 180:
        r1, g1, b1 = 0, c, x
    elif h < 240:
        r1, g1, b1 = 0, x, c
    elif h < 300:
        r1, g1, b1 = x, 0, c
    else:
        r1, g1, b1 = c, 0, x
    return (int((r1 + m) * 255), int((g1 + m) * 255), int((b1 + m) * 255))


_BAR_ROW = re.compile(r"^(\s*)(\S.*?)\s{2,}\S+\s+[\d.]+%\s+(█+)\s*$")


def fallback_colorize(spans: list[list[Span]]) -> list[list[Span]]:
    """Color the '█' runs the way the package would (terminal.py)."""
    out: list[list[Span]] = []
    for line in spans:
        text = "".join(s[0] for s in line)
        m = _BAR_ROW.match(text)
        if not m:
            out.append(line)
            continue
        indent, name, bar = m.groups()
        depth = len(indent) // 2
        h = int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 360
        col = _hsl_to_rgb(h, 65 + (depth % 3) * 8, max(35, 70 - depth * 12))
        pre = text[: m.start(3)]
        post = text[m.end(3):]
        out.append([(pre, None, False, False), (bar, col, False, False), (post, None, False, False)])
    return out


# ---------------------------------------------------------------------------
# Terminal window rendering
# ---------------------------------------------------------------------------

def _span_color(span: Span) -> tuple[int, int, int]:
    _, fg, _bold, dim = span
    c = fg if fg is not None else FG
    return _dim(c) if dim else c


def render_frame(
    cmd: str,
    typed: int,
    output_lines: list[list[Span]],
    n_visible: int,
    font: ImageFont.FreeTypeFont,
    bold_font: ImageFont.FreeTypeFont,
    title: str,
    height: int,
    cursor: bool = True,
) -> Image.Image:
    img = Image.new("RGB", (WINDOW_W, height), BG)
    d = ImageDraw.Draw(img)

    # window chrome
    d.rectangle([0, 0, WINDOW_W, CHROME_H], fill=CHROME_BG)
    for i, col in enumerate(DOTS):
        cx = 18 + i * 20
        d.ellipse([cx - 6, CHROME_H // 2 - 6, cx + 6, CHROME_H // 2 + 6], fill=col)
    tw = d.textlength(title, font=font)
    d.text(((WINDOW_W - tw) / 2, CHROME_H // 2 - FONT_SIZE // 2 - 1), title,
           font=font, fill=FG_DIM)
    d.line([(0, CHROME_H), (WINDOW_W, CHROME_H)], fill=(48, 54, 61))

    x0, y = PAD_X, CHROME_H + PAD_TOP

    # prompt line: "$ <cmd>" with block cursor
    d.text((x0, y), "$", font=bold_font, fill=PROMPT_GREEN)
    x = x0 + font.getlength("$ ")
    d.text((x, y), cmd[:typed], font=font, fill=(240, 246, 252))
    x += font.getlength(cmd[:typed])
    if cursor:
        cw = font.getlength("M")
        d.rectangle([x + 1, y + 2, x + cw + 1, y + LINE_HEIGHT - 2],
                    fill=(88, 166, 255))
    y += LINE_HEIGHT

    # output lines
    for line in output_lines[:n_visible]:
        x = x0
        for span in line:
            text = span[0]
            if not text:
                continue
            f = bold_font if span[2] else font
            d.text((x, y), text, font=f, fill=_span_color(span))
            x += f.getlength(text)
        y += LINE_HEIGHT

    return img


def make_gif(
    cmd: str,
    output_text: str,
    stderr_text: str,
    out_path: Path,
    title: str,
) -> None:
    font = _load_font(FONT_CANDIDATES)
    bold_font = _load_font(BOLD_CANDIDATES)

    # stderr: warnings precede output; the "total: ..." summary follows it,
    # matching how a real terminal interleaves the streams.
    stderr_lines = [w for w in stderr_text.splitlines() if w.strip()]
    warnings = [w for w in stderr_lines if w.startswith(("warning", "error"))]
    trailing = [w for w in stderr_lines if w not in warnings]

    lines: list[list[Span]] = [
        [(w, (227, 179, 65), False, False)] for w in warnings
    ]
    lines += parse_output(output_text)
    lines += [[(w, None, False, True)] for w in trailing]
    if "\x1b" not in output_text:  # CLI ran without color: re-derive bar colors
        lines = fallback_colorize(lines)
    # drop trailing blank lines
    while lines and not "".join(s[0] for s in lines[-1]).strip():
        lines.pop()

    n_lines = len(lines)
    height = CHROME_H + PAD_TOP + (n_lines + 1) * LINE_HEIGHT + PAD_BOTTOM

    frames: list[Image.Image] = []
    durations: list[int] = []

    def add(img: Image.Image, ms: int) -> None:
        frames.append(img)
        durations.append(ms)

    # phase 1: typewriter
    steps = list(range(0, len(cmd) + 1, TYPE_CHARS_PER_FRAME))
    if steps[-1] != len(cmd):
        steps.append(len(cmd))
    for k in steps:
        add(render_frame(cmd, k, lines, 0, font, bold_font, title, height), TYPE_MS)
    add(render_frame(cmd, len(cmd), lines, 0, font, bold_font, title, height,
                     cursor=False), PAUSE_AFTER_TYPE_MS)

    # phase 2: reveal output line by line
    for i in range(1, n_lines + 1):
        add(render_frame(cmd, len(cmd), lines, i, font, bold_font, title,
                         height, cursor=False), LINE_MS)

    # final hold
    add(render_frame(cmd, len(cmd), lines, n_lines, font, bold_font, title,
                     height, cursor=False), HOLD_MS)

    # shared palette keeps size down and avoids per-frame palette flashing
    pal = frames[-1].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    qframes = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    qframes[0].save(
        out_path,
        save_all=True,
        append_images=qframes[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"wrote {out_path}  ({out_path.stat().st_size / 1024:.0f} KB, "
          f"{len(frames)} frames, {WINDOW_W}x{height})")


# ---------------------------------------------------------------------------
# Capture real CLI output
# ---------------------------------------------------------------------------

def run_cli(args: list[str], stdin_text: str | None = None) -> tuple[str, str]:
    env = dict(os.environ)
    env.update(
        PYTHONPATH=str(REPO / "src"),
        FORCE_COLOR="1",
        COLORTERM="truecolor",
        TERM="xterm-256color",
        COLUMNS="80",
    )
    proc = subprocess.run(
        [sys.executable, "-m", "prompt_flamegraph", *args],
        input=stdin_text,
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO,
    )
    if proc.returncode != 0:
        raise SystemExit(f"CLI failed ({proc.returncode}): {proc.stderr}")
    return proc.stdout, proc.stderr


OPENAI_PAYLOAD = {
    "model": "gpt-4o",
    "messages": [
        {"role": "system", "content": "You are a helpful coding assistant. "
         "Be concise. Always think step by step."},
        {"role": "user", "content": "Refactor this function to be async and add retries."},
        {"role": "assistant", "content": "Sure — wrap the call in asyncio and "
         "use exponential backoff."},
        {"role": "user", "content": "Now add structured logging around each retry."},
    ],
    "tools": [
        {"type": "function", "function": {
            "name": "read_file",
            "description": "Read a file from disk. Accepts a path argument.",
            "parameters": {"type": "object",
                           "properties": {"path": {"type": "string"}}},
        }},
        {"type": "function", "function": {
            "name": "run_command",
            "description": "Execute a shell command and return stdout/stderr.",
            "parameters": {"type": "object",
                           "properties": {"command": {"type": "string"}}},
        }},
    ],
}


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("all", "terminal"):
        out, err = run_cli(["--demo", "--terminal"])
        make_gif(
            cmd="prompt-flamegraph --demo --terminal",
            output_text=out,
            stderr_text=err,
            out_path=OUT_DIR / "demo_terminal.gif",
            title="prompt-flamegraph — terminal demo",
        )

    if which in ("all", "flow"):
        payload = json.dumps(OPENAI_PAYLOAD)
        out, err = run_cli(
            ["-", "--model", "gpt-4o", "--terminal"], stdin_text=payload
        )
        make_gif(
            cmd="cat openai_payload.json | prompt-flamegraph - --model gpt-4o --terminal",
            output_text=out,
            stderr_text=err,
            out_path=OUT_DIR / "demo_flow.gif",
            title="openai payload → prompt-flamegraph",
        )


if __name__ == "__main__":
    main()
