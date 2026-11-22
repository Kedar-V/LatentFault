"""Activation Space Explorer (Streamlit + Plotly). Reads only cached, real results.

Needs, per model, results/raw/<model>/{text,image}/*.npz (hidden states),
results/<model>/{labels.json,metrics_by_layer.json,oof_scores.npz}. Nothing is synthesised:
a model whose files are missing is simply not offered.

Views (one model at a time; raw 3B and 7B coordinates are never placed in one space):
  1. 3D PCA of final-token activations at a chosen layer. PCA is fit on the TRAINING items of
     the chosen fold (text + image jointly); held-out items are projected into that space and
     drawn as open markers.
  2. Paired text vs image: 2D PCA with a segment joining each request's text and image point.
  3. Held-out AUROC heatmap (condition x layer) and text-to-image transfer curves.
  4. Held-out projection scores on the candidate refusal direction, by class and modality.
  5. Trajectories: a chosen request's held-out score at every layer (per-layer direction,
     centred on that layer's training threshold, so layers share one aligned scale).

Run:  streamlit run src/dashboard.py
Export static HTML for every view:  python src/dashboard.py --export
"""
import json
import sys
from pathlib import Path

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from prompts import load_items  # noqa: E402

COLORS = {"harmful": "#c2410c", "benign": "#1f4e9c"}


def models():
    return sorted(p.name for p in (ROOT / "results").iterdir()
                  if (p / "metrics_by_layer.json").exists() and (ROOT / "results" / "raw" / p.name).exists())


def load_model(model):
    raw = ROOT / "results" / "raw" / model
    labels = {(r["id"], r["modality"]): r for r in json.loads((ROOT / "results" / model / "labels.json").read_text())}
    items, H = [], {"text": [], "image": []}
    for it in load_items():
        paths = [raw / m / f"{it['id']}.npz" for m in ("text", "image")]
        if all(p.exists() for p in paths):
            items.append(it)
            for m, p in zip(("text", "image"), paths):
                H[m].append(np.load(p)["h"])
    H = {m: np.stack(v) for m, v in H.items()}
    metrics = json.loads((ROOT / "results" / model / "metrics_by_layer.json").read_text())
    oof = dict(np.load(ROOT / "results" / model / "oof_scores.npz", allow_pickle=True))
    y = np.array([it["harmful"] for it in items])
    groups = np.array([it["pair"] for it in items])
    folds = list(GroupKFold(n_splits=5).split(H["text"][:, 0], y, groups))
    return {"items": items, "H": H, "labels": labels, "metrics": metrics, "oof": oof, "y": y,
            "groups": groups, "folds": folds}


def frame(D, layer, fold, dims):
    tr, _ = D["folds"][fold]
    train = np.zeros(len(D["items"]), bool)
    train[tr] = True
    Xtr = np.concatenate([D["H"]["text"][train, layer], D["H"]["image"][train, layer]])
    pca = PCA(n_components=dims).fit(Xtr)
    rows = []
    for m in ("text", "image"):
        Z = pca.transform(D["H"][m][:, layer])
        for i, it in enumerate(D["items"]):
            lab = D["labels"][(it["id"], m)]["label"]
            rows.append({"id": it["id"], "pair": it["pair"], "kind": it["kind"], "modality": m,
                         "category": it["category"], "behavior": it["behavior"], "observed": lab,
                         "split": "train" if train[i] else "held-out",
                         **{f"PC{k + 1}": Z[i, k] for k in range(dims)}})
    return rows, pca.explained_variance_ratio_


