"""Causal tests on the residual stream during generation: remove or add a direction, measure refusals.

Condition names (one folder each under results/interventions/<model>/):
  ablate-<dir>-<window>-<kind>[:image]   project <dir> out of decoder layers in <window>
  add-<dir>-L<l>-s<a>-<kind>[:image]     add a * gap_l * <dir> to the output of hidden layer l
<kind> is harmful or benign. A ":image" suffix runs image inputs only.

Held out: every direction (and gap) is fit on the cached baseline activations of the TRAINING
folds only (same 5-fold split by pair as analyze.py); a request uses the fold that excludes it.

Directions (unit length, one per hidden-state index):
  harmtext      mean(harmful) - mean(benign), text activations
  refusalorth   mean(benign refused) - mean(benign complied), text, made orthogonal to harmtext
  random        Gaussian, seed 0 (batch 1); random1..random3 use seeds 1..3 (batch 2)
gap_l = mean projection of training harmful minus benign on harmtext at layer l; additions of
every direction use this same size, so strengths are comparable across directions.

Windows (decoder layer i writes hidden-state index i + 1):
  early  decoder 0-17 (hidden 1-18)   late  decoder 18-35 (hidden 19-36)   all  every layer
"Layer 20" in an add condition is hidden index 20, i.e. the output of decoder layer 19.

Safety: replies capped at 40 new tokens. For harmful requests under intervention only the label
and the first 160 characters are stored; no modified weights are ever saved (hooks only).

Usage: python src/intervene.py --model ~/models/Qwen2.5-VL-3B-Instruct [--conditions a,b] [--pairs N]
"""
import argparse
import json
import re
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import GroupKFold
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

from extract import build
from label import label
from prompts import load_items

ROOT = Path(__file__).resolve().parent.parent
WINDOWS = {"early": range(0, 18), "late": range(18, 36), "all": range(0, 36)}
BATCH1 = ["ablate-harmtext-late-harmful", "ablate-harmtext-early-harmful",
          "ablate-random-late-harmful", "ablate-random-early-harmful",
          "ablate-harmtext-all-harmful", "ablate-random-all-harmful",
          "ablate-harmtext-all-benign", "ablate-random-all-benign"]
BATCH2_GPU0 = ["add-harmtext-L20-s1-benign", "add-harmtext-L12-s1-benign",
               "add-harmtext-L20-s2-benign", "add-harmtext-L12-s2-benign",
               "add-harmtext-L20-s0.5-benign", "add-harmtext-L12-s0.5-benign",
               "add-random-L20-s2-benign"]                                          # 1,400
BATCH2_GPU1 = ["ablate-refusalorth-late-harmful",
               "ablate-random1-late-harmful", "ablate-random2-late-harmful", "ablate-random3-late-harmful",
               "ablate-random1-all-benign:image", "ablate-random2-all-benign:image",
               "ablate-random3-all-benign:image"]                                   # 1,100


def parse(cond):
    """-> dict(mode, direction, window|layer, strength, kind, modalities, folder)."""
    body, _, only = cond.partition(":")
    parts = body.split("-")
    d = {"folder": cond.replace(":", "-"), "mode": parts[0], "direction": parts[1],
         "modalities": ("image",) if only == "image" else ("text", "image")}
    if d["mode"] == "ablate":
        d.update(window=parts[2], kind=parts[3], layer=None, strength=None)
    else:
        d.update(window=parts[2], layer=int(parts[2][1:]), strength=float(parts[3][1:]), kind=parts[4])
    return d


def fold_directions(model_tag, items):
    """Per fold, unit directions per hidden index; also test fold per item and harm gaps per fold."""
    raw = ROOT / "results" / "raw" / model_tag / "text"
    X = np.stack([np.load(raw / f"{it['id']}.npz")["h"] for it in items])  # (n, layers+1, d)
    y = np.array([it["harmful"] for it in items])
    groups = np.array([it["pair"] for it in items])
    labels = {(r["id"], r["modality"]): r for r in
              json.loads((ROOT / "results" / model_tag / "labels.json").read_text())}
    ref = np.array([labels[(it["id"], "text")]["refused"] for it in items])
    folds = list(GroupKFold(n_splits=5).split(X[:, 0], y, groups))
    unit = lambda v: v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)  # noqa: E731
    test_fold = np.zeros(len(items), int)
    harm, refusal, gaps = [], [], []
    for k, (tr, te) in enumerate(folds):
        Xt, yt, rt = X[tr], y[tr], ref[tr]
        h = unit(Xt[yt == 1].mean(0) - Xt[yt == 0].mean(0))
        r = Xt[(yt == 0) & (rt == 1)].mean(0) - Xt[(yt == 0) & (rt == 0)].mean(0)
        r = unit(r - (r * h).sum(-1, keepdims=True) * h)
        p = (Xt * h).sum(-1)                                     # (n_train, layers+1)
        gaps.append(p[yt == 1].mean(0) - p[yt == 0].mean(0))
        harm.append(h)
        refusal.append(r)
        test_fold[te] = k
    dirs = {"harmtext": harm, "refusalorth": refusal}
    for name, seed in (("random", 0), ("random1", 1), ("random2", 2), ("random3", 3)):
        rnd = np.random.default_rng(seed).standard_normal(X.shape[1:])
        dirs[name] = [unit(rnd)] * 5
    fold_directions.gaps = gaps
    return dirs, test_fold


