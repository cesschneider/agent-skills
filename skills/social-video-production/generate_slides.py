#!/usr/bin/env python3
"""
Generic slide-deck image generator for the social-video-production skill.

Renders a JSON slide spec to a series of PNGs — used for both the
Instagram carousel (1080x1350) and key-topic scene images (1920x1080).

Usage:
    python3 generate_slides.py <config.json> <output_dir>

Config schema (see skills/social-video-production/SKILL.md for the
full walkthrough and an example config):

{
  "width": 1080, "height": 1350, "margin": 72,
  "background": "#0f0f1a", "grid_color": "#181828",
  "colors": {"white": "#f5f5f7", "muted": "#9499a8",
             "accent1": "#8b5cf6", "accent2": "#5eead4"},
  "font_dir": "/mnt/skills/examples/canvas-design/canvas-fonts",
  "fonts": {"headline": "BricolageGrotesque-Bold.ttf",
            "body": "Outfit-Regular.ttf", "body_bold": "Outfit-Bold.ttf",
            "mono": "GeistMono-Regular.ttf", "mono_bold": "GeistMono-Bold.ttf"},
  "blueprint_grid": true, "corner_brackets": true, "page_dots": true,
  "grid_step": 54,
  "slides": [
    {
      "eyebrow": "01 — THE SHIFT",
      "elements": [
        {"type": "headline", "text": "17M", "size": 220, "color": "accent2"},
        {"type": "body", "text": "Supporting line.", "size": 40,
         "bold": true, "color": "white", "gap_before": 60}
      ],
      "footer": "FOOTER TAG"
    }
  ]
}

Element types: "headline" (uses the headline font), "body" (uses body
or body_bold font), "divider" (horizontal rule). Every element accepts
"gap_before" (px, default 0) inserted before it is drawn.
"""

import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont

FALLBACK_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FALLBACK_FONTS = {
    "headline": "DejaVuSans-Bold.ttf",
    "body": "DejaVuSans.ttf",
    "body_bold": "DejaVuSans-Bold.ttf",
    "mono": "DejaVuSansMono.ttf",
    "mono_bold": "DejaVuSansMono-Bold.ttf",
}


def hex_to_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def wrap_text(d, text, fnt, max_width):
    words = text.split(" ")
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textlength(test, font=fnt) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_multiline(d, xy, text, fnt, fill, max_width, line_spacing=1.3):
    x, y = xy
    asc, desc = fnt.getmetrics()
    line_h = int((asc + desc) * line_spacing)
    for para in text.split("\n"):
        if para == "":
            y += line_h
            continue
        for line in wrap_text(d, para, fnt, max_width):
            d.text((x, y), line, font=fnt, fill=fill)
            y += line_h
    return y


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: generate_slides.py <config.json> <output_dir>")

    config_path, out_dir = sys.argv[1], sys.argv[2]
    with open(config_path) as f:
        cfg = json.load(f)

    os.makedirs(out_dir, exist_ok=True)

    W, H = cfg.get("width", 1080), cfg.get("height", 1350)
    MARGIN = cfg.get("margin", 72)
    CONTENT_W = W - 2 * MARGIN
    BG = hex_to_rgb(cfg.get("background", "#0f0f1a"))
    GRID = hex_to_rgb(cfg.get("grid_color", "#181828"))
    colors = {k: hex_to_rgb(v) for k, v in cfg.get("colors", {}).items()}
    colors.setdefault("white", (245, 245, 247))
    colors.setdefault("muted", (148, 153, 168))

    font_dir = cfg.get("font_dir", FALLBACK_FONT_DIR)
    fonts_cfg = cfg.get("fonts", {})
    if not os.path.isdir(font_dir):
        font_dir = FALLBACK_FONT_DIR
        fonts_cfg = FALLBACK_FONTS

    def font(role, size):
        return ImageFont.truetype(os.path.join(font_dir, fonts_cfg[role]), size)

    grid_step = cfg.get("grid_step", 54)
    slides = cfg["slides"]
    total = len(slides)

    for idx, slide in enumerate(slides):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)

        if cfg.get("blueprint_grid", True):
            for x in range(0, W, grid_step):
                d.line([(x, 0), (x, H)], fill=GRID, width=1)
            for y in range(0, H, grid_step):
                d.line([(0, y), (W, y)], fill=GRID, width=1)

        if cfg.get("corner_brackets", True):
            L, inset = 46, 48
            accent = colors.get("accent1", colors["white"])
            for p in [
                ((inset, inset + L), (inset, inset), (inset + L, inset)),
                ((W - inset - L, inset), (W - inset, inset), (W - inset, inset + L)),
                ((inset, H - inset - L), (inset, H - inset), (inset + L, H - inset)),
                ((W - inset - L, H - inset), (W - inset, H - inset), (W - inset, H - inset - L)),
            ]:
                d.line(p, fill=accent, width=4, joint="curve")

        y = MARGIN + 24
        if slide.get("eyebrow"):
            f = font("mono_bold", 28)
            text = slide["eyebrow"].upper()
            color = colors.get("accent2", colors["white"])
            d.text((MARGIN, y), text, font=f, fill=color)
            tw = d.textlength(text, font=f)
            d.line([(MARGIN, y + 44), (MARGIN + tw, y + 44)], fill=color, width=2)
        y += 120

        for el in slide.get("elements", []):
            y += el.get("gap_before", 0)
            kind = el["type"]
            color = colors.get(el.get("color", "white"), colors["white"])
            if kind == "headline":
                f = font("headline", el.get("size", 80))
                y = draw_multiline(d, (MARGIN, y), el["text"], f, color, CONTENT_W,
                                    line_spacing=el.get("line_spacing", 1.15))
            elif kind == "body":
                role = "body_bold" if el.get("bold") else "body"
                f = font(role, el.get("size", 38))
                y = draw_multiline(d, (MARGIN, y), el["text"], f, color, CONTENT_W,
                                    line_spacing=el.get("line_spacing", 1.35))
            elif kind == "divider":
                d.line([(MARGIN, y), (W - MARGIN, y)], fill=GRID, width=2)
                y += 2

        if slide.get("footer"):
            d.text((MARGIN, H - 130), slide["footer"], font=font("mono", 22), fill=colors["muted"])

        if cfg.get("page_dots", True) and total > 1:
            r, gap = 6, 22
            start_x = (W - (total - 1) * gap) / 2
            cy = H - 64
            for i in range(total):
                cx = start_x + i * gap
                if i == idx:
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colors.get("accent2", colors["white"]))
                else:
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colors["muted"], width=2)

        path = os.path.join(out_dir, f"{idx + 1:02d}.png")
        img.save(path)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