def fig_pca3d(D, model, layer, fold, color_by):
    rows, ev = frame(D, layer, fold, 3)
    fig = go.Figure()
    for split, sym_suffix in (("train", ""), ("held-out", "-open")):
        for m, sym in (("text", "circle"), ("image", "diamond")):
            sub = [r for r in rows if r["split"] == split and r["modality"] == m]
            if not sub:
                continue
            col = [COLORS[r["kind"]] if color_by == "request" else
                   {"REFUSED": "#7c3aed", "COMPLIED": "#0f766e", "AMBIGUOUS": "#9ca3af"}[r["observed"]] for r in sub]
            fig.add_trace(go.Scatter3d(
                x=[r["PC1"] for r in sub], y=[r["PC2"] for r in sub], z=[r["PC3"] for r in sub],
                mode="markers", name=f"{m} · {split}",
                marker=dict(size=4, color=col, symbol=sym + sym_suffix if sym == "circle" else sym,
                            opacity=0.9 if split == "train" else 0.55),
                text=[f"{r['id']} · {r['kind']} · {r['modality']}<br>{r['category']}: {r['behavior']}"
                      f"<br>observed: {r['observed']} · {r['split']}" for r in sub],
                hoverinfo="text"))
    fig.update_layout(title=f"{model} · layer {layer} · PCA fit on fold-{fold} training items "
                            f"(var {ev[:3].sum():.0%})", height=640, legend=dict(itemsizing="constant"))
    return fig


def fig_pairs(D, model, layer, fold):
    rows, ev = frame(D, layer, fold, 2)
    byid = {}
    for r in rows:
        byid.setdefault(r["id"], {})[r["modality"]] = r
    fig = go.Figure()
    for kind in ("benign", "harmful"):
        xs, ys = [], []
        for rid, d in byid.items():
            if d["text"]["kind"] == kind:
                xs += [d["text"]["PC1"], d["image"]["PC1"], None]
                ys += [d["text"]["PC2"], d["image"]["PC2"], None]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=COLORS[kind], width=0.6),
                                 opacity=0.35, name=f"{kind}: text↔image", hoverinfo="skip"))
        for m, sym in (("text", "circle"), ("image", "diamond")):
            sub = [r for r in rows if r["kind"] == kind and r["modality"] == m]
            fig.add_trace(go.Scatter(x=[r["PC1"] for r in sub], y=[r["PC2"] for r in sub], mode="markers",
                                     marker=dict(color=COLORS[kind], symbol=sym, size=7), name=f"{kind} · {m}",
                                     text=[f"{r['id']} {r['category']}: {r['behavior']} · {r['observed']}"
                                           for r in sub], hoverinfo="text"))
    fig.update_layout(title=f"{model} · layer {layer} · paired text (●) vs image (◆), 2D PCA "
                            f"(var {ev.sum():.0%})", height=560)
    return fig


def fig_heatmap(D, model):
    keys = [("text_auc", "text → text"), ("image_auc", "image → image"), ("transfer_auc", "text dir → image"),
            ("text_refusal_auc", "text: observed refusal"), ("image_refusal_auc", "image: observed refusal")]
    z = [[r[k] for r in D["metrics"]] for k, _ in keys]
    fig = px.imshow(z, y=[n for _, n in keys], x=[r["layer"] for r in D["metrics"]], zmin=0.5, zmax=1.0,
                    color_continuous_scale="Viridis", aspect="auto",
                    labels=dict(x="layer", color="held-out AUROC"))
    fig.update_layout(title=f"{model}: held-out AUROC by layer", height=330)
    return fig


def fig_transfer(all_models):
    """Curves on relative depth so models with different layer counts share an x axis.
    Only scalar metrics are overlaid; no raw activations are compared across models."""
    fig = go.Figure()
    for model, D in all_models.items():
        L = len(D["metrics"])
        x = [r["layer"] / (L - 1) for r in D["metrics"]]
        for k, dash in (("text_auc", "dot"), ("transfer_auc", "solid"), ("transfer_null95", "dash")):
            fig.add_trace(go.Scatter(x=x, y=[r[k] for r in D["metrics"]], name=f"{model}: {k}",
                                     line=dict(dash=dash)))
    fig.update_layout(title="Text-to-image transfer (held-out) vs relative depth", height=440,
                      xaxis_title="layer / (num layers − 1)", yaxis_title="AUROC", yaxis_range=[0.4, 1.02])
    return fig


def fig_projection(D, model, layer):
    oof, y = D["oof"], D["y"]
    fig = go.Figure()
    for name in ("text", "image", "transfer"):
        for k, kind in ((0, "benign"), (1, "harmful")):
            fig.add_trace(go.Violin(y=oof[name][layer][y == k], x=[name] * int((y == k).sum()), name=kind,
                                    legendgroup=kind, showlegend=name == "text", side="negative" if k == 0 else "positive",
                                    line_color=COLORS[kind], points=False, meanline_visible=True))
    fig.update_layout(violinmode="overlay", height=460,
                      title=f"{model} · layer {layer}: held-out projection − train threshold")
    fig.add_hline(y=0, line_width=1)
    return fig


