"""
render_worked_example_assets.py

Purpose:
- Render assets/decision_summary.png from examples/worked_example.md (Decision + Risks)
- Render assets/calendar_starter.png from the 90-day calendar table

This avoids manual screenshots and keeps the README hero images reproducible.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_MD = REPO_ROOT / "examples" / "worked_example.md"
ASSETS_DIR = REPO_ROOT / "assets"

DECISION_OUT = ASSETS_DIR / "decision_summary.png"
CALENDAR_OUT = ASSETS_DIR / "calendar_starter.png"


def read_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    return fix_mojibake(raw)


def fix_mojibake(text: str) -> str:
    replacements = {
        "â€“": "–",
        "â€”": "—",
        "â†’": "→",
        "â€œ": "“",
        "â€": "”",
        "â€™": "’",
        "â€˜": "‘",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def extract_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.M | re.S)
    return match.group(1).strip() if match else ""


def strip_md(line: str) -> str:
    line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
    line = re.sub(r"`([^`]*)`", r"\1", line)
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip()


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = []
    if bold:
        font_candidates = [
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "C:\\Windows\\Fonts\\segoeuib.ttf",
        ]
    else:
        font_candidates = [
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
        ]
    for p in font_candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    words = text.split()
    lines: List[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        width = draw.textlength(test, font=font)
        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def parse_constraints(situation_text: str) -> List[str]:
    lines = situation_text.splitlines()
    constraints: List[str] = []
    capture = False
    for line in lines:
        if "Constraints / cooldowns" in line:
            capture = True
            continue
        if capture:
            if line.strip().startswith("-"):
                constraints.append(strip_md(line.strip().lstrip("- ").strip()))
            elif line.strip().startswith("##"):
                break
    return constraints


def parse_data_used(data_text: str) -> Tuple[List[str], List[str]]:
    public: List[str] = []
    steam: List[str] = []
    current = None
    for line in data_text.splitlines():
        line = line.strip()
        if line.startswith("**Public signals"):
            current = "public"
            continue
        if line.startswith("**Steamworks exports required"):
            current = "steam"
            continue
        if line.startswith("-"):
            item = strip_md(line.lstrip("- ").strip())
            if current == "public":
                public.append(item)
            elif current == "steam":
                steam.append(item)
    return public, steam


def render_decision_summary(decision_text: str, risks_text: str, situation_text: str, data_text: str) -> None:
    title_font = load_font(36, bold=True)
    header_font = load_font(26, bold=True)
    body_font = load_font(22, bold=False)

    lines = [ln.strip() for ln in decision_text.splitlines() if ln.strip()]
    goal_line = next((ln for ln in lines if ln.startswith("**Goal:**") or ln.startswith("Goal:")), "")
    bullets = [ln for ln in lines if ln.startswith("-")]
    bullets = [strip_md(ln.lstrip("- ").strip()) for ln in bullets]
    bullets = bullets[:3]  # keep core recommendation bullets

    risk_lines = [ln.strip() for ln in risks_text.splitlines() if ln.strip().startswith("-")]
    risk_pairs: List[str] = []
    for ln in risk_lines[:3]:
        clean = strip_md(ln.lstrip("- ").strip())
        clean = re.sub(r"Mitigation:\s*", "Mitigation: ", clean)
        risk_pairs.append(clean)

    width = 1400
    margin = 60
    line_gap = 8

    tmp_img = Image.new("RGB", (width, 1000), "white")
    draw = ImageDraw.Draw(tmp_img)

    content: List[Tuple[str, ImageFont.ImageFont]] = []
    content.append(("Decision Summary (Preview — redacted)", title_font))
    content.append(("", body_font))
    if goal_line:
        content.append((strip_md(goal_line), body_font))
    content.append(("", body_font))
    content.append(("Recommendation", header_font))
    for b in bullets:
        content.append((f"• {b}", body_font))
    content.append(("", body_font))
    content.append(("Why / constraints", header_font))
    constraints = parse_constraints(situation_text)[:3]
    for c in constraints:
        content.append((f"• {c}", body_font))
    content.append(("", body_font))
    content.append(("Risks + mitigations", header_font))
    for r in risk_pairs:
        content.append((f"• {r}", body_font))
    content.append(("", body_font))
    content.append(("Data needed", header_font))
    public, steam = parse_data_used(data_text)
    if public:
        content.append((f"• Public: {public[0]}", body_font))
    if steam:
        content.append((f"• Steamworks: {steam[0]}", body_font))

    wrapped_lines: List[Tuple[str, ImageFont.ImageFont]] = []
    for text_line, font in content:
        if text_line == "":
            wrapped_lines.append(("", font))
            continue
        for ln in wrap_text(draw, text_line, font, width - 2 * margin):
            wrapped_lines.append((ln, font))

    line_heights = []
    for ln, font in wrapped_lines:
        bbox = font.getbbox("Ag")
        line_heights.append((bbox[3] - bbox[1]) + line_gap)

    total_height = margin + sum(line_heights) + margin
    img = Image.new("RGB", (width, total_height), "white")
    draw = ImageDraw.Draw(img)

    y = margin
    for (ln, font), h in zip(wrapped_lines, line_heights):
        if ln:
            draw.text((margin, y), ln, fill="black", font=font)
        y += h

    img.save(DECISION_OUT)


def render_calendar_table(text: str) -> None:
    title_font = load_font(32, bold=True)
    header_font = load_font(22, bold=True)
    body_font = load_font(20, bold=False)

    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in lines]
    if len(rows) < 2:
        raise ValueError("Schedule table not found.")

    header = rows[0]
    data_rows = rows[2:] if rows[1][0].startswith("---") else rows[1:]

    col_widths = [240, 230, 200, 230, 520]
    table_width = sum(col_widths)
    margin = 60
    width = table_width + margin * 2

    tmp = Image.new("RGB", (width, 1000), "white")
    draw = ImageDraw.Draw(tmp)

    def cell_lines(text: str, font: ImageFont.ImageFont, max_w: int) -> List[str]:
        return wrap_text(draw, text, font, max_w - 12)

    header_lines = [cell_lines(h, header_font, w) for h, w in zip(header, col_widths)]
    header_height = max(len(ls) for ls in header_lines) * (header_font.getbbox("Ag")[3] - header_font.getbbox("Ag")[1] + 6)

    row_heights = []
    row_wrapped = []
    for row in data_rows:
        wrapped = [cell_lines(c, body_font, w) for c, w in zip(row, col_widths)]
        row_wrapped.append(wrapped)
        height = max(len(ls) for ls in wrapped) * (body_font.getbbox("Ag")[3] - body_font.getbbox("Ag")[1] + 6) + 6
        row_heights.append(height)

    title_height = title_font.getbbox("Ag")[3] - title_font.getbbox("Ag")[1]
    total_height = margin + title_height + 20 + header_height + sum(row_heights) + margin

    img = Image.new("RGB", (width, total_height), "white")
    draw = ImageDraw.Draw(img)

    y = margin
    draw.text((margin, y), "90-Day Promo Calendar (Starter — Preview, redacted)", font=title_font, fill="black")
    y += title_height + 20

    x = margin
    for idx, (lines, w) in enumerate(zip(header_lines, col_widths)):
        draw.rectangle([x, y, x + w, y + header_height], fill="#f0f2f5", outline="#d0d0d0")
        ty = y + 4
        for ln in lines:
            draw.text((x + 6, ty), ln, font=header_font, fill="black")
            ty += header_font.getbbox("Ag")[3] - header_font.getbbox("Ag")[1] + 6
        x += w
    y += header_height

    for row_idx, (wrapped, rh) in enumerate(zip(row_wrapped, row_heights)):
        x = margin
        fill = "#ffffff" if row_idx % 2 == 0 else "#fafafa"
        for lines, w in zip(wrapped, col_widths):
            draw.rectangle([x, y, x + w, y + rh], fill=fill, outline="#e0e0e0")
            ty = y + 4
            for ln in lines:
                draw.text((x + 6, ty), ln, font=body_font, fill="black")
                ty += body_font.getbbox("Ag")[3] - body_font.getbbox("Ag")[1] + 6
            x += w
        y += rh

    img.save(CALENDAR_OUT)


def main() -> None:
    text = read_text(SOURCE_MD)
    decision = extract_section(text, "Decision (Public Preview — redacted)")
    risks = extract_section(text, "Risks + mitigations")
    situation = extract_section(text, "Situation")
    data_used = extract_section(text, "Data used (public vs Steamworks-required)")
    schedule = extract_section(text, "Schedule (90-day promo calendar starter — redacted)")
    if not schedule:
        schedule = extract_section(text, "Schedule (90-day promo calendar starter)")

    if not decision:
        raise SystemExit("Decision section not found in worked_example.md")
    if not schedule:
        raise SystemExit("Schedule section not found in worked_example.md")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    render_decision_summary(decision, risks, situation, data_used)
    render_calendar_table(schedule)
    print(f"Rendered {DECISION_OUT.relative_to(REPO_ROOT)}")
    print(f"Rendered {CALENDAR_OUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
