"""Print the opening of replies in the label cells most likely to be wrong, for manual review:
harmful requests labelled COMPLIED and benign requests labelled REFUSED. Only the first
70 characters are shown: enough to judge refusal vs compliance.

Usage: python src/spot_check.py Qwen2.5-VL-3B-Instruct [n_per_cell]
"""
import json
import sys
from pathlib import Path

from label import label

ROOT = Path(__file__).resolve().parent.parent
model, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8
raw = ROOT / "results" / "raw" / model
cells = {("harmful", "COMPLIED"): [], ("benign", "REFUSED"): []}
for js in sorted(raw.glob("*/*.json")):
    m = json.loads(js.read_text())
    key = (m["kind"], label(m["reply"])[0])
    if key in cells:
        cells[key].append(m)
for (kind, lab), ms in cells.items():
    print(f"== {kind} labelled {lab}: {len(ms)} (showing {min(n, len(ms))})")
    for m in ms[:n]:
        print(f"  {m['id']} {m['modality']:5} | {' '.join(m['reply'].split())[:70]!r}")
