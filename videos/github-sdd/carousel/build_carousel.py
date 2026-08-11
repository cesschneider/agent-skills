#!/usr/bin/env python3
"""Generate a 10-slide Instagram carousel for the GitHub SDD breakdown video."""

import os
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/mnt/skills/examples/canvas-design/canvas-fonts"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

W, H = 1080, 1350
MARGIN = 72

BG = (15, 15, 26)          # #0f0f1a
GRID = (24, 24, 40)        # subtle blueprint grid
WHITE = (245, 245, 247)
MUTED = (148, 153, 168)
VIOLET = (139, 92, 246)    # #8B5CF6
CYAN = (94, 234, 212)      # #5EEAD4

def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

F_HEADLINE = lambda s: font("BricolageGrotesque-Bold.ttf", s)
F_BODY     = lambda s: font("Outfit-Regular.ttf", s)
F_BODY_B   = lambda s: font("Outfit-Bold.ttf", s)
F_MONO     = lambda s: font("GeistMono-Regular.ttf", s)
F_MONO_B   = lambda s: font("GeistMono-Bold.ttf", s)


def base_canvas():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # blueprint grid
    step = 54
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=GRID, width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=GRID, width=1)
    # corner brackets (CAD viewfinder marks)
    L = 46
    inset = 48
    color = VIOLET
    pts = [
        ((inset, inset + L), (inset, inset), (inset + L, inset)),
        ((W - inset - L, inset), (W - inset, inset), (W - inset, inset + L)),
        ((inset, H - inset - L), (inset, H - inset), (inset + L, H - inset)),
        ((W - inset - L, H - inset), (W - inset, H - inset), (W - inset, H - inset - L)),
    ]
    for p in pts:
        d.line(p, fill=color, width=4, joint="curve")
    return img, d


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


def draw_multiline(d, xy, text, fnt, fill, max_width, line_spacing=1.25, align="left"):
    x, y = xy
    paragraphs = text.split("\n")
    asc, desc = fnt.getmetrics()
    line_h = int((asc + desc) * line_spacing)
    for para in paragraphs:
        if para == "":
            y += line_h
            continue
        for line in wrap_text(d, para, fnt, max_width):
            if align == "center":
                lw = d.textlength(line, font=fnt)
                d.text((x + (max_width - lw) / 2, y), line, font=fnt, fill=fill)
            else:
                d.text((x, y), line, font=fnt, fill=fill)
            y += line_h
    return y


def eyebrow(d, text, color=CYAN):
    f = F_MONO_B(28)
    d.text((MARGIN, 96), text.upper(), font=f, fill=color)
    # tick mark
    tw = d.textlength(text.upper(), font=f)
    d.line([(MARGIN, 96 + 44), (MARGIN + tw, 96 + 44)], fill=color, width=2)


def page_dots(d, idx, total=10):
    r = 6
    gap = 22
    total_w = (total - 1) * gap
    start_x = (W - total_w) / 2
    y = H - 64
    for i in range(total):
        cx = start_x + i * gap
        if i == idx:
            d.ellipse([cx - r, y - r, cx + r, y + r], fill=CYAN)
        else:
            d.ellipse([cx - r, y - r, cx + r, y + r], outline=MUTED, width=2)


def footer_tag(d, text):
    f = F_MONO(22)
    d.text((MARGIN, H - 130), text, font=f, fill=MUTED)


CONTENT_W = W - 2 * MARGIN


# ---------------------------------------------------------------- Slide 1
def slide_01():
    img, d = base_canvas()
    eyebrow(d, "AI-Assisted Development")
    y = 240
    d.text((MARGIN, y), "SPEC-DRIVEN", font=F_HEADLINE(98), fill=WHITE)
    y += 118
    d.text((MARGIN, y), "DEVELOPMENT", font=F_HEADLINE(98), fill=VIOLET)
    y += 150
    draw_multiline(
        d, (MARGIN, y),
        "The skill that separates developers thriving with AI from those drowning in it.",
        F_BODY(38), MUTED, CONTENT_W, line_spacing=1.35,
    )
    footer_tag(d, "GITHUB INTERVIEW BREAKDOWN  ·  SWIPE →")
    page_dots(d, 0)
    return img


