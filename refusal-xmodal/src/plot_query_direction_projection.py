"""How a harmful and a benign request project onto the learned harm direction (layer 28).

Two data sources:

  --source activations   (full figure; needs results/raw/<model>/text/*.npz, i.e. the GPU server)
      One cross-validation fold (fold 0 of GroupKFold(5) by pair, the fold concept_plane.py uses).
      d      = unit(mean harmful - mean benign) over that fold's TRAINING items, layer 28
      origin = mean of that fold's TRAINING activations
      x      = (h - origin) . d                      for each HELD-OUT item
      y      = first principal component of the training residuals (h - origin) - x d,
               fit on training items only (numpy SVD), applied to held-out residuals.

  --source oof           (mock; runs anywhere, uses results/<model>/oof_scores.npz)
      x is REAL: each item's held-out score from analyze.py (h . d_fold - threshold_fold, where the
      threshold is the midpoint of the training class means), pooled over the 5 folds.
      y is a PLACEHOLDER spread (seeded random), because the orthogonal component needs the full
      activations. The caption says so.

The highlighted pair defaults to JailbreakBench pair 15 (h015 / b015): a topic-matched held-out
pair whose scores sit near both class medians (4th closest of 100 pairs, IQR-normalized), with
short request texts that are safe to print. The texts are read from data/items.json, unaltered.

Usage:
  python src/plot_query_direction_projection.py --source oof
  python src/plot_query_direction_projection.py --source activations
Writes figures/query_direction_projection[_mock].png (3200x1800, 300 dpi) and .svg.
"""
import argparse
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODEL = "Qwen2.5-VL-3B-Instruct"
LAYER = 28
BG, NAVY, TEAL, CORAL = "#FAFBFD", "#0B1730", "#008D98", "#E64B45"
GREY, LIGHT = "#6B7689", "#D5DBE3"


def load_items():
    return json.loads((ROOT / "data" / "items.json").read_text())


def from_oof(items, seed=0):
    z = np.load(ROOT / "results" / MODEL / "oof_scores.npz")
    ids = [str(i) for i in z["ids"]]
    x = z["text"][LAYER]
    rng = np.random.default_rng(seed)
    y = rng.normal(0, 1, len(ids)) * np.std(x) * 0.28  # placeholder vertical spread
    origin = "0 = midpoint of the training class means; held-out scores pooled over 5 folds"
    return ids, np.asarray(z["y"]), x, y, origin


