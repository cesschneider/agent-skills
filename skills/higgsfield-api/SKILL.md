---
name: higgsfield-api
description: Connects directly to Higgsfield's official REST API (platform.higgsfield.ai) to generate images (Soul, Seedream, Reve) and videos (DOP, Seedance, Kling) from text or reference images — authenticated with an API key/secret pair, no MCP server or proxy gateway involved. Use when generating B-roll clips, cinematic product/character shots, or social-asset images/videos as part of a video production pipeline.
---

# Higgsfield API Integration

## Overview

Higgsfield is an AI image/video generation platform built on a fal.ai-style async queue. This skill governs direct, server-to-server use of its **official** REST API at `https://platform.higgsfield.ai`. Every request is a plain HTTPS call authenticated with an `Authorization: Key <api_key>:<api_secret>` header — there is no MCP server, browser session, or third-party proxy in the path.

A shared client module, `higgsfield_client.py` (in this skill directory), wraps the submit/poll/result pattern. Import it from `videos/<topic>/` scripts instead of re-implementing HTTP calls.

> **Unverified surface area.** Higgsfield's official docs are sparse and the exact request/response field names vary by model and change without notice. Treat the model catalog and payload shapes below as a starting point — always run one cheap test generation for a model before relying on it in a full production run (see Verification).

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `HIGGSFIELD_API_KEY` | Higgsfield API key ID, first half of the `Key <id>:<secret>` auth header. From the [Higgsfield Cloud](https://cloud.higgsfield.ai/) dashboard. Never hardcode it. |
| `HIGGSFIELD_API_SECRET` | Higgsfield API key secret, second half of the auth header. Never hardcode it. |

## When to Use

- Generating B-roll clips or cinematic stills to cut alongside a HeyGen avatar narration
- Generating a consistent "Soul Character" across multiple images/videos for a recurring on-screen presence
- Image-to-video animation of an existing still (product shots, thumbnails) via DOP/Seedance/Kling
- As an **alternative render backend** to `heygen-api` for a project's narration video — see `social-video-production`'s `render_backend` field

## Model Reference

All endpoints are on `https://platform.higgsfield.ai`, header `Authorization: Key $HIGGSFIELD_API_KEY:$HIGGSFIELD_API_SECRET`. Submit with `POST /{model_id}`, body `{"input": {...}}`.

| Model ID | Type | Purpose |
|----------|------|---------|
| `higgsfield-ai/soul/standard` | Image | Soul — stylized portraits/characters with consistent identity |
| `reve/text-to-image` | Image | General text-to-image |
| `bytedance/seedream/v4/text-to-image` | Image | Text-to-image (cheapest — use for connectivity tests) |
| `bytedance/seedream/v4/edit` | Image | Image editing/inpainting |
| `higgsfield-ai/dop/preview`, `higgsfield-ai/dop/standard` | Video | Image-to-video animation ("DOP") |
| `bytedance/seedance/v1/pro/image-to-video` | Video | Image-to-video, cinematic motion |
| `kling-video/v2.1/pro/image-to-video` | Video | Image-to-video, Kling engine |

`input` typically includes `prompt` (text models) or `image_url` + `prompt` (image-to-video models), plus model-specific params like `aspect_ratio`/`resolution` or `width`/`height` — confirm the exact keys for a model with one test call before bulk use.

## Production Configuration

No Soul Character has been created for this project yet. Once one exists, record its identity/reference here (mirroring the `heygen-api` skill's avatar table) so every video reuses the same on-screen character:

| Asset | ID | Use when |
|-------|-----|----------|
| _(none yet)_ | — | Create via the Higgsfield dashboard, then add the Soul Character ID here |

## Process

### Submit, Poll, Collect (Standard Flow)

```python
import sys
sys.path.insert(0, "<repo>/skills/higgsfield-api")
from higgsfield_client import submit, poll_until_done

MODEL = "bytedance/seedream/v4/text-to-image"

request_id = submit(MODEL, {
    "prompt": "A neon-lit city loft at night, cinematic, 35mm",
    "aspect_ratio": "16:9",
})

result = poll_until_done(MODEL, request_id,
                          on_update=lambda i, status, d: print(f"[{i*5}s] {status}"))
print(result)  # inspect once — field names (images[].url vs video.url) vary by model
```

1. `submit(model_id, input)` → returns `request_id`; save it immediately (in case polling is interrupted)
2. `poll_until_done(model_id, request_id)` → polls status every 5s until `COMPLETED`/`FAILED`/`NSFW`/`CANCELLED`
3. On a terminal non-`COMPLETED` status, `poll_until_done` raises with the full status payload — inspect it for the failure reason
4. Download the resulting image/video URL(s) from the result payload (field names vary by model — print and inspect on first use)

### Resuming a Poll

If a script crashes mid-poll, **do not resubmit** — re-run with the saved `request_id`:

```python
result = poll_until_done(MODEL, request_id, on_update=...)
```

### Image-to-Video with a Reference Image

Upload a local still first, then pass its URL as `image_url`:

```python
from higgsfield_client import upload_file, submit, poll_until_done

image_url = upload_file("scene-images/03.png")
request_id = submit("higgsfield-ai/dop/standard", {
    "image_url": image_url,
    "prompt": "slow push-in, subtle parallax",
})
result = poll_until_done("higgsfield-ai/dop/standard", request_id)
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "The model catalog in this doc is final, I'll trust the field names" | Higgsfield's docs are sparse and change without notice. Run one cheap test (`bytedance/seedream/v4/text-to-image`) and print the raw result before scripting a full batch. |
| "I'll poll once and assume it's done" | Generation is async — always poll until `COMPLETED`/`FAILED`/`NSFW`/`CANCELLED`. |
| "I'll hardcode the API key/secret to save env lookups" | Never. Both `HIGGSFIELD_API_KEY` and `HIGGSFIELD_API_SECRET` must come from the environment. |
| "A request failed once, I'll resubmit" | Retry the *same* status/result call (idempotent); only `submit()` creates a new job — don't resend it for a `request_id` you already have. |

## Red Flags

- Calling `submit()` for a new model without a prior cheap test call to confirm `input` keys and result field names
- Hardcoded API keys/secrets, or keys committed to `video-config.json` / scripts
- Treating `IN_QUEUE`/`IN_PROGRESS` as failure — only `COMPLETED`/`FAILED`/`NSFW`/`CANCELLED` are terminal
- Using the unofficial `cloud.higgsfield.ai`/`fnf.higgsfield.ai` web backend (cookie/session auth, reverse-engineered, against this skill's "no proxy" rule)

## Verification

After any generation:

- [ ] `request_id` saved immediately after `submit()` (before polling)
- [ ] Polled via `poll_until_done`/`get_status` until a terminal status (not assumed)
- [ ] Result payload printed/inspected at least once per model to confirm field names before scripting a batch
- [ ] On `FAILED`/`NSFW`, the full status payload was inspected for the reason
- [ ] Generated asset URLs downloaded/saved into `videos/<topic>/` before the signed URLs expire
