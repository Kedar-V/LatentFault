"""Forward-pass-only activation extraction (no generation), for machines without the GPU cache.

Same prompts as extract.py (build()): typed request, or the rendered card plus IMAGE_INSTRUCTION.
Saves the last-prompt-token residual stream at every hidden-state index (37 x 2048, float32) to
results/raw_forward/<model>/<modality>/<id>.npy. Skips items already done, so it can resume.

Usage: THREADS=12 python src/extract_forward.py --model models/Qwen2.5-VL-3B-Instruct --modality text
"""
import argparse
import os
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

from extract import build
from prompts import load_items

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--modality", choices=["text", "image"], required=True)
    args = ap.parse_args()
    tag = args.model.rstrip("/").split("/")[-1]
    out = ROOT / "results" / "raw_forward" / tag / args.modality
    out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(int(os.environ.get("THREADS", "12")))
    proc = AutoProcessor.from_pretrained(args.model)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(args.model, dtype=torch.float32).eval()
    items = load_items()
    t0, done = time.time(), 0
    for it in items:
        f = out / f"{it['id']}.npy"
        if f.exists():
            continue
        inputs, _ = build(proc, it, args.modality)
        with torch.inference_mode():
            hs = model(**inputs, output_hidden_states=True).hidden_states
        np.save(f, torch.stack([h[0, -1] for h in hs]).float().numpy())
        done += 1
        print(f"{args.modality} {it['id']} {done} done, {(time.time() - t0) / done:.1f}s/item", flush=True)


if __name__ == "__main__":
    main()
