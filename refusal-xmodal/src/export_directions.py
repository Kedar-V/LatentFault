"""Export the harm and refusal directions (all 200 JBB items, text) as one small .npz, numpy only.

No torch import, so it runs where PyTorch cannot start. The output holds two (layers+1, d)
unit-vector arrays and the JBB reference means; it contains no per-request activations.

Usage: python src/export_directions.py Qwen2.5-VL-3B-Instruct
"""
import json
import sys
from pathlib import Path

import numpy as np

from prompts import load_items

ROOT = Path(__file__).resolve().parent.parent
tag = sys.argv[1]
items = load_items()
raw = ROOT / "results" / "raw" / tag / "text"
X = np.stack([np.load(raw / f"{it['id']}.npz")["h"] for it in items])
y = np.array([it["harmful"] for it in items])
labels = {(r["id"], r["modality"]): r for r in json.loads((ROOT / "results" / tag / "labels.json").read_text())}
ref = np.array([labels[(it["id"], "text")]["refused"] for it in items])


def unit(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


harm = unit(X[y == 1].mean(0) - X[y == 0].mean(0))
r = X[(y == 0) & (ref == 1)].mean(0) - X[(y == 0) & (ref == 0)].mean(0)
refusal = unit(r - (r * harm).sum(-1, keepdims=True) * harm)
ph = (X * harm).sum(-1)
out = ROOT / "results" / tag / "ghostprompt_directions.npz"
np.savez(out, harm=harm.astype(np.float32), refusal=refusal.astype(np.float32),
         jbb_harm_harmful=ph[y == 1].mean(0).astype(np.float32),
         jbb_harm_benign=ph[y == 0].mean(0).astype(np.float32))
print("wrote", out, harm.shape)
