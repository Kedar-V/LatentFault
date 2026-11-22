"""Sanity check: inside an ablated window, recorded hidden states have ~0 projection on the direction.

Usage: python src/check_ablation.py <condition> [ids...]
"""
import json
import sys
from pathlib import Path

import numpy as np

from intervene import WINDOWS, fold_directions
from prompts import load_items

ROOT = Path(__file__).resolve().parent.parent
MODEL = "Qwen2.5-VL-3B-Instruct"
cond = sys.argv[1]
ids = sys.argv[2:] or ["h000", "h001", "h002"]
_, direction, window, _ = cond.split("-")
items = load_items()
dirs, tf = fold_directions(MODEL, items)
idx = {it["id"]: i for i, it in enumerate(items)}
hidden = [i + 1 for i in WINDOWS[window] if i + 1 < 36]  # index 36 is after the final norm
for rid in ids:
    for mod in ("text", "image"):
        base = ROOT / "results" / "interventions" / MODEL / cond / mod / rid
        if not base.with_suffix(".json").exists():
            continue
        R = dirs[direction][tf[idx[rid]]]
        h = np.load(base.with_suffix(".npz"))["h"].astype(np.float32)
        p = np.abs((h * R).sum(1))[hidden]
        rec = json.loads(base.with_suffix(".json").read_text())
        head = rec.get("reply_head", rec.get("reply", ""))[:40]
        print(f"{cond} {rid} {mod:5} max|proj| in window: {p.max():5.2f} | {rec['label']:8} | {head!r}")
