"""Concept plane: every request placed on two meaningful axes, at every layer, with intervention arrows.

  x = projection on the harm direction        mean(harmful) - mean(benign), text activations
  y = projection on the refusal direction     mean(benign refused) - mean(benign complied), text,
                                               made orthogonal to the harm direction
Both directions are fit on the TRAINING items of fold 0 only (baseline activations); every point,
held-out or intervened, is projected into that fixed basis, which is never refit per condition.
The 30 over-refused benign requests are what make the refusal axis separable from the harm axis.

Arrows join a harmful request's baseline position to its position under an ablation condition
(same request, same modality, same layer). The model's own refusal decision is the outline.

Writes figures/interactive/concept_plane_<model>.html (layer slider) and
results/<model>/concept_plane.json (coordinates, for the notebook and dashboard).
Usage: python src/concept_plane.py --model Qwen2.5-VL-3B-Instruct [--conditions a,b]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from sklearn.model_selection import GroupKFold

from prompts import load_items

ROOT = Path(__file__).resolve().parent.parent
COL = {"harmful": "#c2410c", "benign": "#1f4e9c"}


def unit(v):
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen2.5-VL-3B-Instruct")
    ap.add_argument("--conditions", default="ablate-harmtext-late-harmful,ablate-harmtext-early-harmful")
    args = ap.parse_args()
    items = load_items()
    raw = ROOT / "results" / "raw" / args.model
    labels = {(r["id"], r["modality"]): r for r in
              json.loads((ROOT / "results" / args.model / "labels.json").read_text())}
    X = {m: np.stack([np.load(raw / m / f"{it['id']}.npz")["h"] for it in items]) for m in ("text", "image")}
    y = np.array([it["harmful"] for it in items])
    ref = np.array([labels[(it["id"], "text")]["refused"] for it in items])
    groups = np.array([it["pair"] for it in items])
    tr, te = next(iter(GroupKFold(n_splits=5).split(X["text"][:, 0], y, groups)))
    train = np.zeros(len(items), bool)
    train[tr] = True

    Xt = X["text"][train]
    harm = unit(Xt[y[train] == 1].mean(0) - Xt[y[train] == 0].mean(0))                     # (L, d)
    ben = (y[train] == 0)
    refuse = Xt[ben & (ref[train] == 1)].mean(0) - Xt[ben & (ref[train] == 0)].mean(0)
    refuse = unit(refuse - (refuse * harm).sum(-1, keepdims=True) * harm)                # orthogonal to harm
    L = harm.shape[0]
    cos_raw = [float(np.dot(unit(Xt[ben & (ref[train] == 1)].mean(0)[l] - Xt[ben & (ref[train] == 0)].mean(0)[l]),
                            harm[l])) for l in range(L)]

    def coords(H):  # H: (n, L, d) -> (n, L, 2)
        return np.stack([(H * harm).sum(-1), (H * refuse).sum(-1)], -1)

    pts = []
    for m in ("text", "image"):
        C = coords(X[m])
        for i, it in enumerate(items):
            pts.append({"id": it["id"], "kind": it["kind"], "modality": m, "category": it["category"],
                        "split": "train" if train[i] else "held-out", "condition": "baseline",
                        "refused": int(labels[(it["id"], m)]["refused"]), "xy": C[i].round(3).tolist()})
    idx = {it["id"]: i for i, it in enumerate(items)}
    for cond in [c for c in args.conditions.split(",") if c]:
        d = ROOT / "results" / "interventions" / args.model / cond
        for m in ("text", "image"):
            for p in sorted((d / m).glob("*.json")):
                rec = json.loads(p.read_text())
                H = np.load(p.with_suffix(".npz"))["h"].astype(np.float32)[None]
                i = idx[rec["id"]]
                pts.append({"id": rec["id"], "kind": rec["kind"], "modality": m, "category": rec["category"],
                            "split": "train" if train[i] else "held-out", "condition": cond,
                            "refused": rec["refused"], "xy": coords(H)[0].round(3).tolist()})
    out = {"model": args.model, "layers": L, "basis": "fold-0 training items, baseline text activations",
           "cos_harm_vs_raw_refusal_direction": [round(c, 3) for c in cos_raw], "points": pts}
    (ROOT / "results" / args.model / "concept_plane.json").write_text(json.dumps(out))
    figure(args.model, out, [c for c in args.conditions.split(",") if c])


def figure(model, out, conds):
    pts, L = out["points"], out["layers"]
    base = [p for p in pts if p["condition"] == "baseline"]
    layers = list(range(1, L))

    def traces(l):
        tr = []
        for kind in ("benign", "harmful"):
            for m, sym in (("text", "circle"), ("image", "diamond")):
                sub = [p for p in base if p["kind"] == kind and p["modality"] == m]
                tr.append(go.Scatter(
                    x=[p["xy"][l][0] for p in sub], y=[p["xy"][l][1] for p in sub], mode="markers",
                    name=f"{kind} · {m}", legendgroup=f"{kind}{m}",
                    marker=dict(symbol=sym if all(p["refused"] for p in sub[:0]) else sym, size=7,
                                color=[COL[kind] if p["refused"] else "rgba(0,0,0,0)" for p in sub],
                                line=dict(color=COL[kind], width=1.5)),
                    text=[f"{p['id']} · {p['category']} · {m} · {'refused' if p['refused'] else 'complied'}"
                          f" · {p['split']}" for p in sub], hoverinfo="text"))
        for c, dash in zip(conds, ("solid", "dot")):
            moved = {(p["id"], p["modality"]): p for p in pts if p["condition"] == c}
            xs, ys = [], []
            for p in base:
                q = moved.get((p["id"], p["modality"]))
                if q:
                    xs += [p["xy"][l][0], q["xy"][l][0], None]
                    ys += [p["xy"][l][1], q["xy"][l][1], None]
            tr.append(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#7c3aed", width=0.8, dash=dash),
                                 opacity=0.5, name=f"→ {c.replace('ablate-harmtext-', 'remove harm dir, ').replace('-harmful', '')}",
                                 hoverinfo="skip"))
            sub = list(moved.values())
            tr.append(go.Scatter(x=[q["xy"][l][0] for q in sub], y=[q["xy"][l][1] for q in sub], mode="markers",
                                 marker=dict(size=5, color=["#7c3aed" if q["refused"] else "rgba(0,0,0,0)" for q in sub],
                                             line=dict(color="#7c3aed", width=1)),
                                 name=f"after: {c.split('-')[2]} layers", hoverinfo="text",
                                 text=[f"{q['id']} {q['modality']} after ablation · "
                                       f"{'refused' if q['refused'] else 'complied'}" for q in sub]))
        return tr

    start = 28 if L > 28 else L - 1
    fig = go.Figure(data=traces(start),
                    frames=[go.Frame(data=traces(l), name=str(l)) for l in layers])
    fig.update_layout(
        title=f"{model}: concept plane (filled = refused, hollow = complied; basis: {out['basis']})",
        xaxis_title="projection on harm direction", yaxis_title="projection on refusal direction (⊥ harm)",
        height=680, legend=dict(itemsizing="constant"),
        sliders=[dict(active=layers.index(start), currentvalue=dict(prefix="layer "),
                      steps=[dict(label=str(l), method="animate",
                                  args=[[str(l)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                             for l in layers])])
    d = ROOT / "figures" / "interactive"
    d.mkdir(parents=True, exist_ok=True)
    fig.write_html(d / f"concept_plane_{model}.html", include_plotlyjs="cdn")
    print("wrote", d / f"concept_plane_{model}.html", "| points:", len(pts))
    return fig


if __name__ == "__main__":
    main()
