"""Manual-review helper for intervention replies.

Benign replies are printed in full (to judge coherence); harmful replies only by their
opening words (enough to judge refusal vs compliance without reproducing harmful content).

Usage: python src/spot_check_interventions.py <condition> <n> [seed]
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cond, n = sys.argv[1], int(sys.argv[2])
random.seed(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
base = ROOT / "results" / "interventions" / "Qwen2.5-VL-3B-Instruct" / cond
for mod in ("text", "image"):
    files = sorted((base / mod).glob("*.json"))
    random.shuffle(files)
    for f in files[:n]:
        r = json.loads(f.read_text())
        harmful = r["kind"] == "harmful"
        text = " ".join(r.get("reply_head" if harmful else "reply", "").split())
        print(f"  {r['id']} {mod:5} {r['label']:8} | {text[:55] if harmful else text[:230]}")