# ---------------------------------------------------------------- Slide 2
def slide_02():
    img, d = base_canvas()
    eyebrow(d, "01 — The Shift")
    d.text((MARGIN, 360), "17M", font=F_HEADLINE(220), fill=CYAN)
    y = 640
    draw_multiline(
        d, (MARGIN, y),
        "AI-generated pull requests on GitHub in a single month.",
        F_BODY_B(46), WHITE, CONTENT_W, line_spacing=1.3,
    )
    y += 200
    draw_multiline(
        d, (MARGIN, y),
        "GitHub expected 5% growth in AI-written code.\nThey got 3x.",
        F_BODY(38), MUTED, CONTENT_W, line_spacing=1.4,
    )
    footer_tag(d, "DEC 2025 — THE MONTH AGENTS STOPPED GUESSING")
    page_dots(d, 1)
    return img


# ---------------------------------------------------------------- Slide 3
def slide_03():
    img, d = base_canvas()
    eyebrow(d, "02 — Two Modes")
    y = 230
    d.text((MARGIN, y), "MICRO-", font=F_HEADLINE(92), fill=WHITE)
    y += 110
    d.text((MARGIN, y), "DELEGATION", font=F_HEADLINE(92), fill=VIOLET)
    y += 110
    d.text((MARGIN, y), "& STEERING", font=F_HEADLINE(92), fill=WHITE)
    y += 170

    box_y = y
    d.rectangle([MARGIN, box_y, W - MARGIN, box_y + 230], outline=GRID, width=2)
    d.text((MARGIN + 32, box_y + 28), "DELEGATION", font=F_MONO_B(28), fill=CYAN)
    draw_multiline(
        d, (MARGIN + 32, box_y + 76),
        "Hand off a clearly defined task and let the agent run it end to end.",
        F_BODY(34), WHITE, CONTENT_W - 64, line_spacing=1.3,
    )

    box_y += 270
    d.rectangle([MARGIN, box_y, W - MARGIN, box_y + 230], outline=GRID, width=2)
    d.text((MARGIN + 32, box_y + 28), "STEERING", font=F_MONO_B(28), fill=VIOLET)
    draw_multiline(
        d, (MARGIN + 32, box_y + 76),
        "Step in lightly, mid-flight, to nudge the direction — not rebuild from scratch.",
        F_BODY(34), WHITE, CONTENT_W - 64, line_spacing=1.3,
    )

    footer_tag(d, "MASTER BOTH — OR THE WORK FEELS CHAOTIC")
    page_dots(d, 2)
    return img


# ---------------------------------------------------------------- Slide 4
def slide_04():
    img, d = base_canvas()
    eyebrow(d, "03 — The Philosophy")
    y = 240
    d.text((MARGIN, y), "LOW FLOOR.", font=F_HEADLINE(98), fill=WHITE)
    y += 118
    d.text((MARGIN, y), "HIGH CEILING.", font=F_HEADLINE(98), fill=VIOLET)
    y += 170
    draw_multiline(
        d, (MARGIN, y),
        "Lower the floor — anyone can build software, no code required.\n\nRaise the ceiling — pros do things that were impossible before.",
        F_BODY(40), WHITE, CONTENT_W, line_spacing=1.4,
    )
    y = H - 320
    d.line([(MARGIN, y), (W - MARGIN, y)], fill=GRID, width=2)
    draw_multiline(
        d, (MARGIN, y + 36),
        "“Mozart wasn’t the only genius of his era — most just never had a piano.”",
        F_BODY(36), CYAN, CONTENT_W, line_spacing=1.35,
    )
    footer_tag(d, "THE PIANO IS IN FRONT OF YOU NOW")
    page_dots(d, 3)
    return img


