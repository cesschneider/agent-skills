---
name: heygen-mcp
description: Connects to HeyGen via an authenticated MCP server to create avatar videos, manage streaming sessions, and generate speech. Use when producing AI avatar videos, building interactive streaming avatars, synthesizing speech, or managing HeyGen assets and templates programmatically.
---

# HeyGen MCP Integration

## Overview

HeyGen is an AI video platform. This skill governs how to interact with it through its MCP server, which exposes 36 tools spanning video generation, avatar management, voice synthesis, interactive streaming, template workflows, webhook registration, and asset management.

The MCP server uses HTTP + SSE transport and requires a `Bearer` token on every request. All credentials are sourced from environment variables — never hardcoded.

## Environment Variables

| Variable  | Purpose                                    |
|-----------|--------------------------------------------|
| `MCP_URL` | Full endpoint URL (includes `/api/mcp`)    |
| `API_KEY` | HeyGen API key used as the Bearer token    |

The Claude Code settings at `.claude/settings.json` wires these automatically:

```json
{
  "mcpServers": {
    "heygen": {
      "type": "http",
      "url": "${MCP_URL}",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

## When to Use

- Generating a one-shot avatar video from a script or prompt
- Building personalized video campaigns using templates
- Running an interactive avatar session (WebRTC streaming)
- Synthesizing speech before embedding audio in a video
- Auditing account quota or listing existing videos/assets
- Registering webhooks to track async video completion

## Tool Reference

### Account
| Tool | Purpose |
|------|---------|
| `heygen_get_user_info` | Authenticated user's username, email, and account status |
| `heygen_get_remaining_quota` | Remaining API credit balance (USD; $1 ≈ 1 min of 720p/1080p video) |

### Video Generation
| Tool | Purpose |
|------|---------|
| `heygen_create_video` | Create a video with full control — avatar, voice, resolution, aspect ratio, motion prompt |
| `heygen_get_video_status` | Poll status (`pending → processing → completed/failed`) and retrieve the download URL |
| `heygen_create_video_agent` | One-shot v3 generation from a natural language prompt; HeyGen picks avatar/voice/settings |
| `heygen_video_agent_generate` | One-shot v1 agent endpoint (simpler payload, less control) |
| `heygen_list_videos` | List all account videos with status, title, and URL (paginated) |
| `heygen_delete_video` | Permanently delete a video |
| `heygen_generate_video_v2` | Legacy v2 multi-scene videos (supported until Oct 2026) |
| `heygen_generate_avatar_iv_video` | Avatar IV via v2 endpoint — photorealistic, angled/profile photo support |

### Avatars
| Tool | Purpose |
|------|---------|
| `heygen_list_avatars` | All avatars (stock + custom) with IDs, names, genders, preview URLs |
| `heygen_list_avatar_groups` | Avatar groups organizing related looks/styles |
| `heygen_list_avatars_in_group` | Avatars within a specific group |
| `heygen_upload_photo_avatar` | Upload a photo URL to create a Talking Photo avatar |

### Voices
| Tool | Purpose |
|------|---------|
| `heygen_list_voices` | Filterable by type, engine, language, gender; use `engine=starfish` for TTS |
| `heygen_list_voices_v2` | Legacy v2 voice list with preview audio URLs |

### Templates
| Tool | Purpose |
|------|---------|
| `heygen_list_templates` | All available templates |
| `heygen_get_template` | Template variable definitions (avatar, text, media placeholders) |
| `heygen_generate_from_template` | Generate a personalized video by populating template variables |
| `heygen_get_template_v3` | v3 equivalent of `heygen_get_template` |
| `heygen_generate_from_template_v3` | v3 equivalent of `heygen_generate_from_template` |

### Interactive Streaming
| Tool | Purpose |
|------|---------|
| `heygen_create_streaming_token` | Short-lived session token — **always generate server-side, never expose to browser** |
| `heygen_create_streaming_session` | Create a WebRTC session (returns `session_id`, SDP offer, LiveKit URL) |
| `heygen_start_streaming_session` | Activate a session by providing the WebRTC SDP answer |
| `heygen_list_streaming_sessions` | Audit all open sessions to avoid quota leaks |
| `heygen_send_streaming_task` | Make avatar speak (`repeat`) or respond from knowledge base (`talk`) |
| `heygen_interrupt_streaming` | Stop the avatar mid-speech immediately |
| `heygen_keep_alive_streaming` | Reset idle timer to prevent auto-termination |
| `heygen_stop_streaming_session` | Terminate a session — **always call when done** |

### Assets & Speech
| Tool | Purpose |
|------|---------|
| `heygen_upload_asset` | Upload image/audio/video from a public URL; returns `asset_id` |
| `heygen_get_asset` | Retrieve details of an uploaded asset |
| `heygen_generate_speech` | Text-to-speech via `starfish` engine voices; returns audio URL |

### Webhooks
| Tool | Purpose |
|------|---------|
| `heygen_list_webhooks` | All registered webhook endpoints |
| `heygen_add_webhook` | Register an HTTPS URL for event notifications (`avatar_video.success`, etc.) |
| `heygen_delete_webhook` | Remove a webhook endpoint |

## Process

### Creating a Video (Standard Flow)

```
1. heygen_get_remaining_quota       → confirm credits before generating
2. heygen_list_avatars              → pick avatar_id
3. heygen_list_voices               → pick voice_id (filter by language/gender)
4. heygen_create_video              → submit job, receive video_id
5. heygen_get_video_status          → poll until status = "completed" or "failed"
6. [on failure] inspect failure_code + failure_message in response
```

### One-Shot Video from Prompt

```
1. heygen_get_remaining_quota
2. heygen_create_video_agent        → submit natural language prompt
3. heygen_get_video_status          → poll for completion
```

### Interactive Streaming Session

```
1. heygen_create_streaming_token    → get short-lived token (server-side only)
2. heygen_create_streaming_session  → create WebRTC session, get SDP offer + LiveKit URL
3. [frontend] negotiate WebRTC, produce SDP answer
4. heygen_start_streaming_session   → activate with SDP answer
5. heygen_send_streaming_task       → avatar speaks (repeat) or responds (talk)
6. heygen_keep_alive_streaming      → call periodically during idle
7. heygen_stop_streaming_session    → terminate — mandatory cleanup
```

### Template-Based Personalized Video

```
1. heygen_list_templates            → find template_id
2. heygen_get_template_v3           → discover variable names and types
3. heygen_generate_from_template_v3 → fill variables, submit job
4. heygen_get_video_status          → poll for completion
```

### Speech-First Workflow (Audio Lip-Sync)

```
1. heygen_list_voices               → filter engine=starfish, pick voice_id
2. heygen_generate_speech           → produce audio, get audio URL
3. heygen_upload_asset              → upload audio, get asset_id
4. heygen_create_video              → pass audio_asset_id instead of script
5. heygen_get_video_status          → poll for completion
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll poll once and assume it's done" | Videos are async — always poll until `completed` or `failed`. Processing can take minutes. |
| "The streaming token is safe to pass to the frontend" | Never. Tokens are short-lived and must stay server-side to protect the API key. |
| "I don't need to call stop_streaming_session" | Unclosed sessions consume quota. Always terminate explicitly. |
| "I'll use v2 for everything since it's familiar" | v2 is deprecated for single-scene videos. Use v3 (`heygen_create_video`) for new work. |
| "Audio and script are interchangeable" | They are mutually exclusive fields — passing both is an error. |

## Red Flags

- Calling `heygen_create_video` without checking `heygen_get_remaining_quota` first in critical flows
- Passing `script` and `audio_asset_id` together in the same request
- Exposing a streaming session token to client-side JavaScript
- Never calling `heygen_stop_streaming_session` after a streaming workflow
- Using `heygen_list_voices_v2` when `heygen_list_voices` with `engine=starfish` is required for TTS
- Not validating the HeyGen API response shape before using it in application logic

## Verification

After any video creation:

- [ ] `heygen_get_video_status` polled until status is `completed` (not assumed)
- [ ] `failure_code` and `failure_message` checked when status is `failed`
- [ ] Remaining quota confirmed before bulk or long-form generation
- [ ] Streaming sessions explicitly terminated with `heygen_stop_streaming_session`
- [ ] Streaming tokens never appear in client-side code or logs
- [ ] API response shape validated before downstream use
