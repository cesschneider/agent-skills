---
name: social-video-production
description: Produces a complete multi-platform content package from a source YouTube video — extracts the topic/transcript, writes a scene-by-scene script, generates a HeyGen avatar video, renders key-topic scene images and a 10-slide Instagram carousel, and writes ready-to-paste YouTube/LinkedIn/Instagram captions with hashtags. Use when the user gives a YouTube URL (or pastes a transcript) and asks to turn it into a video, breakdown, or social content package.
---

# Social Video Production Pipeline

## Overview

Turns one source video into a full publishing package: an avatar-narrated breakdown video, supporting scene images, an Instagram carousel, and copy-paste-ready descriptions/captions for YouTube, LinkedIn, and Instagram — all saved under `videos/<topic>/`.

## When to Use

- The user provides a YouTube URL and asks for a breakdown/summary video, a "new video", or a "content package" from it.
- The user pastes a transcript directly and asks for the same output.
- The user asks for marketing assets (carousel, captions) for an already-produced `videos/<topic>/` video.
- NOT for: editing raw footage, live/interactive avatar streaming (see `heygen-mcp` skill), or generating unrelated standalone images.

## Inputs

| Input | Required | Notes |
|---|---|---|
| `youtube_url` | Yes (or a pasted transcript) | Source video to break down |
| `target_duration_min` | No | Default 9–10 min for long-form 16:9, ~90s for Shorts/9:16. Ask if ambiguous and the source is long-form. |
| `topic` slug | No | Derived from the video title (lowercase-hyphenated) — becomes `videos/<topic>/` |

Production defaults (avatar, voice, resolution, background) come from the **`heygen-mcp`** skill's "Production Configuration" section — do not redefine them here.

## Process

### 1. Extract Source Material

YouTube blocks direct transcript scraping in this environment (WebFetch on `youtube.com/watch` redirects to a Google captcha; third-party transcript sites return 403/404). Use this fallback order:

1. `WebFetch`/`WebSearch` to identify the title, channel, and topic from the URL.
2. `WebSearch` for articles, podcast write-ups, or summaries covering the same content (e.g., the show notes, a blog recap).
3. If neither yields enough substance, ask the user to paste the transcript.

From whatever material you gather, produce a `key_ideas` list (6–8 bullets) — the concrete frameworks, stats, analogies, and quotes worth covering.

**Copyright:** never reproduce long verbatim passages from a transcript or article. Synthesize an **original script** in your own words from the summarized ideas. Short (<25-word) attributed quotes are fine.

### 2. Write the Scene Script

- Word budget: `words ≈ target_duration_min × 130`.
- Structure as 8 scenes: **Hook**, 6 concept scenes (one core idea each), **Your Next Step / CTA**.
- Each scene: 90–200 words, plain spoken language (no markdown, no bullet symbols — write out "First/Second/Third").
- Save `videos/<topic>/video-config.json`:

```json
{
  "title": "...",
  "source_video": "https://youtu.be/...",
  "target_duration_min": 9,
  "avatar_id": "<from heygen-mcp skill>",
  "voice_id": "<from heygen-mcp skill>",
  "dimension": {"width": 1920, "height": 1080},
  "aspect_ratio": "16:9",
  "caption": true,
  "background": "#0f0f1a",
  "status": "draft",
  "key_ideas": ["..."],
  "scenes": [{"id": 1, "name": "Hook", "script": "...", "words": 0}],
  "total_words": 0,
  "estimated_duration_min": 0
}
```

Compute `words`, `total_words`, and `estimated_duration_min` (= `total_words / 130`) with a small Python snippet rather than by hand.

### 3. Generate Key-Topic Scene Images

Render one 1920×1080 image per scene/key idea using `generate_slides.py` (in this skill directory) — eyebrow label, big headline of the core idea, short supporting line. Save to `videos/<topic>/scene-images/`.

