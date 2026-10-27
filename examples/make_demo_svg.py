"""Record the README demo: run real aichivist commands on the invented demo inbox and render an animated SVG.

    python examples/make_demo_svg.py docs/demo.svg

No dependencies; the output is reproducible, so the animation always matches what the tool really prints.
"""
import html
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

WIDTH, LINE_HEIGHT, FONT_SIZE, MAX_CHARS = 960, 19, 13, 104
SCREEN_LINES = 15
TYPE_SECONDS, HOLD_SECONDS = 1.0, 3.2
ROOT = Path(__file__).resolve().parent.parent


def steps(demo: Path) -> List[Tuple[str, List[str]]]:
    inbox, archive, plan = demo / "Downloads", demo / "archive", demo / "plan.md"
    insurance = archive / "Personal/Insurance/2026-01-01 Example Health Ltd Policy basic insurance.txt"
    slides = archive / "Study/01_Term/Statistics/Slides/Lecture 3 Descriptive statistics.txt"
    return [
        ("survey", ["survey", str(inbox)]),
        ("suggest", ["suggest", str(inbox / "scan_0042.txt")]),
        ("duplicates", ["duplicates", str(inbox), "--in", str(archive)]),
        ("apps", ["apps", str(inbox / "Example Game")]),
        ("plan add", ["plan", "add", str(plan), str(inbox / "scan_0042.txt"), str(insurance),
                      "--reason", "health insurance policy"]),
        ("plan add", ["plan", "add", str(plan), str(inbox / "lecture3.txt"), str(slides),
                      "--reason", "statistics slides"]),
        ("plan add", ["plan", "add", str(plan), str(inbox / "invoice(1) copy.txt"), "TRASH", "--reason", "duplicate"]),
        ("plan approve", ["plan", "approve", str(plan)]),
        ("plan apply", ["plan", "apply", str(plan)]),
        ("close", ["close", str(archive / "Study/01_Term"), "--note", "all grades received"]),
        ("search", ["search", str(archive / "Study/01_Term"), "statistics"]),
        ("storage", ["storage", str(demo / "storage.md"), "--currency", "CHF"]),
    ]


def record(demo: Path) -> List[Tuple[str, List[str]]]:
    env = {**os.environ, "AICHIVIST_HOME": str(demo / ".state"), "AICHIVIST_TRASH": str(demo / ".trash"),
           "PYTHONPATH": str(ROOT)}
    subprocess.run([sys.executable, str(ROOT / "examples/make_demo.py"), str(demo)], check=True,
                   capture_output=True, env=env)
    frames = []
    for _, args in steps(demo):
        out = subprocess.run([sys.executable, "-m", "aichivist", *args], capture_output=True, text=True, env=env)
        command = "aichivist " + " ".join(f'"{a}"' if " " in a else a for a in args)
        text = (out.stdout + out.stderr).replace(str(demo), "~/demo").replace("\t", "  ")
        frames.append((command.replace(str(demo), "~/demo"), [line for line in text.splitlines() if line.strip()]))
    return merge_plan_adds(frames)


def merge_plan_adds(frames: List[Tuple[str, List[str]]]) -> List[Tuple[str, List[str]]]:
    """Show the three `plan add` calls as one screen."""
    merged: List[Tuple[str, List[str]]] = []
    for command, lines in frames:
        if merged and command.startswith("aichivist plan add") and merged[-1][0].startswith("aichivist plan add"):
            merged[-1] = (merged[-1][0], merged[-1][1] + ["$ " + command] + lines)
        else:
            merged.append((command, lines))
    return merged


def clip(line: str) -> str:
    return line if len(line) <= MAX_CHARS else line[:MAX_CHARS - 1] + "…"


def render(frames: List[Tuple[str, List[str]]]) -> str:
    total = len(frames) * (TYPE_SECONDS + HOLD_SECONDS)
    height = (SCREEN_LINES + 3) * LINE_HEIGHT
    css, groups = [], []
    for i, (command, lines) in enumerate(frames):
        start = i * (TYPE_SECONDS + HOLD_SECONDS)
        show, out_at, hide = start / total * 100, (start + TYPE_SECONDS) / total * 100, (start + TYPE_SECONDS +
                                                                                           HOLD_SECONDS) / total * 100
        css.append(f"@keyframes f{i}{{0%,{show:.2f}%{{opacity:0}}{show + 0.01:.2f}%,{hide - 0.01:.2f}%{{opacity:1}}"
                   f"{hide:.2f}%,100%{{opacity:0}}}}"
                   f"@keyframes o{i}{{0%,{out_at:.2f}%{{opacity:0}}{out_at + 0.01:.2f}%,100%{{opacity:1}}}}"
                   f".f{i}{{animation:f{i} {total}s step-end infinite}}"
                   f".o{i}{{animation:o{i} {total}s step-end infinite}}")
        rows = [f'<text class="p" y="{2 * LINE_HEIGHT}">$ {html.escape(clip(command))}</text>']
        for j, line in enumerate(lines[:SCREEN_LINES], start=3):
            cls = "c" if line.startswith("$ ") else ("w" if line.lstrip().startswith("!") else "t")
            rows.append(f'<text class="{cls}" y="{j * LINE_HEIGHT}">{html.escape(clip(line))}</text>')
        groups.append(f'<g class="f{i}">{rows[0]}<g class="o{i}">{"".join(rows[1:])}</g></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height + 34}" '
            f'viewBox="0 0 {WIDTH} {height + 34}" role="img" aria-label="aichivist demo">'
            f'<style>text{{font:{FONT_SIZE}px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;'
            f'white-space:pre}}.p,.c{{fill:#7ee787}}.t{{fill:#e6edf3}}.w{{fill:#f2cc60}}{"".join(css)}</style>'
            f'<rect width="100%" height="100%" rx="10" fill="#0d1117"/>'
            f'<circle cx="20" cy="17" r="6" fill="#ff5f56"/><circle cx="40" cy="17" r="6" fill="#ffbd2e"/>'
            f'<circle cx="60" cy="17" r="6" fill="#27c93f"/>'
            f'<g transform="translate(16 24)">{"".join(groups)}</g></svg>\n')


def main(target: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        frames = record(Path(tmp) / "demo")
    Path(target).write_text(render(frames), encoding="utf-8")
    print(f"{target}: {len(frames)} screens")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
