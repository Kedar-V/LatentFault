"""Export batch-2 causal results as {rows, meta} JSON for the results dashboard (no activations).

One row per condition x input type: adding the harm direction (strength-response, layers 20
and 12), the random add control, four random directions removed, and the refusal direction
removed. Harm-direction batch-1 rows are included as the reference points.
Input: results/<model>/interventions_summary.json (written by analyze_interventions.py).
Usage: python src/export_batch2_dashboard.py <interventions_summary.json> <out.json>
"""
import json
import sys
from pathlib import Path

src, dst = sys.argv[1], sys.argv[2]
code = Path(__file__).read_text()
S = json.loads(Path(src).read_text())
keep = lambda c: (c.startswith("add-") or c.startswith("ablate-random") or c.startswith("ablate-refusalorth")
                  or c in ("ablate-harmtext-late-harmful", "ablate-harmtext-all-benign"))  # noqa: E731
rows = []
for r in S:
    if not keep(r["condition"]):
        continue
    rows.append({"key": f"{r['condition']}|{r['modality']}", "condition": r["condition"],
                 "mode": r.get("mode") or ("add" if r["condition"].startswith("add-") else "ablate"),
                 "direction": r["direction"], "window": r["window"], "layer": r.get("layer"),
                 "strength": r.get("strength"), "kind": r["kind"], "modality": r["modality"], "n": r["n"],
                 "refusal_before": r["refusal_before"], "refusal_after": r["refusal_after"],
                 "change": round(r["refusal_after"] - r["refusal_before"], 3),
                 "ci_low": r["ci_after"][0], "ci_high": r["ci_after"][1],
                 "flipped_to_comply": r["refused_before_only"], "flipped_to_refuse": r["refused_after_only"],
                 "mcnemar_p": r["mcnemar_p"]})
meta = [{"label": "export_batch2_dashboard.py", "value": code, "type": "code", "lang": "python"},
        {"label": "Model", "value": "Qwen2.5-VL-3B-Instruct"}, {"label": "Input", "value": "interventions_summary.json"}]
Path(dst).write_text(json.dumps({"rows": rows, "meta": meta}))
print(len(rows), "rows")
