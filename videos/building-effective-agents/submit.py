#!/usr/bin/env python3
"""Submit the "How Anthropic Builds Effective AI Agents" breakdown video to HeyGen."""

import json, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "skills", "heygen-api"))
from heygen_client import get_remaining_quota, generate_video_v2, poll_until_done

config_path = os.path.join(os.path.dirname(__file__), "video-config.json")
with open(config_path) as f:
    config = json.load(f)

quota = get_remaining_quota()
print(f"Quota: {quota.get('remaining_quota')} API credits")

video_inputs = [
    {
        "character": {"type": "talking_photo", "talking_photo_id": config["avatar_id"]},
        "voice": {"type": "text", "input_text": scene["script"], "voice_id": config["voice_id"]},
        "background": {"type": "color", "value": config["background"]},
    }
    for scene in config["scenes"]
]

print(f"Submitting {len(video_inputs)} scenes (~{config['estimated_duration_min']} min)...")
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
    video_id,
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
print(f"GIF: {data.get('gif_url', '')}")
print(f"Captioned URL: {data.get('video_url_caption', '')[:100]}...")
