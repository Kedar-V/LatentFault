"""Per-layer refusal-direction analysis for one model.

Direction (per layer): r = mean(train harmful) - mean(train benign), unit-normalised, computed
ONLY on training folds (5-fold, grouped by pair so a pair's harmful+benign, text+image, share a
fold). Score = projection onto r minus the midpoint of the two training class means, so
out-of-fold scores from different folds are on one scale and 0 is the training threshold.

Reported per layer, held-out (out-of-fold) unless marked train:
  text    : AUROC / balanced accuracy / Cohen's d for harmful vs benign, text inputs
  image   : the same, image (rendered-card) inputs, image-derived direction
  transfer: TEXT-derived direction and threshold applied to held-out IMAGE inputs
  refusal : AUROC of the same scores against OBSERVED refusal labels (from label.py)
  cosine  : cos(text direction, image direction), all data, plus a shuffled-label null
  null    : 95th percentile of held-out AUROC over 50 within-pair label shuffles
CIs: 95% bootstrap over pairs (1000 resamples) on pooled out-of-fold scores.

The "selected layer" is chosen on TEXT held-out AUROC only; image/transfer numbers at that
layer are therefore not selected on their own outcome.

Usage: env/bin/python src/analyze.py --model Qwen2.5-VL-3B-Instruct
"""
import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from label import label_dir
from prompts import load_items

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(0)


def load(model):
    raw = ROOT / "results" / "raw" / model
    items = load_items()
    keep, X = [], {"text": [], "image": []}
    for it in items:
        paths = [raw / m / f"{it['id']}.npz" for m in ("text", "image")]
        if all(p.exists() for p in paths):
            keep.append(it)
            for m, p in zip(("text", "image"), paths):
                X[m].append(np.load(p)["h"])
    return keep, {m: np.stack(v) for m, v in X.items()}


def direction(Xtr, ytr):
    r = Xtr[ytr == 1].mean(0) - Xtr[ytr == 0].mean(0)
    r = r / (np.linalg.norm(r) + 1e-12)
    p = Xtr @ r
    thr = 0.5 * (p[ytr == 1].mean() + p[ytr == 0].mean())
    return r, thr


def bal_acc(y, s):
    pred = (s > 0).astype(int)
    return 0.5 * ((pred[y == 1] == 1).mean() + (pred[y == 0] == 0).mean())


def cohen_d(y, s):
    a, b = s[y == 1], s[y == 0]
    sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / (sp + 1e-12))


def auc(y, s):
    return float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else float("nan")


def boot_ci(y, s, groups, n=1000):
    ug = np.unique(groups)
    idx = {g: np.where(groups == g)[0] for g in ug}
    vals = []
    for _ in range(n):
        pick = np.concatenate([idx[g] for g in RNG.choice(ug, len(ug))])
        if len(np.unique(y[pick])) == 2:
            vals.append(roc_auc_score(y[pick], s[pick]))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def shuffle_within_pairs(y, groups):
    y2 = y.copy()
    for g in np.unique(groups):
        i = np.where(groups == g)[0]
        if RNG.random() < 0.5:
            y2[i] = y2[i][::-1]
    return y2


