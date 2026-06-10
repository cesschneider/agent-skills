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

## "Claude brand" theme (cream / navy / terracotta)

For a light, editorial Claude-branded look (sunburst logo, serif title,
"Skills-Diagnosis"-style section rules, line-art icon grids), set:

  "background": "#F3ECE2", "blueprint_grid": false,
  "corner_brackets": false, "page_dots": false, "letterbox": true,
  "colors": {"navy": "#1F2D4D", "terracotta": "#C96A4A",
             "charcoal": "#1A1A1A"},
  "fonts": {..., "serif_bold": "Lora-Bold.ttf", "serif": "Lora-Regular.ttf"}

and use these additional element types:

  {"type": "logo_header", "text": "Claude"}
  {"type": "title", "align": "center", "size": 62, "lines": [
      [{"text": "McKinsey-Style ", "color": "navy"},
       {"text": "Skills", "color": "charcoal"}],
      [{"text": "for Opus 4.8", "color": "charcoal"}]
  ]}
  {"type": "section_header", "text": "Skills-Diagnosis"}
  {"type": "icon_grid", "columns": 5, "items": [
      {"icon": "pin", "label": "Situation\nAssessment"}, ...
  ]}

Available icon names: pin, binoculars, map, doc_alert, bars_blocked,
clipboard, people_chat, image_frame, dashboard, shield, circle (fallback).
"""

import json
import math
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
    "serif_bold": "DejaVuSerif-Bold.ttf",
    "serif": "DejaVuSerif.ttf",
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


# ---------------------------------------------------------------------------
# "Claude brand" theme helpers: sunburst logo + line-art icon set
# ---------------------------------------------------------------------------

def draw_sunburst(d, center, r_outer, r_inner, color, n=8, width=None):
    cx, cy = center
    width = width or max(2, int(r_outer * 0.18))
    for i in range(n):
        angle = math.pi * 2 * i / n
        x0 = cx + r_inner * math.cos(angle)
        y0 = cy + r_inner * math.sin(angle)
        x1 = cx + r_outer * math.cos(angle)
        y1 = cy + r_outer * math.sin(angle)
        d.line([(x0, y0), (x1, y1)], fill=color, width=width)
        rr = width / 2
        d.ellipse([x1 - rr, y1 - rr, x1 + rr, y1 + rr], fill=color)
        d.ellipse([x0 - rr, y0 - rr, x0 + rr, y0 + rr], fill=color)


def icon_pin(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    cx = x0 + w / 2
    r = w * 0.26
    cy = y0 + h * 0.32
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=navy, width=lw)
    pt = (cx, y0 + h * 0.74)
    d.line([(cx - r * 0.78, cy + r * 0.55), pt], fill=navy, width=lw, joint="curve")
    d.line([(cx + r * 0.78, cy + r * 0.55), pt], fill=navy, width=lw, joint="curve")
    ir = r * 0.4
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=terracotta)
    gy = y0 + h * 0.9
    d.line([(x0 + w * 0.16, gy), (x1 - w * 0.16, gy)], fill=navy, width=lw)


def icon_binoculars(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    r = w * 0.22
    cy = y0 + h * 0.5
    cx1, cx2 = x0 + w * 0.32, x0 + w * 0.68
    for cx in (cx1, cx2):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=navy, width=lw)
        ir = r * 0.45
        d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], outline=terracotta, width=max(2, int(lw * 0.7)))
    d.line([(cx1 + r * 0.55, cy - r * 0.75), (cx2 - r * 0.55, cy - r * 0.75)], fill=navy, width=lw)
    d.line([(cx1, cy - r), (cx1, y0 + h * 0.12)], fill=navy, width=lw)
    d.line([(cx2, cy - r), (cx2, y0 + h * 0.12)], fill=navy, width=lw)


def icon_map(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    pad = w * 0.08
    rx0, ry0, rx1, ry1 = x0 + pad, y0 + h * 0.2, x1 - pad, y1 - h * 0.12
    seg = (rx1 - rx0) / 3
    zig = h * 0.05
    top_pts = [(rx0, ry0 + zig), (rx0 + seg, ry0 - zig), (rx0 + 2 * seg, ry0 + zig), (rx1, ry0 - zig)]
    bot_pts = [(rx0, ry1 - zig), (rx0 + seg, ry1 + zig), (rx0 + 2 * seg, ry1 - zig), (rx1, ry1 + zig)]
    d.line(top_pts, fill=navy, width=lw, joint="curve")
    d.line(bot_pts, fill=navy, width=lw, joint="curve")
    d.line([top_pts[0], bot_pts[0]], fill=navy, width=lw)
    d.line([top_pts[-1], bot_pts[-1]], fill=navy, width=lw)
    d.line([(rx0 + seg, top_pts[1][1]), (rx0 + seg, bot_pts[1][1])], fill=terracotta, width=lw)
    d.line([(rx0 + 2 * seg, top_pts[2][1]), (rx0 + 2 * seg, bot_pts[2][1])], fill=terracotta, width=lw)


def icon_doc_alert(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    dx0, dy0, dx1, dy1 = x0 + w * 0.12, y0 + h * 0.06, x0 + w * 0.66, y1 - h * 0.06
    fold = w * 0.16
    d.line([(dx0, dy0), (dx1 - fold, dy0), (dx1, dy0 + fold), (dx1, dy1), (dx0, dy1), (dx0, dy0)],
           fill=navy, width=lw, joint="curve")
    d.line([(dx1 - fold, dy0), (dx1 - fold, dy0 + fold), (dx1, dy0 + fold)], fill=navy, width=max(2, int(lw * 0.8)))
    r = w * 0.2
    mcx, mcy = x1 - w * 0.26, y1 - h * 0.28
    d.ellipse([mcx - r, mcy - r, mcx + r, mcy + r], outline=terracotta, width=lw)
    d.line([(mcx + r * 0.7, mcy + r * 0.7), (mcx + r * 1.5, mcy + r * 1.5)], fill=terracotta, width=lw)
    d.line([(mcx, mcy - r * 0.45), (mcx, mcy + r * 0.05)], fill=terracotta, width=max(2, int(lw * 0.8)))
    d.ellipse([mcx - 2, mcy + r * 0.3 - 2, mcx + 2, mcy + r * 0.3 + 2], fill=terracotta)


def icon_bars_blocked(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    base = y1 - h * 0.12
    bw = w * 0.12
    heights = [0.32, 0.5, 0.7, 0.42]
    gap = w * 0.06
    start = x0 + w * 0.08
    for i, hh in enumerate(heights):
        bx0 = start + i * (bw + gap)
        by0 = base - h * hh
        d.rectangle([bx0, by0, bx0 + bw, base], outline=navy, width=lw)
    r = w * 0.14
    cx, cy = x1 - w * 0.16, y0 + h * 0.18
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=terracotta, width=lw)
    d.line([(cx - r * 0.6, cy - r * 0.6), (cx + r * 0.6, cy + r * 0.6)], fill=terracotta, width=max(2, int(lw * 0.8)))
    d.line([(cx - r * 0.6, cy + r * 0.6), (cx + r * 0.6, cy - r * 0.6)], fill=terracotta, width=max(2, int(lw * 0.8)))


def icon_clipboard(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    bx0, by0, bx1, by1 = x0 + w * 0.16, y0 + h * 0.1, x1 - w * 0.16, y1 - h * 0.04
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=w * 0.05, outline=navy, width=lw)
    cw = w * 0.28
    d.rounded_rectangle([(bx0 + bx1) / 2 - cw / 2, by0 - h * 0.05, (bx0 + bx1) / 2 + cw / 2, by0 + h * 0.06],
                         radius=w * 0.02, outline=navy, width=lw)
    for frac in (0.34, 0.52, 0.7):
        ly = by0 + (by1 - by0) * frac
        sq = w * 0.05
        d.rectangle([bx0 + w * 0.06, ly - sq / 2, bx0 + w * 0.06 + sq, ly + sq / 2],
                     outline=navy, width=max(2, int(lw * 0.7)))
        d.line([(bx0 + w * 0.16, ly), (bx1 - w * 0.06, ly)], fill=navy, width=max(2, int(lw * 0.6)))
    r = w * 0.13
    cx, cy = bx1 - r * 0.5, by1 - r * 0.5
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=terracotta)


def icon_people_chat(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.045))
    bx0, by0, bx1, by1 = x0 + w * 0.1, y0 + h * 0.05, x1 - w * 0.1, y0 + h * 0.45
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=w * 0.06, outline=terracotta, width=lw)
    d.line([(bx0 + w * 0.15, by1), (bx0 + w * 0.1, by1 + h * 0.08), (bx0 + w * 0.25, by1)],
           fill=terracotta, width=max(2, int(lw * 0.7)), joint="curve")
    for frac in (0.4, 0.62):
        ly = by0 + (by1 - by0) * frac
        d.line([(bx0 + w * 0.12, ly), (bx1 - w * 0.12, ly)], fill=terracotta, width=max(2, int(lw * 0.6)))
    r = w * 0.11
    for cx in (x0 + w * 0.34, x0 + w * 0.66):
        cy = y1 - h * 0.34
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=navy, width=lw)
        bw = r * 2.6
        d.arc([cx - bw / 2, cy + r * 0.5, cx + bw / 2, cy + r * 0.5 + bw], start=180, end=360, fill=navy, width=lw)


def icon_image_frame(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    fx0, fy0, fx1, fy1 = x0 + w * 0.1, y0 + h * 0.1, x1 - w * 0.1, y1 - h * 0.1
    d.rectangle([fx0, fy0, fx1, fy1], outline=terracotta, width=lw)
    r = w * 0.08
    d.ellipse([fx0 + w * 0.12, fy0 + h * 0.12, fx0 + w * 0.12 + 2 * r, fy0 + h * 0.12 + 2 * r], outline=navy, width=lw)
    d.line([(fx0 + w * 0.05, fy1 - h * 0.06), (fx0 + w * 0.35, fy0 + h * 0.45),
            (fx0 + w * 0.55, fy1 - h * 0.18), (fx0 + w * 0.7, fy0 + h * 0.55),
            (fx1 - w * 0.05, fy1 - h * 0.06)], fill=navy, width=lw, joint="curve")


def icon_dashboard(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    fx0, fy0, fx1, fy1 = x0 + w * 0.08, y0 + h * 0.08, x1 - w * 0.08, y1 - h * 0.08
    d.rounded_rectangle([fx0, fy0, fx1, fy1], radius=w * 0.04, outline=navy, width=lw)
    by = fy0 + h * 0.1
    for dxf in (0.16, 0.24, 0.32):
        cx = fx0 + w * dxf
        rr = w * 0.02
        d.ellipse([cx - rr, by - rr, cx + rr, by + rr], fill=navy)
    d.line([(fx0, fy0 + h * 0.18), (fx1, fy0 + h * 0.18)], fill=navy, width=max(2, int(lw * 0.6)))
    r = w * 0.16
    pcx, pcy = fx0 + w * 0.3, fy0 + h * 0.62
    d.ellipse([pcx - r, pcy - r, pcx + r, pcy + r], outline=terracotta, width=lw)
    d.pieslice([pcx - r, pcy - r, pcx + r, pcy + r], start=0, end=130, fill=terracotta)
    bw = w * 0.07
    base = fy1 - h * 0.1
    for i, hh in enumerate((0.16, 0.3, 0.22)):
        bx0 = fx0 + w * 0.56 + i * (bw + w * 0.04)
        d.rectangle([bx0, base - h * hh, bx0 + bw, base], fill=navy)


def icon_shield(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    lw = max(3, int(w * 0.05))
    cx = x0 + w / 2
    pts = [(cx, y0 + h * 0.06), (x1 - w * 0.1, y0 + h * 0.2), (x1 - w * 0.1, y0 + h * 0.55),
           (cx, y1 - h * 0.04), (x0 + w * 0.1, y0 + h * 0.55), (x0 + w * 0.1, y0 + h * 0.2)]
    d.line(pts + [pts[0]], fill=navy, width=lw, joint="curve")
    d.line([(cx - w * 0.16, y0 + h * 0.42), (cx - w * 0.03, y0 + h * 0.55), (cx + w * 0.18, y0 + h * 0.28)],
           fill=terracotta, width=lw, joint="curve")


def icon_circle(d, box, navy, terracotta):
    x0, y0, x1, y1 = box
    lw = max(3, int((x1 - x0) * 0.05))
    pad_x, pad_y = (x1 - x0) * 0.1, (y1 - y0) * 0.1
    d.ellipse([x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y], outline=navy, width=lw)


ICON_DRAWERS = {
    "pin": icon_pin,
    "binoculars": icon_binoculars,
    "map": icon_map,
    "doc_alert": icon_doc_alert,
    "bars_blocked": icon_bars_blocked,
    "clipboard": icon_clipboard,
    "people_chat": icon_people_chat,
    "image_frame": icon_image_frame,
    "dashboard": icon_dashboard,
    "shield": icon_shield,
    "circle": icon_circle,
}


def draw_icon(d, name, box, navy, terracotta):
    ICON_DRAWERS.get(name, icon_circle)(d, box, navy, terracotta)


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
    colors.setdefault("accent1", (139, 92, 246))
    colors.setdefault("accent2", (94, 234, 212))
    colors.setdefault("navy", colors["accent1"])
    colors.setdefault("terracotta", colors["accent2"])
    colors.setdefault("charcoal", colors["white"])

    font_dir = cfg.get("font_dir", FALLBACK_FONT_DIR)
    fonts_cfg = dict(cfg.get("fonts", {}))
    if not os.path.isdir(font_dir):
        font_dir = FALLBACK_FONT_DIR
        fonts_cfg = dict(FALLBACK_FONTS)
    fonts_cfg.setdefault("serif_bold", fonts_cfg.get("headline", FALLBACK_FONTS["headline"]))
    fonts_cfg.setdefault("serif", fonts_cfg.get("body", FALLBACK_FONTS["body"]))

    def font(role, size):
        return ImageFont.truetype(os.path.join(font_dir, fonts_cfg[role]), size)

    grid_step = cfg.get("grid_step", 54)
    letterbox_h = int(H * cfg.get("letterbox_height", 0.045)) if cfg.get("letterbox") else 0
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

        y = MARGIN + (letterbox_h if letterbox_h else 24)
        if slide.get("eyebrow"):
            f = font("mono_bold", 28)
            text = slide["eyebrow"].upper()
            color = colors.get("accent2", colors["white"])
            d.text((MARGIN, y), text, font=f, fill=color)
            tw = d.textlength(text, font=f)
            d.line([(MARGIN, y + 44), (MARGIN + tw, y + 44)], fill=color, width=2)
            y += 96

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
            elif kind == "logo_header":
                text = el["text"]
                f = font("serif_bold", el.get("size", 56))
                tw = d.textlength(text, font=f)
                logo_r = el.get("logo_radius", int(el.get("size", 56) * 0.5))
                gap = el.get("gap", 16)
                total_w = logo_r * 2 + gap + tw
                align = el.get("align", "center")
                start_x = (W - total_w) / 2 if align == "center" else MARGIN
                cy = y + logo_r
                draw_sunburst(d, (start_x + logo_r, cy), logo_r, logo_r * 0.32,
                               colors.get("terracotta"), n=el.get("spokes", 8))
                asc, desc = f.getmetrics()
                d.text((start_x + logo_r * 2 + gap, y + (logo_r * 2 - (asc + desc)) / 2),
                       text, font=f, fill=colors.get("charcoal"))
                y += logo_r * 2
            elif kind == "title":
                f = font("serif_bold", el.get("size", 64))
                align = el.get("align", "left")
                line_spacing = el.get("line_spacing", 1.2)
                asc, desc = f.getmetrics()
                line_h = int((asc + desc) * line_spacing)
                for line in el["lines"]:
                    total_w = sum(d.textlength(span["text"], font=f) for span in line)
                    x = MARGIN if align == "left" else (W - total_w) / 2
                    for span in line:
                        col = colors.get(span.get("color", "charcoal"), color)
                        d.text((x, y), span["text"], font=f, fill=col)
                        x += d.textlength(span["text"], font=f)
                    y += line_h
            elif kind == "section_header":
                f = font("serif", el.get("size", 36))
                text = el["text"]
                tw = d.textlength(text, font=f)
                col = colors.get(el.get("color", "terracotta"), color)
                cx = W / 2
                pad = el.get("pad", 24)
                asc, desc = f.getmetrics()
                text_h = asc + desc
                line_y = y + text_h / 2
                d.line([(MARGIN, line_y), (cx - tw / 2 - pad, line_y)], fill=col, width=2)
                d.line([(cx + tw / 2 + pad, line_y), (W - MARGIN, line_y)], fill=col, width=2)
                d.text((cx - tw / 2, y), text, font=f, fill=col)
                y += text_h
            elif kind == "icon_grid":
                items = el["items"]
                cols = el.get("columns", 5)
                cell_w = CONTENT_W / cols
                icon_size = el.get("icon_size", int(cell_w * 0.55))
                label_f = font("serif", el.get("label_size", 30))
                navy = colors.get("navy")
                terracotta = colors.get("terracotta")
                label_color = colors.get("charcoal")
                asc, desc = label_f.getmetrics()
                line_h = int((asc + desc) * 1.1)
                row_gap = el.get("row_gap", 36)
                rows = math.ceil(len(items) / cols)
                for i, item in enumerate(items):
                    row, col = divmod(i, cols)
                    cell_x0 = MARGIN + col * cell_w
                    cell_y0 = y + row * (icon_size + line_h * 2 + row_gap)
                    icon_x0 = cell_x0 + (cell_w - icon_size) / 2
                    box = (icon_x0, cell_y0, icon_x0 + icon_size, cell_y0 + icon_size)
                    draw_icon(d, item.get("icon", "circle"), box, navy, terracotta)
                    ly = cell_y0 + icon_size + 12
                    for ll in item.get("label", "").split("\n"):
                        tw = d.textlength(ll, font=label_f)
                        d.text((cell_x0 + (cell_w - tw) / 2, ly), ll, font=label_f, fill=label_color)
                        ly += line_h
                y += rows * (icon_size + line_h * 2 + row_gap)

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

        if letterbox_h:
            d.rectangle([0, 0, W, letterbox_h], fill=(0, 0, 0))
            d.rectangle([0, H - letterbox_h, W, H], fill=(0, 0, 0))

        path = os.path.join(out_dir, f"{idx + 1:02d}.png")
        img.save(path)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
