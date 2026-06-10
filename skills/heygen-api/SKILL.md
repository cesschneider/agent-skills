---
name: heygen-api
description: Connects directly to HeyGen's native REST API (api.heygen.com) to create avatar videos, manage avatars/voices/assets, and poll render status — authenticated with an X-Api-Key header, no MCP server or proxy gateway involved. Use when producing AI avatar videos, generating multi-scene HeyGen videos, uploading image/audio assets, or checking HeyGen render status.
---

# HeyGen API Integration

## Overview

HeyGen is an AI video platform. This skill governs direct, server-to-server use of its REST API at `https://api.heygen.com`. Every request is a plain HTTPS call authenticated with an `X-Api-Key` header — there is no MCP server, SSE transport, or third-party proxy in the path.

A shared client module, `heygen_client.py` (in this skill directory), wraps the endpoints used for video production. Import it from `videos/<topic>/` scripts instead of re-implementing HTTP calls.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `HEYGEN_API_KEY` | HeyGen API key, sent as the `X-Api-Key` header on every request. Get it from the HeyGen dashboard under Settings → API. Never hardcode it. |

## When to Use

- Generating a one-shot or multi-scene avatar video from a script
- Checking remaining API credit quota before a generation run
- Listing avatars/voices to find an `avatar_id`/`voice_id`
- Uploading an image/audio/video asset for use as a background or input
- Polling a submitted video until it completes or fails

## Endpoint Reference

All endpoints are on `https://api.heygen.com`, header `X-Api-Key: $HEYGEN_API_KEY`.

| Endpoint | Method | Purpose | Wrapped by |
|----------|--------|---------|------------|
| `/v2/user/remaining_quota` | GET | Remaining API credit balance ($1 ≈ 1 min of 720p/1080p video) | `get_remaining_quota()` |
| `/v2/avatars` | GET | List avatars (stock + custom) with `avatar_id`, name, gender | `list_avatars()` |
| `/v2/voices` | GET | List voices with `voice_id`, language, gender, emotion support | `list_voices()` |
| `/v3/assets` | POST (multipart) | Upload an image/video/audio/PDF (max 32MB), returns `asset_id` + public `url` | `upload_asset(path)` |
| `/v2/video/generate` | POST | Submit a 1-50 scene video (`video_inputs`, `dimension`, `caption`, `title`) | `generate_video_v2(...)` |
| `/v1/video_status.get?video_id=...` | GET | Poll status (`pending → processing → completed/failed`); returns `video_url`, `gif_url`, `video_url_caption`, `duration` | `get_video_status(id)` / `poll_until_done(id)` |

`/v1` and `/v2` endpoints (including the multi-scene `/v2/video/generate` used for this project's videos) are supported through October 31, 2026. HeyGen's newer `/v3/videos` and `/v3/video-agents` endpoints cover single-scene/agent-driven generation but do not yet replace the multi-scene Studio workflow — keep using `/v2/video/generate` for multi-scene avatar videos. Full reference: https://developers.heygen.com/docs/quick-start

## Production Configuration

### Confirmed Avatar — "City Loft Studio with Microphone"

| Engine | Avatar ID | Use when |
|--------|-----------|----------|
| Avatar V (standard, talking_photo) | `731e46ac49bf4795bd4e4c799f1d3b95` | Walkthroughs, tutorials, bulk scenes |
| Avatar IV (cinematic) | `0b89efd1a0a446e29b155177f63a0446` | Intros, outros, hero segments |

- **Look name:** Cesar Schneider at the microphone
- **Group:** Cesar Schneider (`d835d346a0cc455cb41b98c1b73d1c78`)
- **Voice:** Cesar Schneider cloned voice — `c0a044792fc64b3fa7dfc0700da93016`
- **Resolution:** `1080p` · **Aspect ratio:** `16:9` (YouTube main), `9:16` (Shorts)

This avatar is used for **all talking-head scenes** across every video. Do not switch looks mid-episode — visual consistency is the brand.

## Process

### Multi-Scene Video (Standard Flow)

```python
import sys
sys.path.insert(0, "<repo>/skills/heygen-api")
from heygen_client import get_remaining_quota, generate_video_v2, poll_until_done

print(get_remaining_quota())  # confirm credits before generating

video_inputs = [
    {
        "character": {"type": "talking_photo", "talking_photo_id": AVATAR_ID},
        "voice": {"type": "text", "input_text": scene["script"], "voice_id": VOICE_ID},
        "background": {"type": "color", "value": "#0f0f1a"},
    }
    for scene in scenes
]

video_id = generate_video_v2(title=title, video_inputs=video_inputs,
                              dimension={"width": 1920, "height": 1080}, caption=True)

data = poll_until_done(video_id, on_update=lambda i, status, d: print(f"[{i*15}s] {status}"))
print(data["video_url"], data["video_url_caption"], data["gif_url"], data["duration"])
```

1. `get_remaining_quota()` → confirm credits before generating
2. `generate_video_v2(...)` → submit job, save `video_id` immediately (in case polling is interrupted)
3. `poll_until_done(video_id)` → polls `/v1/video_status.get` every 15s until `completed`/`failed`
4. On `failed`, inspect `error`/`failure_code`/`failure_message` in the returned data

### Resuming a Poll

If a script crashes or the session restarts mid-poll, **do not resubmit** — the render continues server-side. Re-run with the saved `video_id`:

```python
data = poll_until_done(video_id, on_update=...)
```

### Image/Asset Backgrounds

Upload via `upload_asset(path)` → returns `{"asset_id", "url", ...}`. Use the returned `url` as `background: {"type": "image", "url": ...}` in `video_inputs`. (The previous MCP-proxy path could not reach `/v3/assets` — calling it directly should work now; verify with a small test generation before relying on it for a full run.)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll poll once and assume it's done" | Videos are async — always poll until `completed` or `failed`. Processing can take minutes. |
| "A request failed once, I'll resubmit" | Network blips happen. Retry the *same* call (status checks are idempotent); only `generate_video_v2` creates a new job, so never resend that one for a `video_id` you already have. |
| "I'll hardcode the API key to save an env lookup" | Never. `HEYGEN_API_KEY` must come from the environment — `heygen_client.py` enforces this. |
| "Audio and script are interchangeable" | `video_inputs[].voice` is either `{"type":"text", ...}` or `{"type":"audio", ...}` — mutually exclusive. |

## Red Flags

- Calling `generate_video_v2` without checking `get_remaining_quota()` first for bulk/long-form runs
- Hardcoded API keys or keys committed to `video-config.json` / scripts
- Treating a single `pending`/`processing` status as failure — only `completed`/`failed` are terminal
- Not validating the response shape (`data["status"]`, `data["video_id"]`) before downstream use

## Verification

After any video creation:

- [ ] `get_remaining_quota()` checked before bulk or long-form generation
- [ ] `video_id` saved to `video-config.json` immediately after submission (before polling)
- [ ] Polled via `poll_until_done`/`get_video_status` until status is `completed` (not assumed)
- [ ] `error`/`failure_code`/`failure_message` checked when status is `failed`
- [ ] `video_url`, `video_url_caption`, `gif_url`, `duration` written back to `video-config.json` on completion
