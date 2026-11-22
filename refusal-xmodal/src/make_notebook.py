"""Write notebooks/explore_refusal_directions.ipynb (run on the machine that holds results/).

Usage: python src/make_notebook.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parent.parent
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

cells = [
    md("""# Refusal-direction explorer: Qwen2.5-VL, text vs rendered-image requests

Everything here is read in place from `results/` on this server: real cached hidden states,
real replies, real labels. Nothing is synthesised.

**Data.** JailbreakBench JBB-Behaviors: 100 harmful + 100 topic-matched benign requests
(row `Index` = pair). Each request is given to the model twice: as **text**, and as **image**
(the same words typed on a 672×336 card, 288 image tokens, plus a fixed instruction).

**Activations.** Residual stream at the last prompt token (end of the assistant header), every
layer (index 0 = embeddings). **Direction** per layer = mean(harmful) − mean(benign), fit on
training folds only (5 folds grouped by pair). **Scores** = projection − training threshold.

**Kernel:** `refusal-xmodal (Python 3.11)`. To look at the 7B, change `MODEL` below.
Correlation only: a separating direction does not show that it causes refusal."""),
    code("""import sys, json, math
from pathlib import Path
import numpy as np, pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

def find_root():
    # Cursor/VS Code may run from the workspace root, Jupyter from notebooks/: search both ways
    start = Path(globals().get("__vsc_ipynb_file__", Path.cwd())).resolve()
    for p in [start, *start.parents]:
        for c in (p, p / "refusal-xmodal"):
            if (c / "src" / "dashboard.py").exists():
                return c
    raise FileNotFoundError("could not find the refusal-xmodal folder; set ROOT = Path('...') by hand")

ROOT = find_root()
sys.path.insert(0, str(ROOT / "src"))
print("project folder:", ROOT)
import dashboard as dash   # plotting helpers shared with the Streamlit app

MODEL = "Qwen2.5-VL-3B-Instruct"   # or "Qwen2.5-VL-7B-Instruct" once its analysis has run
RES = ROOT / "results" / MODEL
summary = json.loads((RES / "summary.json").read_text())
D = dash.load_model(MODEL)
LAYER = summary["selected_layer_by_text_heldout"]   # chosen on TEXT held-out AUROC only
FOLD = 0
print(f"{MODEL}: {summary['n_items']} requests ({summary['n_pairs']} pairs), "
      f"{summary['layers']} layers, d={summary['d_model']}, selected layer {LAYER}")"""),
    md("## 1. Behaviour: refusal rates and a paired text-vs-image test"),
    code("""lab = pd.DataFrame(json.loads((RES / "labels.json").read_text()))
rates = lab.pivot_table(index="kind", columns="modality", values="refused", aggfunc="mean").round(3)
display(rates)

# Paired exact McNemar on harmful requests: does the same request get refused as text but not as image?
h = lab[lab.kind == "harmful"].pivot(index="id", columns="modality", values="refused")
b_ = int(((h.text == 1) & (h.image == 0)).sum())   # refused as text, complied as image
c_ = int(((h.text == 0) & (h.image == 1)).sum())   # complied as text, refused as image
n = b_ + c_
p = min(1.0, 2 * sum(math.comb(n, k) for k in range(0, min(b_, c_) + 1)) / 2 ** n) if n else 1.0
print(f"harmful requests: refused-as-text-only = {b_}, refused-as-image-only = {c_}, exact McNemar p = {p:.3g}")
print("manual label decisions:", (RES / "review_decisions.csv").exists() and
      pd.read_csv(RES / "review_decisions.csv")[["id", "modality", "label", "note"]].to_dict("records"))"""),
    md("## 2. Separation by layer (held-out vs training, with shuffled-label null)"),
    code("""M = pd.DataFrame(D["metrics"])
cols = ["layer", "text_auc", "image_auc", "transfer_auc", "text_null95", "transfer_null95",
        "cosine_text_image", "text_refusal_auc", "image_refusal_auc", "transfer_bal_acc"]
display(M[cols].round(3).style.background_gradient(subset=["text_auc", "image_auc", "transfer_auc"], cmap="viridis"))"""),
    code("""fig = go.Figure()
for name, c in (("text", "#1f4e9c"), ("image", "#c2410c"), ("transfer", "#7c3aed")):
    fig.add_scatter(x=M.layer, y=M[f"{name}_auc"], name=f"{name}: held-out", line=dict(color=c, width=3))
    fig.add_scatter(x=M.layer, y=M[f"{name}_auc_train"], name=f"{name}: train", line=dict(color=c, dash="dot", width=1))
fig.add_scatter(x=M.layer, y=M.transfer_null95, name="transfer null 95th pct", line=dict(color="grey", dash="dash"))
fig.add_vline(x=LAYER, line_dash="dot")
fig.update_layout(title=f"{MODEL}: harmful-vs-benign AUROC by layer", yaxis_range=[0.4, 1.02],
                  xaxis_title="layer", yaxis_title="AUROC", height=480)
fig"""),
    code("dash.fig_heatmap(D, MODEL)"),
    code("""fig = go.Figure()
