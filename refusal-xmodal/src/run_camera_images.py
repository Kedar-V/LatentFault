"""Run arbitrary images through the GhostPrompt security-camera prompt and read the harm direction.

Same prompt, decoding (greedy, 60 new tokens) and decision parser as ghostprompt_projection.py; the
harm projection uses the precomputed directions (export_directions.py) and is the mean over hidden
layers 19-36, comparable to the poster's camera rows.

Usage: python src/run_camera_images.py --model models/Qwen2.5-VL-3B-Instruct \
         --directions results/Qwen2.5-VL-3B-Instruct/ghostprompt_directions.npz --out results/dahua_camera.json img1 img2 ...
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

from ghostprompt_projection import CAMERA, decision


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--directions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("images", nargs="+")
    args = ap.parse_args()
    torch.set_num_threads(int(os.environ.get("THREADS", "12")))
    z = np.load(args.directions)
    H = torch.tensor(z["harm"], dtype=torch.float32)
    proc = AutoProcessor.from_pretrained(args.model)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(args.model, dtype=torch.float32).eval()
    rows = []
    for path in args.images:
        img = Image.open(path).convert("RGB")
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": CAMERA}]}]
        text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = proc(text=[text], images=[img], return_tensors="pt")
        with torch.inference_mode():
            gen = model.generate(**inputs, max_new_tokens=60, do_sample=False,
                                 output_hidden_states=True, return_dict_in_generate=True)
        h = torch.stack([layer[0, -1] for layer in gen.hidden_states[0]]).float()
        reply = proc.batch_decode(gen.sequences[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0].strip()
        harm = float((h[19:37] * H[19:37]).sum(-1).mean())
        row = {"image": Path(path).name, "decision": decision("camera", reply), "harm_proj": round(harm, 2),
               "reply": reply}
        rows.append(row)
        print(json.dumps(row), flush=True)
    Path(args.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
