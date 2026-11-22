"""3D view of the same idea as plot_query_direction_projection.py: one axis is the learned direction.

Layer 28, typed JailbreakBench requests, one cross-validation fold (fold 0 of GroupKFold(5) by pair):
  d      = unit(mean harmful - mean benign) over the fold's TRAINING items
  origin = mean of the fold's TRAINING activations
  x      = (h - origin) . d                                   (the real projection, axis 1)
  y, z   = first two principal components of the training residuals (h - origin) - x d,
           fit on training items only (numpy SVD), applied to every item.
Held-out items are drawn large; training items faint, for context. The highlighted pair is
h015 / b015 when it is held out in fold 0, otherwise the held-out pair closest to both class medians.

Usage: python src/plot_query_direction_3d.py --raw results/raw_forward/Qwen2.5-VL-3B-Instruct/text
Writes figures/query_direction_3d.png (3200x1800, 300 dpi), .svg and query_direction_3d.json (coordinates).
"""
import argparse
import json
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.model_selection import GroupKFold  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAYER = 28
BG, NAVY, TEAL, CORAL, GREY = "#FAFBFD", "#0B1730", "#008D98", "#E64B45", "#6B7689"


def load(raw, items):
    out = []
    for it in items:
        p = raw / f"{it['id']}.npy"
        out.append(np.load(p)[LAYER] if p.exists() else np.load(raw / f"{it['id']}.npz")["h"][LAYER])
    return np.stack(out).astype(np.float64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--pair", type=int, default=15)
    args = ap.parse_args()
    items = json.loads((ROOT / "data" / "items.json").read_text())
    X = load(ROOT / args.raw, items)
    lab = np.array([it["harmful"] for it in items])
    groups = np.array([it["pair"] for it in items])
    tr, te = next(iter(GroupKFold(n_splits=5).split(X, lab, groups)))
    d = X[tr][lab[tr] == 1].mean(0) - X[tr][lab[tr] == 0].mean(0)
    d /= np.linalg.norm(d)
    mu = X[tr].mean(0)
    C = X - mu
    x = C @ d
    R = C - np.outer(x, d)
    rmu = R[tr].mean(0)
    _, sv, vt = np.linalg.svd(R[tr] - rmu, full_matrices=False)
    y, z = (R - rmu) @ vt[0], (R - rmu) @ vt[1]
    var = sv ** 2 / (sv ** 2).sum()

    held = np.zeros(len(items), bool)
    held[te] = True
    ids = [it["id"] for it in items]
    pairs_te = sorted({groups[i] for i in te})
    if args.pair in pairs_te:
        p = args.pair
    else:  # held-out pair closest to both held-out class medians
        mh, mb = np.median(x[te][lab[te] == 1]), np.median(x[te][lab[te] == 0])
        p = min(pairs_te, key=lambda q: abs(x[ids.index(f"h{q:03d}")] - mh) + abs(x[ids.index(f"b{q:03d}")] - mb))
    hi, bi = ids.index(f"h{p:03d}"), ids.index(f"b{p:03d}")

    plt.rcParams.update({"font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"], "svg.fonttype": "none"})
    fig = plt.figure(figsize=(3200 / 300, 1800 / 300), dpi=300, facecolor=BG)
    ax = fig.add_axes([0.0, 0.08, 0.72, 0.84], projection="3d", facecolor=BG)
    ax.view_init(elev=16, azim=-62)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((0.96, 0.97, 0.98, 1.0))
        pane.set_edgecolor("#E3E7ED")
    ax.grid(False)
    for k, col in ((0, TEAL), (1, CORAL)):
        m = (lab == k) & ~held
        ax.scatter(x[m], y[m], z[m], s=5, color=col, alpha=0.18, depthshade=False, linewidths=0)
        m = (lab == k) & held
        ax.scatter(x[m], y[m], z[m], s=16, color=col, alpha=0.55, depthshade=False, linewidths=0)
    zfloor = z.min() - 0.08 * np.ptp(z)
    y0 = y.min() - 0.05 * np.ptp(y)
    ax.plot([x.min(), x.max()], [y0, y0], [zfloor, zfloor], color=NAVY, lw=1.8)
    for i, col in ((bi, TEAL), (hi, CORAL)):
        ax.plot([x[i], x[i]], [y[i], y0], [z[i], zfloor], ls=(0, (3, 3)), lw=1.1, color=col)
        ax.scatter([x[i]], [y0], [zfloor], s=26, marker="D", color=col, depthshade=False)
        ax.scatter([x[i]], [y[i]], [z[i]], s=150, color=col, edgecolor="white", linewidth=1.6, depthshade=False)
        ax.text(x[i] + 0.04 * np.ptp(x), y0, zfloor + 0.05 * np.ptp(z), f"{x[i]:+.1f}", color=col, fontsize=9,
                fontweight="bold", ha="left")
    ax.set_xlim(x.min(), x.max())
    ax.set_xlabel(r"learned harm direction $d_{28}$ $\rightarrow$", fontsize=8.5, color=NAVY, labelpad=6)
    ax.set_ylabel(f"PC1 ⊥ d ({var[0]:.0%})", fontsize=7.5, color=GREY, labelpad=2)
    ax.set_zlabel(f"PC2 ⊥ d ({var[1]:.0%})", fontsize=7.5, color=GREY, labelpad=2)
    ax.tick_params(labelsize=6, colors=GREY, pad=0)
    ax.set_yticklabels([])
    ax.set_zticklabels([])

    side = fig.add_axes([0.70, 0.08, 0.28, 0.84])
    side.axis("off")
    by = {it["id"]: it for it in items}
    yy = 0.78
    for i, col, tag in ((hi, CORAL, "harmful"), (bi, TEAL, "benign")):
        side.text(0, yy, f"{tag} · {ids[i]} · {x[i]:+.1f}", color=col, fontsize=9, fontweight="bold",
                  transform=side.transAxes)
        side.text(0, yy - 0.04, textwrap.fill(f"“{by[ids[i]]['goal']}”", 38), color=NAVY,
                  fontsize=7.5, va="top", transform=side.transAxes, linespacing=1.3)
        yy -= 0.27
    side.text(0, 0.18, f"{x[hi] - x[bi]:.1f} apart along $d_{{28}}$", color=GREY, fontsize=8,
              transform=side.transAxes)

    fig.text(0.04, 0.93, "A harmful request lands farther along the learned direction than its benign twin",
             fontsize=13, color=NAVY, fontweight="bold")
    fig.text(0.04, 0.885, "Qwen2.5-VL-3B-Instruct · layer 28 residual stream · typed JailbreakBench "
             "requests · teal = benign, coral = harmful", fontsize=8.5, color=GREY)
    cap = ("Axis 1 is the projection onto the harm direction learned from fold-0 training items (origin = mean "
           "training activation). Axes 2–3 are the leading principal components of what remains after "
           "removing that direction, fit on training items only. Large dots: held-out requests; faint: training. "
           "Activations recomputed on CPU (float32). Illustrative; not a causal intervention.")
    fig.text(0.04, 0.025, textwrap.fill(cap, 190), fontsize=6.3, color=GREY, linespacing=1.35)

    out = ROOT / "figures"
    out.mkdir(exist_ok=True)
    fig.savefig(out / "query_direction_3d.png", dpi=300, facecolor=BG)
    fig.savefig(out / "query_direction_3d.svg", facecolor=BG)
    held_auc = None
    try:
        from sklearn.metrics import roc_auc_score
        held_auc = float(roc_auc_score(lab[te], x[te]))
    except Exception:  # noqa: BLE001
        pass
    summary = {"pair": int(p), ids[hi]: round(float(x[hi]), 3), ids[bi]: round(float(x[bi]), 3),
               "heldout_auroc_x": held_auc, "pc_var_share": [round(float(v), 4) for v in var[:2]],
               "n_train": int(len(tr)), "n_heldout": int(len(te))}
    (out / "query_direction_3d.json").write_text(json.dumps(summary, indent=1))
    # plotted coordinates only (3 numbers per request), for redrawing the figure elsewhere
    pts = [{"id": ids[i], "harmful": int(lab[i]), "heldout": bool(held[i]),
            "x": round(float(x[i]), 3), "y": round(float(y[i]), 3), "z": round(float(z[i]), 3)} for i in range(len(ids))]
    (out / "query_direction_3d_points.json").write_text(json.dumps({**summary, "highlight": [ids[hi], ids[bi]],
                                                                    "points": pts}))
    print(summary)


if __name__ == "__main__":
    main()
