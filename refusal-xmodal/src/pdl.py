"""Parallel ranged download of a Hugging Face model repo into a plain local folder.

Small files go through hf_hub_download; each *.safetensors file is fetched in N byte ranges
over separate HTTPS connections (resumable: finished ranges are kept as .partNN files).
Written because unauthenticated single-connection downloads ran at ~4 MB/s and the xet path hung.

Usage: env/bin/python src/pdl.py Qwen/Qwen2.5-VL-3B-Instruct models/Qwen2.5-VL-3B-Instruct [N]
"""
import os
import shutil
import sys
import threading
import time
import urllib.request
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_download

repo, dest, N = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 8
dest.mkdir(parents=True, exist_ok=True)
info = HfApi().model_info(repo, files_metadata=True)
files = [(s.rfilename, s.size) for s in info.siblings
         if s.rfilename.endswith((".json", ".safetensors", ".txt"))]

for name, size in files:
    if not name.endswith(".safetensors"):
        shutil.copy(hf_hub_download(repo, name), dest / name)
        print("small", name, flush=True)

done_bytes = [0]
lock = threading.Lock()


def fetch(url, start, end, part):
    have = part.stat().st_size if part.exists() else 0
    if have == end - start + 1:
        with lock:
            done_bytes[0] += have
        return
    for attempt in range(8):
        try:
            have = part.stat().st_size if part.exists() else 0
            req = urllib.request.Request(url, headers={"Range": f"bytes={start + have}-{end}"})
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "ab") as fh:
                while chunk := r.read(1 << 20):
                    fh.write(chunk)
                    with lock:
                        done_bytes[0] += len(chunk)
            if part.stat().st_size == end - start + 1:
                return
        except Exception as e:  # retry from where this range stopped
            print(f"retry {part.name}: {e}", flush=True)
            time.sleep(2 + attempt)
    raise RuntimeError(f"range failed: {part}")


big = [(n, s) for n, s in files if n.endswith(".safetensors")]
total = sum(s for _, s in big)
threads = []
for name, size in big:
    url = f"https://huggingface.co/{repo}/resolve/main/{name}"
    step = size // N + 1
    for k in range(N):
        a, b = k * step, min(size, (k + 1) * step) - 1
        if a > b:
            continue
        t = threading.Thread(target=fetch, args=(url, a, b, dest / f"{name}.part{k:02d}"))
        t.start()
        threads.append(t)

t0 = time.time()
while any(t.is_alive() for t in threads):
    time.sleep(10)
    print(f"{done_bytes[0] / 2**30:.2f} / {total / 2**30:.2f} GB  "
          f"{done_bytes[0] / 2**20 / (time.time() - t0):.1f} MB/s avg", flush=True)
for t in threads:
    t.join()

for name, size in big:
    out = dest / name
    with open(out, "wb") as fh:
        for k in range(N):
            p = dest / f"{name}.part{k:02d}"
            if p.exists():
                with open(p, "rb") as src:
                    shutil.copyfileobj(src, fh, 1 << 24)
                p.unlink()
    assert out.stat().st_size == size, f"{name}: {out.stat().st_size} != {size}"
    print("joined", name, size, flush=True)
print("WEIGHTS_DONE", dest, flush=True)
