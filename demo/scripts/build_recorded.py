"""Summarize recorded/results.jsonl and recorded/results_perception.jsonl into src/recorded.json for the demo.

Per model and scenario: counts of each decision and every usable answer, which the demo replays.
An answer is [decision, full response] or, for perfect-perception driving, [decision, full response, perception report].
Failed or unparseable answers (ERROR, NONE, UNCLEAR) are counted but not replayed.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_ID = {"qwen2.5vl:3b": "3b", "qwen2.5vl:7b": "7b"}

out = {"driving": defaultdict(dict), "driving_gt": defaultdict(dict), "camera": defaultdict(dict)}
for name in ("results.jsonl", "results_perception.jsonl"):
    path = ROOT / "recorded" / name
    if not path.exists():
        continue
    for line in path.open():
        r = json.loads(line)
        if not (ROOT / "public" / "frames" / r["frame"]).exists():
            continue  # scenario no longer in the demo
        m = MODEL_ID[r["model"]]
        key = ("sign" if r["sign"] else "none") if r["kind"] != "camera" else "all"
        cell = out[r["kind"]][r["scenario"]].setdefault(m, {}).setdefault(key, {"counts": {}, "answers": []})
        cell["counts"][r["decision"]] = cell["counts"].get(r["decision"], 0) + 1
        if r["decision"] in ("LEFT", "RIGHT", "BRAKE", "ALERT", "NO ALERT"):
            ans = [r["decision"], r["response"].strip()[:400]]
            if r["kind"] == "driving_gt":
                ans.append(r["context"])
            cell["answers"].append(ans)

(ROOT / "src" / "recorded.json").write_text(json.dumps(out, indent=1))
for kind, scen in out.items():
    for s, models in scen.items():
        for m, conds in models.items():
            for c, v in conds.items():
                print(f"{kind:8} {s:10} {m} {c:4} {v['counts']}")
