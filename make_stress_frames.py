"""Digital stress test: how small / blurry can each phone screen get before it stops fooling the camera?

Pastes each screen (with a phone bezel) into the no-phone photo at decreasing sizes, clean and
degraded (blur + heavy JPEG), so plain vs terminal styling can be compared where the attack is hard.
No hand is drawn holding the phone; this is a legibility stress test, not a realism test.
"""
import io
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

HERE = Path(__file__).parent
OUT = HERE / "frames_stress"
OUT.mkdir(exist_ok=True)
SCREENS = {
    "9": HERE / "phone_screens_v3/9_chatml_system.png",
    "10": HERE / "phone_screens_v3/10_chatml_prefill.png",
    "10t": HERE / "phone_screens_v3/10t_chatml_prefill_terminal.png",
    "11": HERE / "phone_screens_v3/11_qwen_identity.png",
}
SIZES = [0.40, 0.28, 0.20, 0.14]  # phone height as a fraction of frame height (round-2 photos were ~0.40)

# the no-phone photo, un-mirrored, at the round-2 photo size
base = ImageOps.mirror(Image.open(HERE / "frames/0_none_raw_mirrored.jpg").convert("RGB")).resize((2000, 1333))


def phone(screen_path, h):
    w = int(h * 1170 / 2532)
    sc = Image.open(screen_path).convert("RGB").resize((w, h), Image.LANCZOS)
    if sc.getpixel((w // 2, 5))[0] > 128:  # light screens get the blue tint seen in the real photos
        sc = ImageChops.multiply(sc, Image.new("RGB", sc.size, (190, 222, 245)))
    b = max(6, h // 40)
    body = Image.new("RGB", (w + 2 * b, h + 2 * b), (120, 135, 125))  # green-grey case like yours
    body.paste(sc, (b, b))
    mask = Image.new("L", body.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, body.width - 1, body.height - 1], b * 4, fill=255)
    return body.rotate(-4, expand=True, resample=Image.BICUBIC), mask.rotate(-4, expand=True)


def degrade(im):
    im = im.filter(ImageFilter.GaussianBlur(1.6))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=35)
    return Image.open(buf).convert("RGB")


for key, path in SCREENS.items():
    for s in SIZES:
        ph, m = phone(path, int(1333 * s))
        im = base.copy()
        cx, cy = 640, 560  # where you held the phone: left of the face, shoulder height
        im.paste(ph, (cx - ph.width // 2, cy - ph.height // 2), m)
        im = im.resize((1008, 672))
        im.save(OUT / f"{key}_s{int(s * 100)}_clean.jpg", quality=92)
        degrade(im).save(OUT / f"{key}_s{int(s * 100)}_degraded.jpg", quality=92)
print(len(list(OUT.glob("*.jpg"))), "frames")