def oof_scores(Xs, Xt, y, groups, folds):
    """Direction fit on source Xs (train folds), scored on target Xt (held-out folds)."""
    s_out, s_train_auc = np.zeros(len(y)), []
    for tr, te in folds:
        r, thr = direction(Xs[tr], y[tr])
        s_out[te] = Xt[te] @ r - thr
        s_train_auc.append(auc(y[tr], Xs[tr] @ r - thr))
    return s_out, float(np.mean(s_train_auc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen2.5-VL-3B-Instruct")
    ap.add_argument("--perms", type=int, default=50)
    args = ap.parse_args()
    out = ROOT / "results" / args.model
    labels = {(r["id"], r["modality"]): r for r in label_dir(ROOT / "results" / "raw" / args.model)}
    items, X = load(args.model)
    n, L, d = X["text"].shape
    y = np.array([it["harmful"] for it in items])
    groups = np.array([it["pair"] for it in items])
    refused = {m: np.array([labels[(it["id"], m)]["refused"] for it in items]) for m in ("text", "image")}
    folds = list(GroupKFold(n_splits=5).split(X["text"][:, 0], y, groups))
    print(f"{args.model}: {n} items ({len(np.unique(groups))} pairs), {L} layers, d={d}", flush=True)

    rows, oof = [], {"text": np.zeros((L, n)), "image": np.zeros((L, n)), "transfer": np.zeros((L, n))}
    for l in range(L):
        Xt, Xi = X["text"][:, l], X["image"][:, l]
        row = {"layer": l}
        for name, Xs, Xtgt in (("text", Xt, Xt), ("image", Xi, Xi), ("transfer", Xt, Xi)):
            s, tr_auc = oof_scores(Xs, Xtgt, y, groups, folds)
            oof[name][l] = s
            tgt_mod = "text" if name == "text" else "image"
            null = []
            for _ in range(args.perms):
                ys = shuffle_within_pairs(y, groups)
                ss, _ = oof_scores(Xs, Xtgt, ys, groups, folds)
                null.append(auc(ys, ss))
            row.update({
                f"{name}_auc": auc(y, s), f"{name}_auc_train": tr_auc,
                f"{name}_bal_acc": float(bal_acc(y, s)), f"{name}_d": cohen_d(y, s),
                f"{name}_null95": float(np.percentile(null, 95)),
                f"{name}_refusal_auc": auc(refused[tgt_mod], s),
            })
        rt, _ = direction(Xt, y)
        ri, _ = direction(Xi, y)
        ys = shuffle_within_pairs(y, groups)
        row["cosine_text_image"] = float(rt @ ri)
        row["cosine_null"] = float(direction(Xt, ys)[0] @ direction(Xi, shuffle_within_pairs(y, groups))[0])
        rows.append(row)
        print(f"L{l:02d} text {row['text_auc']:.3f} image {row['image_auc']:.3f} "
              f"transfer {row['transfer_auc']:.3f} cos {row['cosine_text_image']:+.3f} "
              f"(null95 {row['text_null95']:.3f})", flush=True)

    best = int(np.nanargmax([r["text_auc"] for r in rows]))
    summary = {
        "model": args.model, "n_items": n, "n_pairs": int(len(np.unique(groups))), "layers": L, "d_model": d,
        "selected_layer_by_text_heldout": best,
        "at_selected_layer": {k: rows[best][k] for k in rows[best] if k != "layer"},
        "ci95_at_selected": {name: boot_ci(y, oof[name][best], groups) for name in oof},
        "refusal_rate": {m: {k: float(refused[m][y == (k == "harmful")].mean()) for k in ("harmful", "benign")}
                         for m in ("text", "image")},
        "label_counts": {m: {lab: sum(1 for it in items if labels[(it["id"], m)]["label"] == lab)
                             for lab in ("REFUSED", "COMPLIED", "AMBIGUOUS")} for m in ("text", "image")},
        "median_seconds": {m: float(np.median([labels[(it["id"], m)]["seconds"] for it in items]))
                           for m in ("text", "image")},
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics_by_layer.json").write_text(json.dumps(rows, indent=1))
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    np.savez_compressed(out / "oof_scores.npz", ids=np.array([it["id"] for it in items]), y=y,
                        groups=groups, refused_text=refused["text"], refused_image=refused["image"], **oof)
    figures(args.model, rows, oof, y, best)
    print(json.dumps(summary, indent=1))


def figures(model, rows, oof, y, best):
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(exist_ok=True)
    L = np.array([r["layer"] for r in rows])
    g = lambda k: np.array([r[k] for r in rows])  # noqa: E731

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for name, c in (("text", "#1f4e9c"), ("image", "#c2410c")):
        ax.plot(L, g(f"{name}_auc"), color=c, lw=2, label=f"{name}: held-out")
        ax.plot(L, g(f"{name}_auc_train"), color=c, lw=1, ls="--", label=f"{name}: train")
        ax.fill_between(L, 0.5, g(f"{name}_null95"), color=c, alpha=0.08)
    ax.axvline(best, color="grey", ls=":", lw=1)
    ax.set(xlabel="layer", ylabel="AUROC, harmful vs benign", ylim=(0.4, 1.02),
           title=f"{model}: refusal-direction separation by layer\n(shaded: 95th pct of within-pair shuffled-label null)")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(fig_dir / f"fig1_auroc_by_layer_{model}.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(L, g("text_auc"), color="#1f4e9c", lw=1.5, label="text → text (held-out)")
    ax.plot(L, g("transfer_auc"), color="#7c3aed", lw=2.2, label="text direction → image inputs (held-out)")
    ax.plot(L, g("image_auc"), color="#c2410c", lw=1.5, ls="--", label="image → image (held-out)")
    ax.fill_between(L, 0.5, g("transfer_null95"), color="#7c3aed", alpha=0.1, label="transfer null 95th pct")
    ax.set(xlabel="layer", ylabel="AUROC", ylim=(0.4, 1.02), title=f"{model}: text-to-image transfer")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(fig_dir / f"fig2_transfer_{model}.png", dpi=200); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(L, g("cosine_text_image"), color="#0f766e", lw=2, label="cos(text dir, image dir)")
    ax.plot(L, g("cosine_null"), color="grey", lw=1, label="shuffled-label null")
    ax.axhline(0, color="black", lw=0.6)
    ax.set(xlabel="layer", ylabel="cosine similarity", ylim=(-0.2, 1.0),
           title=f"{model}: text- vs image-derived refusal directions")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(fig_dir / f"fig3_cosine_{model}.png", dpi=200); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, name in zip(axes, ("text", "image", "transfer")):
        s = oof[name][best]
        bins = np.linspace(s.min(), s.max(), 30)
        ax.hist(s[y == 0], bins=bins, color="#1f4e9c", alpha=0.6, label="benign")
        ax.hist(s[y == 1], bins=bins, color="#c2410c", alpha=0.6, label="harmful")
        ax.axvline(0, color="black", lw=0.8)
        ax.set(title=f"{name} (layer {best}, held-out)", xlabel="projection − train threshold")
    axes[0].set_ylabel("count"); axes[0].legend(fontsize=8)
    fig.suptitle(f"{model}: held-out projection scores")
    fig.tight_layout(); fig.savefig(fig_dir / f"fig4_projections_{model}.png", dpi=200); plt.close(fig)


if __name__ == "__main__":
    main()