> **Known limitation:** `heygen_upload_asset` and `background: {type:"image"}` both fail (404/400) on the current HeyGen MCP proxy — see the `heygen-mcp` skill. These images are **not** wired into the HeyGen submission; they're standalone assets for thumbnails, B-roll overlays in a video editor, and social posts. HeyGen submissions use a solid `background.color` per the `heygen-mcp` skill.

### 4. Submit to HeyGen

Follow the `heygen-mcp` skill's standard flow: check quota → `heygen_generate_video_v2` with `video_inputs` built from `config["scenes"]` (talking_photo character, text voice, color background) → poll `heygen_get_video_status` until `completed`/`failed`. Write `video_id`, `duration_s`, `gif_url`, `captioned_url` back into `video-config.json`.

If the MCP proxy returns HTTP 404 mid-poll, the HeyGen render continues server-side — don't resubmit. Re-check `heygen_get_video_status` with the saved `video_id` once the proxy is back up.

### 5. Generate the Instagram Carousel

10 slides, 1080×1350, via `generate_slides.py`. Recommended structure:

1. Cover (title + one-line promise)
2. Hook stat or headline claim
3–8. One core idea per slide (mirrors the 6 concept scenes)
9. Sharpest quote/line from the source, as a pull-quote
10. CTA (next step + question to drive comments)

Save to `videos/<topic>/carousel/`.

### 6. Write Platform Copy

Produce, save to `videos/<topic>/marketing.md`, **and** print each as a separate fenced code block in the chat response (so the user can copy-paste directly):

- **YouTube description**: hook paragraph, chapter list with timestamps, CTA, hashtags. Compute chapter timestamps proportionally: `start_s = cumulative_words_before_scene / total_words × duration_s`.
- **LinkedIn post**: hook, the core framework/analogy, CTA, hashtags.
- **Instagram caption**: short hook + "swipe" prompt + CTA, hashtags.

Every platform output must include hashtags and be a complete, ready-to-paste block — no placeholders like `[link]` left unexplained (call out clearly that the user fills in their own link).

### 7. Save & Ship

Stage and commit everything under `videos/<topic>/` (config, scripts, scene-images, carousel, marketing.md). Push per the repo's git workflow.

## File Layout

```
videos/<topic>/
  video-config.json
  submit.py
  scene-images/01.png ... NN.png
  carousel/01.png ... 10.png
  carousel/build_carousel.py   (or shared generate_slides.py + its config)
  marketing.md
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll paste the transcript text directly into the script" | Copyright risk. Summarize into `key_ideas`, then write an original script. |
| "I'll skip the scene images, HeyGen backgrounds don't work anyway" | Scene images still ship as thumbnails/B-roll/social assets — generate them regardless. |
| "I'll just describe the captions instead of writing them out" | The user needs copy-paste text. Always emit full fenced blocks per platform. |
| "Word count is close enough, I'll skip computing it" | Compute it — it drives both `estimated_duration_min` and the YouTube chapter timestamps. |
| "The proxy 404'd, I'll resubmit the video" | The render continues server-side. Re-poll with the saved `video_id` instead of resubmitting. |

## Red Flags

- Long verbatim quotes (>25 words) from the source video/article in the script or `marketing.md`.
- `video-config.json` missing `total_words`/`estimated_duration_min`, or scene `words` not matching the actual script.
- HeyGen submission using `background.type: "image"` or `heygen_upload_asset` (both broken — color backgrounds only).
- Carousel or scene images with overlapping/clipped text — always inspect rendered PNGs before shipping.
- Marketing copy missing hashtags on any of the three platforms.

## Verification

- [ ] `videos/<topic>/video-config.json` has scenes, accurate `total_words`/`estimated_duration_min`, and (after submission) `video_id` + `status`
- [ ] Scene images rendered to `videos/<topic>/scene-images/` (one per key idea)
- [ ] 10-slide carousel rendered to `videos/<topic>/carousel/`, each slide visually inspected for overlap/clipping
- [ ] `videos/<topic>/marketing.md` contains YouTube description, LinkedIn post, and Instagram caption — each with hashtags
- [ ] Same three copy blocks also printed in the chat response as fenced code blocks
- [ ] `videos/<topic>/` committed and pushed