fig.add_scatter(x=M.layer, y=M.cosine_text_image, name="cos(text dir, image dir)", line=dict(width=3))
fig.add_scatter(x=M.layer, y=M.cosine_null, name="shuffled-label null", line=dict(color="grey"))
fig.update_layout(title=f"{MODEL}: are text- and image-derived directions the same?", yaxis_range=[-0.2, 1],
                  xaxis_title="layer", yaxis_title="cosine", height=400)
fig"""),
    md("## 3. Held-out projection scores at the selected layer"),
    code("dash.fig_projection(D, MODEL, LAYER)"),
    code("""ci = summary["ci95_at_selected"]
pd.DataFrame({k: {"held-out AUROC": summary["at_selected_layer"][f"{k}_auc"], "95% CI": ci[k],
                  "null 95th": summary["at_selected_layer"][f"{k}_null95"],
                  "balanced acc": summary["at_selected_layer"][f"{k}_bal_acc"],
                  "Cohen d": round(summary["at_selected_layer"][f"{k}_d"], 2)}
              for k in ("text", "image", "transfer")}).T"""),
    md("""## 4. Activation space

PCA is fit on the **training items of `FOLD`** (text + image together); held-out items are projected
into that space. Change `LAYER` to watch text and image clouds merge around the middle of the network."""),
    code("dash.fig_pca3d(D, MODEL, LAYER, FOLD, 'request')"),
    code("dash.fig_pca3d(D, MODEL, LAYER, FOLD, 'observed refusal')"),
    code("""# Same request as text (●) and image (◆), joined by a line. Try an early layer vs a late one.
for l in (8, LAYER):
    dash.fig_pairs(D, MODEL, l, FOLD).show()"""),
    md("## 5. Trajectories through the layers (aligned per-layer refusal coordinate)"),
    code("""IDS = ["h001", "b001", "h036", "b036"]   # pick any ids from data/items.json
dash.fig_trajectories(D, MODEL, IDS)"""),
    md("## 6. Where text and image disagree"),
    code("""items = pd.DataFrame(json.loads((ROOT / "data" / "items.json").read_text()))[["id", "kind", "category", "behavior"]]
w = lab.pivot(index="id", columns="modality", values="label").reset_index().merge(items, on="id")
dis = w[w.text != w.image].sort_values(["kind", "category"])
print(f"{len(dis)} requests labelled differently as text vs image")
dis[["id", "kind", "category", "behavior", "text", "image"]]"""),
    code("""# Held-out transfer score by category (text direction applied to image inputs, selected layer)
oof = D["oof"]
sc = pd.DataFrame({"id": oof["ids"], "transfer_score": oof["transfer"][LAYER]}).merge(items, on="id")
sc.groupby(["category", "kind"]).transfer_score.mean().unstack().round(2)"""),
    md("""## 7. Causal test: removing the harm direction

Each request is rerun with one direction projected out of the residual stream at every position,
in a chosen window of decoder layers (held-out: the direction comes from the fold that excludes
the request). `harmtext` is the harm direction learned from text only; `random` is a same-size control.
Replies are capped at 40 tokens; for harmful requests only the label and opening are stored.
"0% refused" means no refusal language, not that every reply carried out the harmful task."""),
    code("""S = pd.DataFrame(json.loads((RES / "interventions_summary.json").read_text()))
S[["condition", "modality", "n", "refusal_before", "refusal_after", "ci_after",
   "refused_before_only", "refused_after_only", "mcnemar_p", "distinct_ratio_before", "distinct_ratio_after"]]"""),
    code("""from IPython.display import Image as _Img
display(_Img(filename=str(ROOT / "figures" / f"fig6_ablation_{MODEL}.png")))      # remove: necessary
display(_Img(filename=str(ROOT / "figures" / f"fig7_addition_{MODEL}.png")))      # add: sufficient (strength-response)
display(_Img(filename=str(ROOT / "figures" / f"fig8_random_range_{MODEL}.png")))  # specificity vs random + refusal direction"""),
    md("""## 8. Concept plane, with intervention arrows

x = harm direction, y = refusal direction (benign refused minus benign complied, made orthogonal to x),
both fit on fold-0 training items and fixed. Filled = refused, hollow = complied. Purple arrows join a
harmful request's baseline point to its point with the harm direction removed. Use the layer slider:
in layers 19+ the late-ablation arrows collapse to x = 0; watch whether y collapses too."""),
    code("""import concept_plane as cp
_cp = json.loads((RES / "concept_plane.json").read_text())
cp.figure(MODEL, _cp, ["ablate-harmtext-late-harmful", "ablate-harmtext-early-harmful"])"""),
    md("""## Notes
* Selected layer chosen on text held-out AUROC only, so image and transfer numbers there are not tuned on themselves.
* Labels: phrase rubric in `src/label.py` + manual decisions in `review_decisions.csv`; replies capped at 40 tokens.
* Raw 3B and 7B activations are different spaces (d = 2048 vs 3584): compare their **metrics**, not their coordinates."""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"name": "refusal-xmodal", "display_name": "refusal-xmodal (Python 3.11)", "language": "python"}})
out = ROOT / "notebooks" / "explore_refusal_directions.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print("wrote", out)
