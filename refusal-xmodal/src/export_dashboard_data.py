"""Export one model's analysis results as {rows, meta} JSON files for the results dashboard.

Reads results/<model>/{metrics_by_layer.json, summary.json, labels.json, oof_scores.npz}
(written by analyze.py) and writes results/<model>/dashboard/{layers,selected,labels,scores}.json.
No reply text is exported: labels carry ids, categories and the refusal label only.

Usage: python src/export_dashboard_data.py Qwen2.5-VL-3B-Instruct
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
model = sys.argv[1]
res = ROOT / "results" / model
out = res / "dashboard"
out.mkdir(exist_ok=True)
code = Path(__file__).read_text()


def write(name, rows, inputs):
    meta = [{"label": "export_dashboard_data.py", "value": code, "type": "code", "lang": "python"},
            {"label": "Model", "value": model}, {"label": "Input", "value": ", ".join(inputs)}]
    (out / f"{name}.json").write_text(json.dumps({"rows": rows, "meta": meta}))
    print(name, len(rows), "rows")


metrics = json.loads((res / "metrics_by_layer.json").read_text())
write("layers", [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in metrics],
      ["metrics_by_layer.json"])

s = json.loads((res / "summary.json").read_text())
L = s["selected_layer_by_text_heldout"]
at = s["at_selected_layer"]
write("selected", [{
    "condition": c, "layer": L, "auroc": round(at[f"{c}_auc"], 4),
    "ci_low": round(s["ci95_at_selected"][c][0], 4), "ci_high": round(s["ci95_at_selected"][c][1], 4),
    "null95": round(at[f"{c}_null95"], 4), "balanced_accuracy": round(at[f"{c}_bal_acc"], 4),
    "cohen_d": round(at[f"{c}_d"], 3), "auroc_train": round(at[f"{c}_auc_train"], 4),
    "refusal_auroc": round(at[f"{c}_refusal_auc"], 4),
    "cosine_text_image": round(at["cosine_text_image"], 4), "cosine_null": round(at["cosine_null"], 4),
    "n_requests": s["n_items"], "n_pairs": s["n_pairs"], "layers": s["layers"], "d_model": s["d_model"],
} for c in ("text", "image", "transfer")], ["summary.json"])

labels = json.loads((res / "labels.json").read_text())
write("labels", [{k: r[k] for k in ("id", "pair", "kind", "modality", "category", "label", "refused", "why")}
                 for r in labels], ["labels.json", "review_decisions.csv"])

o = np.load(res / "oof_scores.npz", allow_pickle=True)
rows = []
for i, rid in enumerate(o["ids"]):
    for cond in ("text", "image", "transfer"):
        rows.append({"id": str(rid), "kind": "harmful" if int(o["y"][i]) else "benign", "condition": cond,
                     "layer": L, "score": round(float(o[cond][L][i]), 4)})
write("scores", rows, ["oof_scores.npz"])
