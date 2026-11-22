"""Summarise the ablation runs: refusal rate change per condition, paired against the baseline.

Baseline labels: results/<model>/labels.json (rubric + manual decisions). Intervened labels:
the same rubric (label.py) applied to each intervened reply; manual review of soft refusals
under intervention goes in results/<model>/intervention_review.csv (id,modality,condition,label).

Per condition x modality: refusal rate with a 95% Wilson interval, the paired counts against
the baseline (refused before & not after = b, not before & refused after = c) and an exact
two-sided McNemar p. Benign conditions also report coherence (distinct-word ratio, length)
against the baseline replies, to tell a mechanism apart from a broken model.

Writes results/<model>/interventions_summary.json and figures/fig6_ablation_<model>.png.
Usage: python src/analyze_interventions.py --model Qwen2.5-VL-3B-Instruct
"""
import argparse
import csv
import json
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 3), round(c + h, 3)]


def mcnemar(b, c):
    n, k = b + c, min(b, c)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def coherence(reply):
    w = re.findall(r"[A-Za-z']+", reply.lower())
    return len(w), (len(set(w)) / len(w) if w else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen2.5-VL-3B-Instruct")
    args = ap.parse_args()
    res = ROOT / "results" / args.model
    base = {(r["id"], r["modality"]): r for r in json.loads((res / "labels.json").read_text())}
    raw = ROOT / "results" / "raw" / args.model
    base_reply = {(p.stem, p.parent.name): json.loads(p.read_text())["reply"] for p in raw.glob("*/*.json")}
    review = {}
    rf = res / "intervention_review.csv"
    if rf.exists():
        with open(rf) as fh:
            review = {(r["id"], r["modality"], r["condition"]): r["label"] for r in csv.DictReader(fh)}

    rows = []
    for cdir in sorted((ROOT / "results" / "interventions" / args.model).iterdir()):
        for mod in ("text", "image"):
            recs = [json.loads(p.read_text()) for p in sorted((cdir / mod).glob("*.json"))]
            if not recs:
                continue
            after, before, b, c = 0, 0, 0, 0
            for r in recs:
                lab = review.get((r["id"], mod, cdir.name), r["label"])
                a_ref = int(lab == "REFUSED")
                b_ref = int(base[(r["id"], mod)]["refused"])
                after += a_ref
                before += b_ref
                b += int(b_ref and not a_ref)
                c += int(a_ref and not b_ref)
            n = len(recs)
            row = {"condition": cdir.name, "direction": recs[0]["direction"], "window": recs[0]["window"],
                   "mode": recs[0].get("mode", "ablate"), "layer": recs[0].get("layer"),
                   "strength": recs[0].get("strength"),
                   "kind": recs[0]["kind"], "modality": mod, "n": n,
                   "refusal_before": round(before / n, 3), "refusal_after": round(after / n, 3),
                   "ci_after": wilson(after, n), "ci_before": wilson(before, n),
                   "refused_before_only": b, "refused_after_only": c, "mcnemar_p": round(mcnemar(b, c), 4)}
            if recs[0]["kind"] == "benign":
                la = [coherence(r.get("reply", "")) for r in recs]
                lb = [coherence(base_reply[(r["id"], mod)]) for r in recs]
                row["distinct_ratio_after"] = round(sum(x[1] for x in la) / n, 3)
                row["distinct_ratio_before"] = round(sum(x[1] for x in lb) / n, 3)
                row["words_after"] = round(sum(x[0] for x in la) / n, 1)
                row["words_before"] = round(sum(x[0] for x in lb) / n, 1)
            rows.append(row)
            print(f"{cdir.name:32} {mod:5} n={n:3} refusal {before / n:.2f} -> {after / n:.2f} "
                  f"(b={b}, c={c}, p={row['mcnemar_p']:.2g})"
                  + (f" | distinct words {row['distinct_ratio_before']:.2f} -> {row['distinct_ratio_after']:.2f}"
                     if "distinct_ratio_after" in row else ""))
    (res / "interventions_summary.json").write_text(json.dumps(rows, indent=1))
    figure(args.model, rows)
    figure_addition(args.model, rows, base)
    figure_random_range(args.model, rows)


def figure_addition(model, rows, base):
    """Fig 7: benign refusal rate vs strength of the added harm direction, by layer and modality."""
    add = [r for r in rows if r["mode"] == "add" and r["direction"] == "harmtext"]
    if not add:
        return
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for (layer, mod), (col, ls) in {(20, "text"): ("#1f4e9c", "-"), (20, "image"): ("#c2410c", "-"),
                                    (12, "text"): ("#1f4e9c", "--"), (12, "image"): ("#c2410c", "--")}.items():
        pts = sorted((r["strength"], r["refusal_after"], r["ci_after"]) for r in add
                     if r["layer"] == layer and r["modality"] == mod)
        if not pts:
            continue
        b0 = next(r["refusal_before"] for r in add if r["modality"] == mod)
        xs, ys = [0.0] + [p[0] for p in pts], [b0] + [p[1] for p in pts]
        ax.plot(xs, ys, color=col, ls=ls, marker="o", lw=2, label=f"{mod}, added at layer {layer}")
        for s, _, (lo, hi) in pts:
            ax.plot([s, s], [lo, hi], color=col, alpha=0.3, lw=4)
    for r in rows:
        if r["mode"] == "add" and r["direction"].startswith("random"):
            ax.scatter([r["strength"]], [r["refusal_after"]], marker="x", s=70, zorder=4,
                       color="#1f4e9c" if r["modality"] == "text" else "#c2410c",
                       label=f"random direction, {r['modality']}, layer {r['layer']}")
    ax.set(xlabel="strength added (× harmful–benign gap at that layer)", ylabel="refusal rate on BENIGN requests",
           ylim=(-0.02, 1.02), title=f"{model}: adding the text-learned harm direction")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / f"fig7_addition_{model}.png", dpi=200)