def fig_trajectories(D, model, ids):
    oof = D["oof"]
    idx = {i: k for k, i in enumerate(oof["ids"])}
    fig = go.Figure()
    L = oof["text"].shape[0]
    for rid in ids:
        k = idx[rid]
        kind = "harmful" if rid.startswith("h") else "benign"
        for name, dash in (("text", "solid"), ("image", "dot")):
            fig.add_trace(go.Scatter(x=list(range(L)), y=oof[name][:, k], name=f"{rid} · {name}",
                                     line=dict(color=COLORS[kind], dash=dash)))
    fig.add_hline(y=0, line_width=1)
    fig.update_layout(title=f"{model}: held-out score by layer (aligned per-layer refusal coordinate)",
                      xaxis_title="layer", yaxis_title="projection − train threshold", height=460)
    return fig


def export():
    out = ROOT / "figures" / "interactive"
    out.mkdir(parents=True, exist_ok=True)
    allD = {m: load_model(m) for m in models()}
    for m, D in allD.items():
        best = json.loads((ROOT / "results" / m / "summary.json").read_text())["selected_layer_by_text_heldout"]
        fig_pca3d(D, m, best, 0, "request").write_html(out / f"pca3d_{m}.html", include_plotlyjs="cdn")
        fig_pairs(D, m, best, 0).write_html(out / f"pairs_{m}.html", include_plotlyjs="cdn")
        fig_heatmap(D, m).write_html(out / f"heatmap_{m}.html", include_plotlyjs="cdn")
        fig_projection(D, m, best).write_html(out / f"projection_{m}.html", include_plotlyjs="cdn")
        fig_trajectories(D, m, ["h001", "b001", "h010", "b010"]).write_html(out / f"trajectories_{m}.html",
                                                                          include_plotlyjs="cdn")
    if allD:
        fig_transfer(allD).write_html(out / "transfer_all.html", include_plotlyjs="cdn")
    print("wrote", sorted(p.name for p in out.iterdir()))


def app():
    import streamlit as st
    st.set_page_config(page_title="Activation Space Explorer", layout="wide")
    st.title("Activation Space Explorer · Qwen2.5-VL refusal directions")
    avail = models()
    if not avail:
        st.warning("No cached results yet. Run extract.py and analyze.py first.")
        return
    model = st.sidebar.selectbox("model", avail)
    D = st.cache_resource(load_model)(model)
    L = len(D["metrics"])
    best = json.loads((ROOT / "results" / model / "summary.json").read_text())["selected_layer_by_text_heldout"]
    layer = st.sidebar.slider("layer", 0, L - 1, best)
    fold = st.sidebar.selectbox("PCA fit on training items of fold", range(5))
    color_by = st.sidebar.radio("colour", ["request", "observed refusal"])
    st.caption(f"{len(D['items'])} requests × 2 modalities · selected layer (by text held-out AUROC) = {best} · "
               "all points are real cached hidden states")
    t1, t2, t3, t4, t5 = st.tabs(["3D PCA", "text ↔ image pairs", "AUROC by layer", "projections", "trajectories"])
    with t1:
        st.plotly_chart(fig_pca3d(D, model, layer, fold, color_by), use_container_width=True)
    with t2:
        st.plotly_chart(fig_pairs(D, model, layer, fold), use_container_width=True)
    with t3:
        st.plotly_chart(fig_heatmap(D, model), use_container_width=True)
        st.plotly_chart(fig_transfer({m: load_model(m) for m in avail}), use_container_width=True)
    with t4:
        st.plotly_chart(fig_projection(D, model, layer), use_container_width=True)
    with t5:
        ids = st.multiselect("requests", [it["id"] for it in D["items"]], default=["h001", "b001"])
        if ids:
            st.plotly_chart(fig_trajectories(D, model, ids), use_container_width=True)


if __name__ == "__main__":
    if "--export" in sys.argv:
        export()
    else:
        app()
