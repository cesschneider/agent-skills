#!/usr/bin/env python3
"""Render "Is Agent Orchestration the Top Engineering Skill of 2026?" as
ONE native HeyGen multi-scene video: an intro, then for each chapter a
narrated slide scene (no avatar, full-frame scene image, voice-over)
followed by the avatar scene for that chapter.

HeyGen stitches and transitions between scenes itself — no local ffmpeg
assembly is needed. video_id/status/duration/video_url/captioned_url are
written back onto video-config.json once the single render completes.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "skills", "heygen-api"))
from heygen_client import get_remaining_quota, upload_asset, generate_video_v2, poll_until_done

topic_dir = os.path.dirname(__file__)
config_path = os.path.join(topic_dir, "video-config.json")
with open(config_path) as f:
    config = json.load(f)

quota = get_remaining_quota()
print(f"Quota: {quota.get('remaining_quota')} API credits")


def ensure_uploaded(scene):
    """Upload a slide scene's image once and cache the asset URL in config."""
    if scene.get("image_url"):
        return scene["image_url"]
    image_path = os.path.join(topic_dir, scene["image"])
    print(f"Uploading slide image for scene {scene['id']} ({scene['name']})...")
    asset = upload_asset(image_path)
    scene["image_url"] = asset["url"]
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    return scene["image_url"]


video_inputs = []
for scene in config["scenes"]:
    if scene["type"] == "avatar":
        video_inputs.append({
            "character": {"type": "talking_photo", "talking_photo_id": config["avatar_id"]},
            "voice": {"type": "text", "input_text": scene["script"], "voice_id": config["voice_id"]},
            "background": {"type": "color", "value": config["background"]},
        })
    elif scene["type"] == "slide":
        image_url = ensure_uploaded(scene)
        video_inputs.append({
            "voice": {"type": "text", "input_text": scene["narration"], "voice_id": config["voice_id"]},
            "background": {"type": "image", "url": image_url},
        })
    else:
        sys.exit(f"Unknown scene type {scene['type']!r} for scene {scene['id']}")

if config.get("video_id") and config.get("status") in ("processing", "completed"):
    print(f"Already submitted ({config['video_id']}, status={config['status']}), skipping resubmit")
else:
    print(f"Submitting {len(video_inputs)} scenes in a single multi-scene render...")
    video_id = generate_video_v2(
        title=config["title"],
        video_inputs=video_inputs,
        dimension=config["dimension"],
        caption=config["caption"],
    )
    print(f"Submitted: {video_id}")
    config["video_id"] = video_id
    config["status"] = "processing"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

print("Polling...")
data = poll_until_done(
    config["video_id"],
    on_update=lambda i, status, d: print(f"  [{i*15}s] {status}"),
)

config.update({
    "status": "completed",
    "duration_s": data.get("duration"),
    "gif_url": data.get("gif_url", ""),
    "captioned_url": data.get("video_url_caption", ""),
    "video_url": data.get("video_url", ""),
})
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"\nDone — {data.get('duration')}s")
print(f"Captioned URL: {data.get('video_url_caption', '')[:100]}...")
print(f"Video URL: {data.get('video_url', '')[:100]}...")
