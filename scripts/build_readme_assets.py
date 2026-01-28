"""
build_readme_assets.py

Purpose:
- Create /assets folder (if missing)
- Build assets/lift_decay.png as a vertical composite of:
    1) reports/figures/lift_curve_by_discount_tier.png (top)
    2) reports/figures/decay_by_discount_tier.png (bottom)
- Copy the source images into /assets as backups

Notes:
- Intentionally does NOT use lift_vs_discount_scatter.png (unit mismatch risk).
- decision_summary.png and calendar_starter.png are expected to be added manually (screenshots).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = REPO_ROOT / "reports" / "figures"
ASSETS_DIR = REPO_ROOT / "assets"

TOP_IMG = FIG_DIR / "lift_curve_by_discount_tier.png"
BOT_IMG = FIG_DIR / "decay_by_discount_tier.png"

OUT_COMPOSITE = ASSETS_DIR / "lift_decay.png"
OUT_TOP_COPY = ASSETS_DIR / "lift_curve_by_discount_tier.png"
OUT_BOT_COPY = ASSETS_DIR / "decay_by_discount_tier.png"


def _require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")


def _to_rgba(img: Image.Image) -> Image.Image:
    return img.convert("RGBA") if img.mode != "RGBA" else img


def _pad_to_width(img: Image.Image, width: int) -> Image.Image:
    """Pad image to target width with white background; center horizontally."""
    if img.width == width:
        return img
    padded = Image.new("RGBA", (width, img.height), (255, 255, 255, 255))
    x = (width - img.width) // 2
    padded.paste(img, (x, 0))
    return padded


def _stack_vertical(top: Image.Image, bottom: Image.Image) -> Image.Image:
    """Stack two images vertically on a white background with width padding."""
    width = max(top.width, bottom.width)
    top_padded = _pad_to_width(_to_rgba(top), width)
    bottom_padded = _pad_to_width(_to_rgba(bottom), width)

    out = Image.new(
        "RGBA", (width, top_padded.height + bottom_padded.height), (255, 255, 255, 255)
    )
    out.paste(top_padded, (0, 0))
    out.paste(bottom_padded, (0, top_padded.height))
    return out


def main() -> None:
    _require(TOP_IMG)
    _require(BOT_IMG)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(TOP_IMG, OUT_TOP_COPY)
    shutil.copy2(BOT_IMG, OUT_BOT_COPY)

    with Image.open(TOP_IMG) as top, Image.open(BOT_IMG) as bottom:
        composite = _stack_vertical(top, bottom)

    composite.convert("RGB").save(OUT_COMPOSITE, optimize=True)

    print("Built README assets:")
    print(f" - {OUT_COMPOSITE.relative_to(REPO_ROOT)}")
    print(f" - {OUT_TOP_COPY.relative_to(REPO_ROOT)}")
    print(f" - {OUT_BOT_COPY.relative_to(REPO_ROOT)}")
    print("Reminder: add assets/decision_summary.png and assets/calendar_starter.png manually.")


if __name__ == "__main__":
    main()
