"""Export causal-test summaries as {rows, meta} JSON for the results dashboard (no activations).

  interventions.json  one row per finished ablation condition x modality (batch 1): refusal rate
                      before/after with 95% Wilson interval, paired counts, exact McNemar p,
                      coherence for benign sets. From results/<model>/interventions_summary.json.
  plane_means.json    mean concept-plane coordinates per layer for harmful requests (baseline and
                      each ablation) and for benign baseline. From results/<model>/concept_plane.json.

Usage: python src/export_causal_dashboard.py Qwen2.5-VL-3B-Instruct
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
model = sys.argv[1]
res = ROOT / "results" / model
out = res / "dashboard"
out.mkdir(exist_ok=True)
code = Path(__file__).read_text()
BATCH1 = {"ablate-harmtext-late-harmful", "ablate-harmtext-early-harmful", "ablate-random-late-harmful",
          "ablate-random-early-harmful", "ablate-harmtext-all-harmful", "ablate-random-all-harmful",
          "ablate-harmtext-all-benign", "ablate-random-all-benign"}


def write(name, rows, inputs):
    meta = [{"label": "export_causal_dashboard.py", "value": code, "type": "code", "lang": "python"},
            {"label": "Model", "value": model}, {"label": "Input", "value": ", ".join(inputs)}]
    (out / f"{name}.json").write_text(json.dumps({"rows": rows, "meta": meta}))
    print(name, len(rows), "rows")


S = json.loads((res / "interventions_summary.json").read_text())
rows = []
for r in S:
    if r["condition"] not in BATCH1:
        continue
    rows.append({"key": f"{r['condition']}|{r['modality']}", "condition": r["condition"],
                 "direction": r["direction"], "window": r["window"], "kind": r["kind"],
                 "modality": r["modality"], "n": r["n"],
                 "refusal_before": r["refusal_before"], "refusal_after": r["refusal_after"],
                 "ci_low": r["ci_after"][0], "ci_high": r["ci_after"][1],
                 "flipped_to_comply": r["refused_before_only"], "flipped_to_refuse": r["refused_after_only"],
                 "mcnemar_p": r["mcnemar_p"],
                 "distinct_before": r.get("distinct_ratio_before"), "distinct_after": r.get("distinct_ratio_after")})
write("interventions", rows, ["interventions_summary.json"])

cp = json.loads((res / "concept_plane.json").read_text())
acc = defaultdict(list)
for p in cp["points"]:
    if p["kind"] == "harmful" or p["condition"] == "baseline":
        acc[(p["condition"], p["kind"], p["modality"])].append(p["xy"])
rows = []
for (cond, kind, mod), xys in sorted(acc.items()):
    a = np.array(xys)  # (n, layers, 2)
    m = a.mean(0)
    for layer in range(1, a.shape[1]):
        rows.append({"series": f"{cond}|{kind}|{mod}", "condition": cond, "kind": kind, "modality": mod,
                     "layer": layer, "harm_axis": round(float(m[layer, 0]), 3),
                     "refusal_axis": round(float(m[layer, 1]), 3), "n": len(xys)})
write("plane_means", rows, ["concept_plane.json (basis: " + cp["basis"] + ")"])