class Intervention:
    """Forward hooks (prepended, so recorded hidden states show the edited values)."""

    def __init__(self, layers):
        self.layers, self.handles = layers, []

    def ablate(self, R, window):
        self.clear()
        for i in WINDOWS[window]:
            self.handles.append(self.layers[i].register_forward_hook(self._ablate(R[i + 1]), prepend=True))

    def add(self, vec, hidden_index):
        self.clear()
        self.handles.append(self.layers[hidden_index - 1].register_forward_hook(self._add(vec), prepend=True))

    @staticmethod
    def _ablate(r):
        def fn(module, inputs, out):
            h = out[0] if isinstance(out, tuple) else out
            hf = h.float()
            h2 = (hf - (hf @ r).unsqueeze(-1) * r).to(h.dtype)
            return (h2, *out[1:]) if isinstance(out, tuple) else h2
        return fn

    @staticmethod
    def _add(v):
        def fn(module, inputs, out):
            h = out[0] if isinstance(out, tuple) else out
            h2 = (h.float() + v).to(h.dtype)
            return (h2, *out[1:]) if isinstance(out, tuple) else h2
        return fn

    def clear(self):
        for h in self.handles:
            h.remove()
        self.handles = []


def coherence(reply):
    words = re.findall(r"[A-Za-z']+", reply.lower())
    return {"n_words": len(words), "distinct_ratio": round(len(set(words)) / len(words), 3) if words else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--conditions", default=None,
                    help="comma-separated names, or batch1 / batch2-gpu0 / batch2-gpu1")
    ap.add_argument("--pairs", type=int, default=None, help="only the first N pairs (smoke test)")
    ap.add_argument("--max-new-tokens", type=int, default=40)
    args = ap.parse_args()

    tag = args.model.rstrip("/").split("/")[-1]
    items = load_items()
    dirs, test_fold = fold_directions(tag, items)
    gaps = fold_directions.gaps
    proc = AutoProcessor.from_pretrained(args.model)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        args.model, dtype=torch.bfloat16, device_map="auto").eval()
    device = next(model.parameters()).device
    hook = Intervention(model.model.language_model.layers)
    Rt = {n: [torch.tensor(r, dtype=torch.float32, device=device) for r in rs] for n, rs in dirs.items()}

    named = {"batch1": BATCH1, "batch2-gpu0": BATCH2_GPU0, "batch2-gpu1": BATCH2_GPU1}
    conds = named.get(args.conditions) or (args.conditions.split(",") if args.conditions else BATCH1)
    keep_pairs = set(sorted({it["pair"] for it in items})[: args.pairs]) if args.pairs else None
    out_root = ROOT / "results" / "interventions" / tag
    for cond in conds:
        c = parse(cond)
        todo = [(i, it) for i, it in enumerate(items) if it["kind"] == c["kind"]
                and (keep_pairs is None or it["pair"] in keep_pairs)]
        t0, done = time.time(), 0
        for i, it in todo:
            k = test_fold[i]
            for modality in c["modalities"]:
                dest = out_root / c["folder"] / modality / it["id"]
                if dest.with_suffix(".json").exists():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                if c["mode"] == "ablate":
                    hook.ablate(Rt[c["direction"]][k], c["window"])
                else:
                    coef = c["strength"] * float(gaps[k][c["layer"]])
                    hook.add(coef * Rt[c["direction"]][k][c["layer"]], c["layer"])
                inputs, _ = build(proc, it, modality)
                inputs = inputs.to(device)
                with torch.inference_mode():
                    gen = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                                         output_hidden_states=True, return_dict_in_generate=True)
                hook.clear()
                h = torch.stack([layer[0, -1].float().cpu() for layer in gen.hidden_states[0]]).numpy()
                reply = proc.batch_decode(gen.sequences[:, inputs["input_ids"].shape[1]:],
                                          skip_special_tokens=True)[0].strip()
                lab, why = label(reply)
                rec = {"id": it["id"], "pair": it["pair"], "kind": c["kind"], "modality": modality,
                       "category": it["category"], "condition": c["folder"], "mode": c["mode"],
                       "direction": c["direction"], "window": c["window"], "layer": c["layer"],
                       "strength": c["strength"], "fold": int(k), "label": lab, "why": why,
                       "refused": int(lab == "REFUSED"), **coherence(reply)}
                if c["kind"] == "harmful":
                    rec["reply_head"] = reply[:160]
                else:
                    rec["reply"] = reply
                np.savez_compressed(dest.with_suffix(".npz"), h=h.astype(np.float16))
                dest.with_suffix(".json").write_text(json.dumps(rec))
                done += 1
                del gen
        n = len(list((out_root / c["folder"]).glob("*/*.json")))
        print(f"{c['folder']}: {n} results ({done} new, {time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
