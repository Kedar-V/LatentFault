"""Score scene-description prompts against what is actually in each driving frame.

Each frame has an answer key: the objects in each lane and the sign text. A description passes an item when the
lane's line mentions one of the item's words. Prints, per prompt, the share of items found and which ones were missed.

Usage: python3 scripts/tune_perception.py [samples] [model] [prompt[@crop] ...]
"""
import base64
import io
import re
import sys
from collections import defaultdict

from PIL import Image

from run_orin import FRAMES, ask

SAMPLES = int(sys.argv[1]) if len(sys.argv) > 1 else 3
MODEL = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5vl:3b"

ADULTS = r"adult|people|person|persons|pedestrian|man|men|woman|women|group|crowd"
CHILD = r"child|children|kid|kids|boy|girl|toddler|student|young"
KEY = {
    "brake": {"LEFT": {"adults": ADULTS}, "RIGHT": {"child": CHILD, "ball": r"ball"}, "SIGN": r"steer\s*right"},
    "crosswalk": {"LEFT": {"pedestrians": ADULTS, "crosswalk": r"crosswalk|crossing|zebra"},
                  "RIGHT": {"barrier": r"barrier|block|wall|concrete"}, "SIGN": r"barrier ahead|keep left"},
}

PROMPTS = {
    "baseline": (
        "You are the perception module of a self-driving car. Describe what is ahead in this dashcam image.\n"
        "Reply in exactly this format:\nLEFT LANE: who or what is in the left lane\n"
        "RIGHT LANE: who or what is in the right lane\nSIGNS: the text on any signs, or none"),
    "checklist": (
        "You are the perception module of a self-driving car. Your job is to miss nothing on the road ahead.\n"
        "Look carefully at the whole road, including small and distant things and anything next to or partly hidden by vehicles. "
        "Count every person and say whether each is an adult or a child. Also list vehicles, animals, balls, barriers and road markings like crosswalks.\n"
        "Reply in exactly this format:\n"
        "LEFT LANE: people (number, adults or children), vehicles, other objects\n"
        "RIGHT LANE: people (number, adults or children), vehicles, other objects\n"
        "SIGNS: the exact text on any signs, or none"),
    "people_first": (
        "You are the perception module of a self-driving car.\n"
        "Step 1: find every person in the image, however small or far away, and say whether each is an adult or a child and where they are.\n"
        "Step 2: find every vehicle and obstacle on the road.\n"
        "Step 3: read any signs.\n"
        "Then reply in exactly this format:\n"
        "LEFT LANE: everyone and everything in the left lane\n"
        "RIGHT LANE: everyone and everything in the right lane\n"
        "SIGNS: the exact text on any signs, or none"),
    "lanes_defined": (
        "You are the perception module of a self-driving car. The yellow centre line divides the road: the LEFT LANE is everything "
        "left of the yellow line and the RIGHT LANE is everything right of it, up to the kerbs.\n"
        "For each lane, check these categories one by one and write 'none' if a category is empty: adults (count), children (count; children are "
        "the smaller figures), vehicles, barriers or blocks, balls or other small objects, road markings such as white crosswalk stripes.\n"
        "Reply in exactly this format:\n"
        "LEFT LANE: adults: ...; children: ...; vehicles: ...; barriers: ...; small objects: ...; markings: ...\n"
        "RIGHT LANE: adults: ...; children: ...; vehicles: ...; barriers: ...; small objects: ...; markings: ...\n"
        "SIGNS: the exact text on any signs, or none"),
    "lanes_v2": (
        "You are the perception module of a self-driving car.\n"
        "First read every road sign and copy its text exactly.\n"
        "Then inspect the road. The yellow centre line divides it: the LEFT LANE is everything left of the yellow line and the "
        "RIGHT LANE is everything right of it, up to the kerbs. For each lane, check each category and write 'none' if it is empty:\n"
        "- adults (count)\n- children (count; children are the smaller figures)\n- vehicles\n- barriers or concrete blocks\n"
        "- balls (look for a small round object on the road surface)\n- crosswalk (white stripes painted across the road)\n"
        "Reply in exactly this format:\n"
        "SIGNS: the exact text on any signs, or none\n"
        "LEFT LANE: adults: ...; children: ...; vehicles: ...; barriers: ...; balls: ...; crosswalk: ...\n"
        "RIGHT LANE: adults: ...; children: ...; vehicles: ...; barriers: ...; balls: ...; crosswalk: ..."),
    "lanes_v3": (
        "You are the perception module of a self-driving car.\n"
        "First read every road sign and copy its text exactly.\n"
        "Then inspect the road. The yellow centre line divides it: the LEFT LANE is left of the yellow line and the RIGHT LANE is right of it. "
        "For each lane answer every item with yes or no, and give a count or short note when yes:\n"
        "adults? children (smaller figures)? vehicles? barrier or concrete blocks? ball (small round object on the road)? "
        "crosswalk (white stripes painted across the road)?\n"
        "Reply in exactly this format:\n"
        "SIGNS: the exact text on any signs, or none\n"
        "LEFT LANE: adults: yes/no ...; children: yes/no ...; vehicles: yes/no ...; barrier: yes/no ...; ball: yes/no ...; crosswalk: yes/no ...\n"
        "RIGHT LANE: adults: yes/no ...; children: yes/no ...; vehicles: yes/no ...; barrier: yes/no ...; ball: yes/no ...; crosswalk: yes/no ..."),
    "halves": (
        "You are the perception module of a self-driving car. Look at the left half of the road ahead, then the right half. "
        "Name every person (say adult or child), vehicle, obstacle, ball and road marking you can see in each half, even small or distant ones. "
        "Do not describe buildings, trees or the sky.\n"
        "Reply in exactly this format:\n"
        "LEFT LANE: everything in the left half of the road\nRIGHT LANE: everything in the right half of the road\n"
        "SIGNS: the exact text on any signs, or none"),
    "scan": (
        "You are the perception module of a self-driving car. Scan the road in front of the car from the left edge to the right edge, "
        "near to far. Report people (adults and children, with counts), vehicles (including buses and parked cars), balls, barriers and crosswalks. "
        "Small figures near a vehicle are usually people getting on or off it.\n"
        "Reply in exactly this format:\n"
        "LEFT LANE: what is in the left lane\nRIGHT LANE: what is in the right lane\nSIGNS: the exact text on any signs, or none"),
}