def figure_random_range(model, rows):
    """Fig 8: refusal change from removing each direction, with every random direction shown."""
    sets = [("harmful", "late", "harmful requests, layers 19–36 removed"),
            ("benign", "all", "benign requests, all layers removed")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, (kind, window, title) in zip(axes, sets):
        for x, mod in ((0, "text"), (1, "image")):
            for r in rows:
                if r["mode"] != "ablate" or r["kind"] != kind or r["window"] != window or r["modality"] != mod:
                    continue
                delta = r["refusal_after"] - r["refusal_before"]
                d = r["direction"]
                style = ({"color": "#7c3aed", "marker": "D", "s": 70} if d == "harmtext" else
                         {"color": "#0f766e", "marker": "s", "s": 60} if d == "refusalorth" else
                         {"color": "#9ca3af", "marker": "o", "s": 40})
                ax.scatter([x + (0.08 if d.startswith("random") else 0)], [delta], zorder=3, **style)
        ax.axhline(0, color="black", lw=0.6)
        ax.set(xticks=[0, 1], xticklabels=["text", "image"], xlim=(-0.5, 1.5), title=title)
    axes[0].set_ylabel("change in refusal rate (after − before)")
    from matplotlib.lines import Line2D
    axes[1].legend(handles=[Line2D([], [], color=c, marker=m, ls="", label=l) for c, m, l in
                            (("#7c3aed", "D", "harm direction"), ("#0f766e", "s", "refusal direction (⊥ harm)"),
                             ("#9ca3af", "o", "random directions"))], fontsize=8)
    fig.suptitle(f"{model}: how specific is the effect?")
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / f"fig8_random_range_{model}.png", dpi=200)


def figure(model, rows):
    order = [("harmtext", "late"), ("harmtext", "early"), ("harmtext", "all"),
             ("random", "late"), ("random", "early"), ("random", "all")]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, kind in zip(axes, ("harmful", "benign")):
        ylab, y = [], 0
        for d, w in order:
            for mod, col in (("text", "#1f4e9c"), ("image", "#c2410c")):
                r = next((x for x in rows if x["direction"] == d and x["window"] == w
                          and x["kind"] == kind and x["modality"] == mod), None)
                if r is None:
                    continue
                ax.plot([r["refusal_before"], r["refusal_after"]], [y, y], color=col, lw=2, alpha=0.6)
                ax.scatter([r["refusal_before"]], [y], color="white", edgecolor=col, zorder=3, s=40)
                ax.scatter([r["refusal_after"]], [y], color=col, zorder=3, s=40)
                lo, hi = r["ci_after"]
                ax.plot([lo, hi], [y, y], color=col, lw=6, alpha=0.15)
                ylab.append((y, f"{'harm' if d == 'harmtext' else 'random'} dir, {w} layers, {mod}"))
                y += 1
            y += 0.5
        ax.set_yticks([t for t, _ in ylab], [s for _, s in ylab], fontsize=8)
        ax.set(xlim=(-0.02, 1.02), xlabel="refusal rate (○ baseline → ● with direction removed)",
               title=f"{kind} requests")
        ax.invert_yaxis()
    fig.suptitle(f"{model}: removing a direction from the residual stream (held-out directions, 40-token replies)")
    fig.tight_layout()
    (ROOT / "figures").mkdir(exist_ok=True)
    fig.savefig(ROOT / "figures" / f"fig6_ablation_{model}.png", dpi=200)


if __name__ == "__main__":
    main()
