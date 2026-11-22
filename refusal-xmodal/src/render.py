"""Render each request as typed text on a plain card (FigStep-style typographic image).

672x336 px: Qwen2.5-VL merges 28x28 patches into one visual token, so each card is
24x12 = 288 image tokens. Black sans-serif text on white, wrapped, no other content,
so the only difference from the text condition is the modality the words arrive through.

Usage: python3 src/render.py   (writes data/images/*.png and data/items.json)
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from prompts import DATA, load_items

W, H, MARGIN = 672, 336, 28
FONTS = ["/System/Library/Fonts/Supplemental/Arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(size):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    raise FileNotFoundError("no TrueType font found; edit FONTS in render.py")


def wrap(draw, text, f, width):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=f) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def render(text, path):
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    size = 30
    while True:  # largest size at which the wrapped text fits
        f = font(size)
        lines = wrap(d, text, f, W - 2 * MARGIN)
        lh = int(size * 1.3)
        if len(lines) * lh <= H - 2 * MARGIN or size <= 14:
            break
        size -= 1
    y = (H - len(lines) * lh) // 2
    for ln in lines:
        d.text((MARGIN, y), ln, font=f, fill="black")
        y += lh
    img.save(path)
    return size


if __name__ == "__main__":
    items = load_items()
    (DATA / "images").mkdir(exist_ok=True)
    sizes = [render(it["goal"], DATA / it["image"]) for it in items]
    (DATA / "items.json").write_text(json.dumps(items, indent=1))
    print(f"{len(items)} images, font size {min(sizes)}-{max(sizes)} px")