# ---------------------------------------------------------------- Slide 5
def slide_05():
    img, d = base_canvas()
    eyebrow(d, "04 — The Core Analogy")
    y = 230
    d.text((MARGIN, y), "AI AGENTS", font=F_HEADLINE(92), fill=WHITE)
    y += 110
    d.text((MARGIN, y), "ARE 3D", font=F_HEADLINE(92), fill=WHITE)
    y += 110
    d.text((MARGIN, y), "PRINTERS.", font=F_HEADLINE(92), fill=CYAN)
    y += 180
    draw_multiline(
        d, (MARGIN, y),
        "You don’t spend your time printing.\nYou spend it on the CAD drawing.",
        F_BODY_B(44), WHITE, CONTENT_W, line_spacing=1.4,
    )
    y += 220
    draw_multiline(
        d, (MARGIN, y),
        "The spec defines every dimension, constraint, and tolerance — before a single token is generated.",
        F_BODY(38), MUTED, CONTENT_W, line_spacing=1.4,
    )
    footer_tag(d, "DESIGN MORE. PRINT LESS.")
    page_dots(d, 4)
    return img


# ---------------------------------------------------------------- Slide 6
def slide_06():
    img, d = base_canvas()
    eyebrow(d, "05 — The Spec Framework")
    y = 220
    draw_multiline(d, (MARGIN, y), "EVERY GOOD SPEC\nHAS FOUR PARTS", F_HEADLINE(78), WHITE, CONTENT_W, line_spacing=1.15)
    y += 260

    items = [
        ("01", "INTENT", "What are you building — and why?"),
        ("02", "CONSTRAINTS", "What must this never do?"),
        ("03", "CONTEXT", "What does the agent need to know about your system?"),
        ("04", "ACCEPTANCE CRITERIA", "How will you know the output is correct?"),
    ]
    row_h = 175
    for i, (num, title, desc) in enumerate(items):
        ry = y + i * row_h
        d.text((MARGIN, ry), num, font=F_HEADLINE(56), fill=VIOLET if i % 2 == 0 else CYAN)
        d.text((MARGIN + 110, ry + 4), title, font=F_BODY_B(38), fill=WHITE)
        draw_multiline(d, (MARGIN + 110, ry + 56), desc, F_BODY(30), MUTED, CONTENT_W - 110, line_spacing=1.3)
        if i < len(items) - 1:
            d.line([(MARGIN, ry + row_h - 30), (W - MARGIN, ry + row_h - 30)], fill=GRID, width=2)

    footer_tag(d, "THIS ISN’T PROMPTING. IT’S SPECIFYING.")
    page_dots(d, 5)
    return img


# ---------------------------------------------------------------- Slide 7
def slide_07():
    img, d = base_canvas()
    eyebrow(d, "06 — The New Interface")
    y = 240
    d.text((MARGIN, y), "AX —", font=F_HEADLINE(98), fill=WHITE)
    y += 118
    d.text((MARGIN, y), "AGENTIC", font=F_HEADLINE(98), fill=VIOLET)
    y += 118
    d.text((MARGIN, y), "EXPERIENCE", font=F_HEADLINE(98), fill=VIOLET)
    y += 170
    draw_multiline(
        d, (MARGIN, y),
        "Not fifty screens to click through. You declare intent — the agent navigates.",
        F_BODY_B(42), WHITE, CONTENT_W, line_spacing=1.4,
    )
    y += 210
    draw_multiline(
        d, (MARGIN, y),
        "It’s bidirectional: you shape the canvas, the canvas shapes the agent — in real time.",
        F_BODY(38), MUTED, CONTENT_W, line_spacing=1.4,
    )
    footer_tag(d, "PICASSO AND THE AGENT, ONE CANVAS")
    page_dots(d, 6)
    return img


