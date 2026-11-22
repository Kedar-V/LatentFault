"""Figure 5: refusal rates and latency per model and modality, plus a cross-model summary table.

Only per-model scalar summaries are compared. Raw 3B and 7B activations live in different
spaces (d = 2048 vs 3584) and are never compared directly.
"""
import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    S = {p.name: json.loads((p / "summary.json").read_text())
         for p in sorted((ROOT / "results").iterdir()) if (p / "summary.json").exists()}
    if not S:
        raise SystemExit("no summaries yet")
    names = list(S)
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4))
    w = 0.2
    x = np.arange(len(names))
    for k, (mod, kind, c) in enumerate([("text", "harmful", "#c2410c"), ("image", "harmful", "#f59e0b"),
                                        ("text", "benign", "#1f4e9c"), ("image", "benign", "#60a5fa")]):
        a.bar(x + (k - 1.5) * w, [S[n]["refusal_rate"][mod][kind] for n in names], w, color=c,
              label=f"{kind}, {mod}")
    a.set(xticks=x, xticklabels=names, ylabel="observed refusal rate", ylim=(0, 1), title="Refusal rate")
    a.legend(fontsize=8)
    for k, (mod, c) in enumerate([("text", "#1f4e9c"), ("image", "#c2410c")]):
        b.bar(x + (k - 0.5) * 0.35, [S[n]["median_seconds"][mod] for n in names], 0.35, color=c, label=mod)
    b.set(xticks=x, xticklabels=names, ylabel="median seconds per request",
          title="Latency (Orin CPU, fp32, ≤40 new tokens)")
    b.legend(fontsize=8)
    fig.tight_layout()
    (ROOT / "figures").mkdir(exist_ok=True)
    fig.savefig(ROOT / "figures" / "fig5_refusal_latency.png", dpi=200)
    table = {n: {"selected_layer": S[n]["selected_layer_by_text_heldout"], "layers": S[n]["layers"],
                 **{k: S[n]["at_selected_layer"][k] for k in
                    ("text_auc", "image_auc", "transfer_auc", "transfer_null95", "cosine_text_image")},
                 "ci95": S[n]["ci95_at_selected"], "refusal_rate": S[n]["refusal_rate"]} for n in names}
    (ROOT / "results" / "comparison.json").write_text(json.dumps(table, indent=1))
    print(json.dumps(table, indent=1))


if __name__ == "__main__":
    main()