def from_activations(items):
    from sklearn.model_selection import GroupKFold

    raw = ROOT / "results" / "raw" / MODEL / "text"
    X = np.stack([np.load(raw / f"{it['id']}.npz")["h"][LAYER] for it in items]).astype(np.float64)
    lab = np.array([it["harmful"] for it in items])
    groups = np.array([it["pair"] for it in items])
    tr, te = next(iter(GroupKFold(n_splits=5).split(X, lab, groups)))
    d = X[tr][lab[tr] == 1].mean(0) - X[tr][lab[tr] == 0].mean(0)
    d /= np.linalg.norm(d)
    mu = X[tr].mean(0)
    C = X - mu
    xs = C @ d
    R = C - np.outer(xs, d)
    _, _, vt = np.linalg.svd(R[tr] - R[tr].mean(0), full_matrices=False)
    ys = (R - R[tr].mean(0)) @ vt[0]
    ids = [items[i]["id"] for i in te]
    origin = "origin = mean training activation, fold 0; held-out items only"
    return ids, lab[te], xs[te], ys[te], origin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["oof", "activations"], default="oof")
    ap.add_argument("--pair", type=int, default=15)
    args = ap.parse_args()
    items = load_items()
    by_id = {it["id"]: it for it in items}
    ids, lab, x, y, origin = (from_oof if args.source == "oof" else from_activations)(items)
    idx = {k: i for i, k in enumerate(ids)}
    hid, bid = f"h{args.pair:03d}", f"b{args.pair:03d}"
    if hid not in idx or bid not in idx:
        raise SystemExit(f"pair {args.pair} is not in the held-out set for this source")
    hi, bi = idx[hid], idx[bid]

    plt.rcParams.update({"font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "svg.fonttype": "none"})
    fig = plt.figure(figsize=(3200 / 300, 1800 / 300), dpi=300, facecolor=BG)
    ax = fig.add_axes([0.07, 0.30, 0.86, 0.50], facecolor=BG)
    rug = fig.add_axes([0.07, 0.165, 0.86, 0.045], facecolor=BG, sharex=ax)

    # background: all held-out items, pale
    for k, col in ((0, TEAL), (1, CORAL)):
        m = lab == k
        ax.scatter(x[m], y[m], s=9, color=col, alpha=0.22, linewidths=0, zorder=1)

    ylo = min(y.min(), -1) * 1.35
    yhi = max(y.max(), 1) * 1.25
    axis_y = ylo
    pad = (x.max() - x.min()) * 0.06
    ax.set_xlim(x.min() - pad, x.max() + pad)
    ax.set_ylim(axis_y - (yhi - ylo) * 0.30, yhi)

    # the projection axis: the learned direction itself
    ax.annotate("", xy=(x.max() + pad * 0.9, axis_y), xytext=(x.min() - pad * 0.9, axis_y),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.6, mutation_scale=12), zorder=2)
    ax.text((x[hi] + x[bi]) / 2, axis_y + (yhi - ylo) * 0.035, r"learned harm-associated direction $d_{28} \rightarrow$",
            ha="center", va="bottom", fontsize=8.5, color=NAVY, fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.15", fc=BG, ec="none"))

    def highlight(i, col, tag, side):
        ax.plot([x[i], x[i]], [y[i], axis_y], ls=(0, (3, 3)), lw=1.1, color=col, zorder=3)
        ax.scatter([x[i]], [axis_y], s=26, marker="D", color=col, zorder=4, linewidths=0)
        ax.scatter([x[i]], [y[i]], s=150, color=col, edgecolor="white", linewidth=1.6, zorder=5)
        ax.text(x[i], axis_y - (yhi - ylo) * 0.075, f"{x[i]:+.1f}", ha="center", va="top",
                fontsize=9.5, color=col, fontweight="bold")
        goal = textwrap.fill(f"“{by_id[ids[i]]['goal']}”", 34)
        ha = "left" if side > 0 else "right"
        dx = (x.max() - x.min()) * 0.025 * side
        halo = dict(boxstyle="round,pad=0.25", fc=BG, ec="none", alpha=0.9)
        ax.text(x[i] + dx, y[i] + (yhi - ylo) * 0.03, f"{tag} · {ids[i]}", ha=ha, va="bottom",
                fontsize=8.5, color=col, fontweight="bold", bbox=halo, zorder=6)
        ax.text(x[i] + dx, y[i] - (yhi - ylo) * 0.005, goal, ha=ha, va="top", fontsize=7.5, color=NAVY,
                linespacing=1.25, bbox=halo, zorder=6)

    highlight(bi, TEAL, "benign", +1)
    highlight(hi, CORAL, "harmful", -1)

    # distance between the two projections
    gap_y = axis_y - (yhi - ylo) * 0.22
    ax.annotate("", xy=(x[hi], gap_y), xytext=(x[bi], gap_y),
                arrowprops=dict(arrowstyle="<->", color=GREY, lw=0.9, shrinkA=0, shrinkB=0))
    ax.text((x[hi] + x[bi]) / 2, gap_y + (yhi - ylo) * 0.012, f"{x[hi] - x[bi]:.1f} apart along $d_{{28}}$",
            ha="center", va="bottom", fontsize=7.5, color=GREY)

    for a in (ax, rug):
        for s in a.spines.values():
            s.set_visible(False)
        a.set_yticks([])
    ax.set_xticks([])

    # compact projection scale with rug marks
    for k, col in ((0, TEAL), (1, CORAL)):
        rug.vlines(x[lab == k], 0, 1, color=col, alpha=0.28, lw=0.6)
    rug.axhline(0, color=LIGHT, lw=0.8)
    for i, col in ((bi, TEAL), (hi, CORAL)):
        rug.scatter([x[i]], [0.5], s=60, color=col, edgecolor="white", linewidth=1.2, zorder=3)
    rug.set_ylim(-0.2, 1.2)
    rug.tick_params(axis="x", colors=GREY, labelsize=7, length=0, pad=3)
    rug.set_xlabel("projection score along $d_{28}$ (all held-out requests)", fontsize=7.5, color=GREY, labelpad=4)

    fig.text(0.07, 0.93, "A harmful request lands farther along the learned direction than its benign twin",
             fontsize=13, color=NAVY, fontweight="bold", ha="left")
    fig.text(0.07, 0.885, f"Qwen2.5-VL-3B-Instruct · layer {LAYER} residual stream · held-out typed "
             "JailbreakBench requests · teal = benign, coral = harmful", fontsize=8.5, color=GREY, ha="left")
    vert = ("Vertical position: leading orthogonal principal component (fit on training items)."
            if args.source == "activations" else
            "Vertical position is a placeholder spread for readability; it carries no data.")
    cap = (f"Layer {LAYER} activations of held-out requests. Horizontal position is the projection onto a "
           f"harm-associated direction learned from training data ({origin}). {vert} The direction is "
           "defined in the full 2,048-dimensional space. Illustrative examples from held-out data; "
           "not a causal intervention.")
    fig.text(0.07, 0.035, textwrap.fill(cap, 175), fontsize=6.5, color=GREY, ha="left", va="bottom",
             linespacing=1.35)

    out = ROOT / "figures"
    out.mkdir(exist_ok=True)
    stem = "query_direction_projection" + ("" if args.source == "activations" else "_mock")
    fig.savefig(out / f"{stem}.png", dpi=300, facecolor=BG)
    fig.savefig(out / f"{stem}.svg", facecolor=BG)
    print(f"wrote {out / stem}.png/.svg | {hid} {x[hi]:+.2f}  {bid} {x[bi]:+.2f}  "
          f"gap {x[hi] - x[bi]:.2f} | n held-out {len(ids)}")


if __name__ == "__main__":
    main()
