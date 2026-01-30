"""
render_upwork_gallery.py

Purpose:
Generate Upwork preview assets (PRIVATE, gitignored) from public/redacted assets:
- decision summary
- 90-day calendar preview
- lift/decay preview

Outputs are written to: client_private/upwork_gallery/
This script never writes to /assets or /reports.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"
OUT_DIR = REPO_ROOT / "client_private" / "upwork_gallery"

INPUTS = {
    "decision": ASSETS_DIR / "decision_summary.png",
    "calendar": ASSETS_DIR / "calendar_starter.png",
    "lift_decay": ASSETS_DIR / "lift_decay.png",
}

TITLES = {
    "decision": "Decision Memo Preview (Redacted)",
    "calendar": "90-Day Calendar Preview (Redacted)",
    "lift_decay": "Lift/Decay Preview",
}


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates = ["C:\\Windows\\Fonts\\arialbd.ttf", "C:\\Windows\\Fonts\\segoeuib.ttf"]
    else:
        candidates = ["C:\\Windows\\Fonts\\arial.ttf", "C:\\Windows\\Fonts\\segoeui.ttf"]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def add_title_bar(img: Image.Image, title: str, width: int, bar_height: int = 64) -> Image.Image:
    out = Image.new("RGB", (width, img.height + bar_height), "white")
    draw = ImageDraw.Draw(out)
    draw.rectangle([0, 0, width, bar_height], fill="#f2f3f5")
    font = load_font(24, bold=True)
    text_w = draw.textlength(title, font=font)
    x = max(20, (width - text_w) // 2)
    y = (bar_height - font.getbbox("Ag")[3]) // 2
    draw.text((x, y), title, font=font, fill="black")
    out.paste(img, (0, bar_height))
    return out


def resize_to_width(img: Image.Image, width: int) -> Image.Image:
    w, h = img.size
    if w == width:
        return img
    new_h = int(h * (width / w))
    return img.resize((width, new_h), Image.Resampling.LANCZOS)


def render_one(key: str, width: int, add_title: bool) -> Path:
    src = INPUTS[key]
    if not src.exists():
        raise FileNotFoundError(f"Missing required input: {src}")
    img = Image.open(src).convert("RGB")
    img = resize_to_width(img, width)
    if add_title:
        img = add_title_bar(img, TITLES[key], width)
    out = OUT_DIR / f"upwork_{key}_preview.png"
    img.save(out, optimize=True)
    return out


def build_pdf(paths: list[Path], width: int) -> Path:
    images = [Image.open(p).convert("RGB") for p in paths]
    total_height = sum(img.height for img in images) + 40 * (len(images) - 1)
    canvas = Image.new("RGB", (width, total_height), "white")
    y = 0
    for img in images:
        canvas.paste(img, (0, y))
        y += img.height + 40
    out = OUT_DIR / "upwork_preview_pack.pdf"
    canvas.save(out, "PDF")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Upwork preview gallery (private).")
    parser.add_argument("--width", type=int, default=1200, help="Output width in pixels.")
    parser.add_argument("--no-title-bar", action="store_true", help="Disable title bar overlay.")
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF generation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = [
        render_one("decision", args.width, not args.no_title_bar),
        render_one("calendar", args.width, not args.no_title_bar),
        render_one("lift_decay", args.width, not args.no_title_bar),
    ]
    if not args.no_pdf:
        build_pdf(paths, args.width)
    print("Generated Upwork preview assets in client_private/upwork_gallery/")


if __name__ == "__main__":
    main()