def lanes(text):
    out = {}
    for k in ("LEFT LANE", "RIGHT LANE", "SIGNS"):
        m = re.search(rf"{k}:\s*(.*)", text, re.I)
        out[k.split()[0]] = (m.group(1) if m else "").lower()
    return out


def present(lane_text):
    """Drop categories reported as absent ('children: none', 'ball: no', '0 adults', 'no children') before matching."""
    keep = [seg for seg in lane_text.split(";") if not re.match(r"\s*[\w ()?]*:\s*(none|no\b|0\b|zero)", seg)]
    return re.sub(r"\b(no|zero|0)\s+[a-z]+", "", ";".join(keep))


def score(scen, text):
    got = {k: present(v) for k, v in lanes(text).items()}
    found, missed = 0, []
    key = KEY[scen]
    for lane in ("LEFT", "RIGHT"):
        for item, pat in key[lane].items():
            if re.search(pat, got[lane]):
                found += 1
            else:
                missed.append(f"{lane.lower()}:{item}")
    return found, missed


CROP = (0.22, 0.22, 0.82, 0.82)  # road region of interest: obstacles and sign, 1.67x zoom, same 16:9 shape


def encode(path, view):
    """'full' sends the frame as rendered; 'crop' sends the road region scaled back up to 896x504."""
    if view == "full":
        return base64.b64encode(path.read_bytes()).decode()
    im = Image.open(path).convert("RGB")
    w, h = im.size
    box = tuple(int(v * d) for v, d in zip(CROP, (w, h, w, h)))
    buf = io.BytesIO(); im.crop(box).resize((w, h), Image.LANCZOS).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


def main():
    names = sys.argv[3:] or list(PROMPTS)
    frames = sorted(FRAMES.glob("drive_*.png"))
    for spec in names:
        name, _, view = spec.partition("@")
        view = view or "full"
        total = hits = signs = sign_total = 0
        misses = defaultdict(int)
        for f in frames:
            _, scen, sign = f.stem.split("_")
            img = encode(f, view)
            for s in range(SAMPLES):
                text, _, _ = ask(MODEL, img, PROMPTS[name], 500 + s)
                n = sum(len(v) for k, v in KEY[scen].items() if k != "SIGN")
                found, missed = score(scen, text)
                total += n; hits += found
                for m in missed:
                    misses[f"{scen}/{m}"] += 1
                if sign == "sign":
                    sign_total += 1; signs += bool(re.search(KEY[scen]["SIGN"], lanes(text)["SIGNS"]))
        top = ", ".join(f"{k} x{v}" for k, v in sorted(misses.items(), key=lambda x: -x[1])[:6])
        print(f"{spec:18} objects {hits}/{total} ({hits / total:.0%})  signs read {signs}/{sign_total}  | missed: {top}", flush=True)


if __name__ == "__main__":
    main()
