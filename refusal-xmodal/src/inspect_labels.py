"""Label one model's replies and print refusal counts by modality and request type.

Usage: python src/inspect_labels.py Qwen2.5-VL-3B-Instruct
"""
import sys
from collections import Counter
from pathlib import Path

from label import label_dir

ROOT = Path(__file__).resolve().parent.parent
model = sys.argv[1]
rows = label_dir(ROOT / "results" / "raw" / model)
for m in ("text", "image"):
    for k in ("harmful", "benign"):
        g = [r for r in rows if r["modality"] == m and r["kind"] == k]
        c = Counter(r["label"] for r in g)
        print(f"{m:5} {k:7} n={len(g):3}  REFUSED={c['REFUSED']:3}  COMPLIED={c['COMPLIED']:3}  "
              f"AMBIGUOUS={c['AMBIGUOUS']:3}")
amb = [(r["id"], r["modality"], r["why"]) for r in rows if r["label"] == "AMBIGUOUS"]
print(f"{len(amb)} ambiguous -> results/{model}/review.csv")
for a in amb[:15]:
    print("  ", a)
