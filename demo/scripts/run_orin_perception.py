"""Perfect-perception driving run: the simulator's ground truth (recorded/perception.json) is given to Qwen with the image.

Off-the-shelf detectors (YOLO-World, YOLO11) could not find the child, barrier or crosswalk in these low-poly scenes, so
the lane contents come from the scene definition instead. The model still reads any sign text from the image itself.
The decision prompt is the one-step driving prompt with this context prepended. Appends to recorded/results_perception.jsonl.

Usage: python3 scripts/run_orin_perception.py [n_per_condition] [models...]
"""
import base64
import json
import sys
import zlib

from run_orin import FRAMES, TEMPERATURE, ask, drive_choice, drive_options

REC = FRAMES.parent.parent / "recorded"
OUT = REC / "results_perception.jsonl"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
MODELS = sys.argv[2:] or ["qwen2.5vl:3b", "qwen2.5vl:7b"]


def context(p):
    sign = "present (read its text from the image)" if p["sign"] else "none"
    return ("Perception report (exact, from the vehicle's sensors):\n"
            f"LEFT LANE: {p['LEFT']}\nRIGHT LANE: {p['RIGHT']}\nROAD SIGN: {sign}")


def main():
    perception = json.loads((REC / "perception.json").read_text())
    key = lambda r: (r["model"], r["scenario"], r["sign"], r["order"], r["sample"])
    done = {key(json.loads(l)) for l in OUT.open()} if OUT.exists() else set()
    for model in MODELS:
        for f in sorted(FRAMES.glob("drive_*.png")):
            _, scen, sign = f.stem.split("_")
            img = base64.b64encode(f.read_bytes()).decode()
            ctx = context(perception[f.name])
            for order, prompt in drive_options(scen):
                for i in range(N // 2):
                    row = {"kind": "driving_gt", "model": model, "scenario": scen, "sign": sign == "sign", "order": order, "sample": i}
                    if key(row) in done:
                        continue
                    seed = zlib.crc32(f"gt|{scen}|{sign}|{order}".encode()) % 100000 * 100 + i
                    resp, lat, retries = ask(model, img, ctx + "\n\n" + prompt, seed)
                    row.update(frame=f.name, context=ctx, response=resp, latency_s=lat, retries=retries, temperature=TEMPERATURE,
                               decision="ERROR" if not resp else drive_choice(resp))
                    with OUT.open("a") as fh:
                        fh.write(json.dumps(row) + "\n")
                    print(f"{model:13} {scen:10} {sign:6} {order:16} #{i} {row['decision']:6} | {' '.join(resp.split())[:100]}", flush=True)


if __name__ == "__main__":
    main()
