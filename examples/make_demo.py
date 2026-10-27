"""Create an invented demo inbox to try aichivist safely: python examples/make_demo.py <empty folder>"""
import sys
from pathlib import Path

# All names and contents are invented.
INBOX = {
    "scan_0042.txt": "Example Health Ltd · Policy basic insurance · valid from 2026-01-01 · Policy holder: Alex Sample",
    "invoice(1).txt": "Example Mobile · Invoice February 2026 · date 2026-03-02 · CHF 29.90",
    "invoice(1) copy.txt": "Example Mobile · Invoice February 2026 · date 2026-03-02 · CHF 29.90",
    "voucher.txt": "Example Store · Gift card · value 50 · code 0000-0000",
    "IMG_2231.txt": "Example School · Diploma · Alex Sample",
    "lecture3.txt": "Example University · Statistics · Lecture 3: descriptive statistics",
}
GAME = "Downloads/Example Game"  # program data: a game library that must stay where the game expects it
STORAGE = """| Place | Kind | Where | Holds | Price | Per |
|---|---|---|---|---|---|
| Laptop | computer | home | Documents, Photos | 0 | |
| External drive | drive | home | Photos, Backup of Laptop | 120 | once |
| Cloud | cloud | away | Documents | 2.90 | month |
"""
AREAS = [
    "Personal/Insurance",
    "Personal/Phone & internet",
    "Personal/Finance & invoices/Vouchers",
    "Applications/Certificates",
    "Study/01_Term/Statistics/Slides",
]


def main(target: str) -> None:
    root = Path(target)
    if root.exists() and any(root.iterdir()):
        sys.exit(f"{root} is not empty – choose an empty folder")
    for area in AREAS:
        (root / "archive" / area).mkdir(parents=True, exist_ok=True)
    (root / "Downloads").mkdir(parents=True, exist_ok=True)
    for name, text in INBOX.items():
        (root / "Downloads" / name).write_text(text + "\n", encoding="utf-8")
    (root / GAME / "steamapps").mkdir(parents=True)
    (root / GAME / "steamapps" / "savegame.dat").write_bytes(b"\x00")
    (root / "storage.md").write_text(STORAGE, encoding="utf-8")
    print(f"Demo created in {root}. Next: aichivist inventory {root / 'Downloads'} --save")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