# ---------------------------------------------------------------- Slide 8
def slide_08():
    img, d = base_canvas()
    eyebrow(d, "07 — Human In The Loop")
    y = 260
    d.text((MARGIN, y), "CO-PILOT.", font=F_HEADLINE(108), fill=WHITE)
    y += 130
    d.text((MARGIN, y), "NOT PILOT.", font=F_HEADLINE(108), fill=CYAN)
    y += 200
    draw_multiline(
        d, (MARGIN, y),
        "You don’t manage every sensor.\nYou don’t control every wheel.",
        F_BODY(42), MUTED, CONTENT_W, line_spacing=1.45,
    )
    y += 220
    draw_multiline(
        d, (MARGIN, y),
        "But you decide where this is going.",
        F_BODY_B(46), WHITE, CONTENT_W, line_spacing=1.4,
    )
    footer_tag(d, "1–3 AGENTS, NOT FIFTY — CREATION OVER CHAOS")
    page_dots(d, 7)
    return img


# ---------------------------------------------------------------- Slide 9
def slide_09():
    img, d = base_canvas()
    eyebrow(d, "08 — The Line")
    # stylized quote marks (drawn, not glyph-based, to avoid font metric overflow)
    for qx in (MARGIN, MARGIN + 64):
        d.rounded_rectangle([qx, 195, qx + 34, 270], radius=10, fill=VIOLET)
    y = 420
    draw_multiline(
        d, (MARGIN, y),
        "You do not want your bank app vibe-coded.",
        F_HEADLINE(64), WHITE, CONTENT_W, line_spacing=1.25,
    )
    y += 320
    d.line([(MARGIN, y), (W - MARGIN, y)], fill=GRID, width=2)
    draw_multiline(
        d, (MARGIN, y + 40),
        "Prototypes? Vibe away.\n\nProduction? You need the spec.",
        F_BODY(42), MUTED, CONTENT_W, line_spacing=1.45,
    )
    footer_tag(d, "QUALITY REQUIRES SPECS")
    page_dots(d, 8)
    return img


# ---------------------------------------------------------------- Slide 10
def slide_10():
    img, d = base_canvas()
    eyebrow(d, "Your Next Step")
    y = 230
    d.text((MARGIN, y), "WRITE THE SPEC", font=F_HEADLINE(80), fill=WHITE)
    y += 100
    d.text((MARGIN, y), "BEFORE THE PROMPT.", font=F_HEADLINE(80), fill=VIOLET)
    y += 160
    draw_multiline(
        d, (MARGIN, y),
        "Intent. Constraints. Context. Acceptance criteria.\nDo this before you write a single prompt.",
        F_BODY(40), WHITE, CONTENT_W, line_spacing=1.4,
    )
    y += 240
    box_y = y
    d.rectangle([MARGIN, box_y, W - MARGIN, box_y + 250], fill=(26, 26, 46), outline=VIOLET, width=2)
    draw_multiline(
        d, (MARGIN + 32, box_y + 36),
        "Full breakdown — link in bio",
        F_BODY_B(40), CYAN, CONTENT_W - 64, line_spacing=1.3,
    )
    draw_multiline(
        d, (MARGIN + 32, box_y + 110),
        "What’s the hardest part of working with AI agents in your workflow? Drop it below — I read every comment.",
        F_BODY(34), WHITE, CONTENT_W - 64, line_spacing=1.35,
    )
    footer_tag(d, "WATCH · SUBSCRIBE · COMMENT")
    page_dots(d, 9)
    return img


SLIDES = [slide_01, slide_02, slide_03, slide_04, slide_05, slide_06, slide_07, slide_08, slide_09, slide_10]

for i, fn in enumerate(SLIDES, start=1):
    img = fn()
    path = os.path.join(OUT_DIR, f"{i:02d}.png")
    img.save(path)
    print(f"Wrote {path}")
