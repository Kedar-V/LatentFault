"""Extract final-prompt-token residual-stream activations and short greedy replies.

For every item and modality (text / image) this runs ONE greedy `generate` call with
`output_hidden_states=True`. The first step's hidden states are the prompt forward pass:
a tuple of (num_layers + 1) tensors [1, seq, d] (index 0 = embeddings). We keep position -1,
the last prompt token, which with `add_generation_prompt=True` is the end of the
"<|im_start|>assistant\\n" header: the position the model answers from.

The official chat template is used (it inserts Qwen's default system prompt). Image items
pass the rendered card through the processor; we record the number of image tokens so the
vision path is verifiably used.

Saves results/raw/<model>/<modality>/<id>.npz (hidden states, float32) + .json (reply,
timings, token counts). Existing files are skipped, so the run can be resumed.

Runs on CUDA in bfloat16 when available (pizer: 2x RTX 3080, the 7B is split across both),
otherwise on CPU in float32 (the Orin fallback). Hidden states are saved as float32 either way.

Usage: python src/extract.py --model <HF id or local folder> [--pairs N]
"""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

from prompts import DATA, IMAGE_INSTRUCTION, load_items

ROOT = Path(__file__).resolve().parent.parent


def build(processor, item, modality):
    if modality == "text":
        content = [{"type": "text", "text": item["goal"]}]
        images = None
    else:
        content = [{"type": "image"}, {"type": "text", "text": IMAGE_INSTRUCTION}]
        images = [Image.open(DATA / item["image"]).convert("RGB")]
    messages = [{"role": "user", "content": content}]
    prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return processor(text=[prompt], images=images, return_tensors="pt"), prompt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-VL-3B-Instruct")
    ap.add_argument("--pairs", type=int, default=None, help="only the first N pairs (smoke test)")
    ap.add_argument("--max-new-tokens", type=int, default=40)
    ap.add_argument("--threads", type=int, default=12)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    tag = args.model.rstrip("/").split("/")[-1]
    out = ROOT / "results" / "raw" / tag
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(args.model)
    if torch.cuda.is_available():
        # bf16 on GPU; device_map="auto" splits a model too big for one card (7B on 2x 10 GB)
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            args.model, dtype=torch.bfloat16, device_map="auto").eval()
    else:
        # float32 on CPU: the Orin's Cortex-A78AE cores have no fast bf16 path
        model = Qwen2_5_VLForConditionalGeneration.from_pretrained(args.model, dtype=torch.float32).eval()
    device = next(model.parameters()).device
    print(f"device {device}, dtype {next(model.parameters()).dtype}, "
          f"map {getattr(model, 'hf_device_map', None) and sorted(set(map(str, model.hf_device_map.values())))}",
          flush=True)
    image_token_id = model.config.image_token_id
    print(f"loaded {tag} in {time.time() - t0:.0f}s", flush=True)

    items = load_items()
    pairs = sorted({it["pair"] for it in items})[: args.pairs]
    # interleave so a partial run stays balanced: each pair's harmful+benign, text+image
    order = [it for p in pairs for it in items if it["pair"] == p]
    for it in order:
        for modality in ("text", "image"):
            dest = out / modality / it["id"]
            if dest.with_suffix(".json").exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            inputs, prompt = build(processor, it, modality)
            inputs = inputs.to(device)
            n_img = int((inputs["input_ids"] == image_token_id).sum())
            if modality == "image":
                assert n_img > 0 and "pixel_values" in inputs, "image did not reach the vision encoder"
            t = time.time()
            with torch.inference_mode():
                gen = model.generate(**inputs, max_new_tokens=args.max_new_tokens, do_sample=False,
                                     output_hidden_states=True, return_dict_in_generate=True)
            dt = time.time() - t
            first = gen.hidden_states[0]  # prompt pass: (layers+1) x [1, seq, d]
            h = torch.stack([layer[0, -1].float().cpu() for layer in first]).numpy()
            reply = processor.batch_decode(gen.sequences[:, inputs["input_ids"].shape[1]:],
                                           skip_special_tokens=True)[0].strip()
            np.savez_compressed(dest.with_suffix(".npz"), h=h)  # stored as float32 either way
            dest.with_suffix(".json").write_text(json.dumps({
                "id": it["id"], "pair": it["pair"], "kind": it["kind"], "modality": modality,
                "category": it["category"], "reply": reply, "seconds": round(dt, 2),
                "prompt_tokens": int(inputs["input_ids"].shape[1]), "image_tokens": n_img,
                "new_tokens": int(gen.sequences.shape[1] - inputs["input_ids"].shape[1]),
                "layers": int(h.shape[0]), "d_model": int(h.shape[1]),
            }))
            del gen, first, inputs
            print(f"{it['id']} {modality:5} {dt:6.1f}s prompt={h.shape} img_tok={n_img:3d} | "
                  f"{reply[:50].replace(chr(10), ' ')!r}", flush=True)


if __name__ == "__main__":
    main()
