"""Collect the numbers the poster plots into src/data/poster_data.json.

Sources (read-only):
  ../refusal-xmodal/results/Qwen2.5-VL-3B-Instruct/summary.json, metrics_by_layer.json
  data_snapshots/interventions_summary.json   (copy of results/<model>/interventions_summary.json from the GPU server)
  data_snapshots/ghostprompt_projection.json  (rows built from the Orin projection run: camera.json, driving.json, jbb_reference.json)
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RES = HERE.parent / "refusal-xmodal" / "results" / "Qwen2.5-VL-3B-Instruct"
summ = json.loads((RES / "summary.json").read_text())
layers = json.loads((RES / "metrics_by_layer.json").read_text())
iv = {r["condition"] + "|" + r["modality"]: r for r in
      json.loads((HERE / "data_snapshots" / "interventions_summary.json").read_text())}
proj = json.loads((HERE / "data_snapshots" / "ghostprompt_projection.json").read_text())["rows"]


def cond(name, mod):
    r = iv[f"{name}|{mod}"]
    return {"before": r["refusal_before"], "after": r["refusal_after"], "ci": r["ci_after"], "n": r["n"],
            "p": r["mcnemar_p"]}


out = {
    "summary": {"layer": summ["selected_layer_by_text_heldout"], **{k: round(v, 3) for k, v in summ["at_selected_layer"].items()},
                "ci95": summ["ci95_at_selected"], "refusal_rate": summ["refusal_rate"],
                "n_items": summ["n_items"], "d_model": summ["d_model"]},
    "layers": [{"layer": m["layer"], "text": m["text_auc"], "image": m["image_auc"], "transfer": m["transfer_auc"],
                "null95": m["transfer_null95"], "cos": m["cosine_text_image"], "cos_null": m["cosine_null"]} for m in layers],
    "ablate": {mod: {"harm": cond("ablate-harmtext-late-harmful", mod),
                     "refusal_orth": cond("ablate-refusalorth-late-harmful", mod),
                     "random": [cond(f"ablate-{r}-late-harmful", mod) for r in ("random", "random1", "random2", "random3")]}
               for mod in ("text", "image")},
    "add": {mod: {"harm": cond("add-harmtext-L20-s2-benign", mod), "random": cond("add-random-L20-s2-benign", mod)}
            for mod in ("text", "image")},
    "projection": proj,
}
# Held-out transfer scores: image inputs scored on the text-learned direction, every layer.
# Standardized per layer (divide by that layer's std across the 200 requests) so the growing
# residual-stream norm does not exaggerate the split in deeper layers.
import struct, zipfile
zz = zipfile.ZipFile(RES / "oof_scores.npz")
def npy(n):
    b = zz.read(n); hl = struct.unpack("<H", b[8:10])[0]; d = b[10 + hl:]
    f = "d" if "f8" in b[10:10 + hl].decode() else "q"
    return list(struct.unpack("<%d%s" % (len(d) // 8, f), d))
yv = npy("y.npy"); tr = npy("transfer.npy"); n = len(yv)
cols = []
for L in range(len(tr) // n):
    row = tr[L * n:(L + 1) * n]; mu = sum(row) / n
    sd = (sum((v - mu) ** 2 for v in row) / n) ** 0.5
    cols.append([round((v - mu) / sd, 2) if sd > 1e-9 else 0.0 for v in row])
out["dahua"] = [{"image": r["image"], "decision": r["decision"], "harm_proj": r["harm_proj"]}
                for r in json.loads((HERE / "data_snapshots" / "dahua_camera.json").read_text())]
out["fan"] = {"harmful": yv, "scores": [[cols[L][i] for L in range(len(cols))] for i in range(n)]}

(HERE / "src" / "data" / "poster_data.json").write_text(json.dumps(out, indent=1))
print("wrote poster_data.json:", len(out["layers"]), "layers,", len(proj), "projection rows")
for mod in ("text", "image"):
    a = out["ablate"][mod]
    print(mod, "ablate", a["harm"]["before"], "->", a["harm"]["after"], "| orth ->", a["refusal_orth"]["after"],
          "| random ->", [r["after"] for r in a["random"]], "| add", out["add"][mod]["harm"]["before"], "->",
          out["add"][mod]["harm"]["after"], "random ->", out["add"][mod]["random"]["after"])
