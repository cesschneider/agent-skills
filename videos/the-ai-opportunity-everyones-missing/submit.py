#!/usr/bin/env python3
"""Render "The AI Opportunity Everyone's Missing" as 8 per-chapter HeyGen clips.

Each scene is submitted as its OWN single-scene video (not one combined
multi-scene render) so assemble.py can insert a title card from
scene-images/ between chapters at a clean boundary. video_id/status/
duration/video_url/captioned_url are written back onto each scene in
video-config.json as soon as they're known.

Run this, then run assemble.py to stitch intro + cards + clips into
final.mp4.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "skills", "heygen-api"))
from heygen_client import get_remaining_quota, generate_video_v2, get_video_status, poll_until_done

config_path = os.path.join(os.path.dirname(__file__), "video-config.json")
with open(config_path) as f:
    config = json.load(f)

quota = get_remaining_quota()
print(f"Quota: {quota.get('remaining_quota')} API credits")

# --- Submit every chapter as its own single-scene video first, saving
# each video_id immediately, so an interrupted run never loses progress
# and never resubmits a chapter that's already in flight. ---
for scene in config["scenes"]:
    if scene.get("video_id") and scene.get("status") in ("processing", "completed"):
        print(f"Scene {scene['id']} ({scene['name']}): already submitted ({scene['video_id']}), skipping resubmit")
        continue
    video_inputs = [{
        "character": {"type": "talking_photo", "talking_photo_id": config["avatar_id"]},
        "voice": {"type": "text", "input_text": scene["script"], "voice_id": config["voice_id"]},
        "background": {"type": "color", "value": config["background"]},
    }]
    video_id = generate_video_v2(
        title=f"{config['title']} — {scene['name']}",
        video_inputs=video_inputs,
        dimension=config["dimension"],
        caption=config["caption"],
    )
    print(f"Scene {scene['id']} ({scene['name']}): submitted {video_id}")
    scene["video_id"] = video_id
    scene["status"] = "processing"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

# --- Poll every chapter until completed/failed, writing results back as
# each one finishes. ---
for scene in config["scenes"]:
    if scene.get("status") == "completed":
        continue
    print(f"Polling scene {scene['id']} ({scene['name']})...")
    data = poll_until_done(
        scene["video_id"],
        on_update=lambda i, status, d, name=scene["name"]: print(f"  [{name}] [{i*15}s] {status}"),
    )
    scene.update({
        "status": "completed",
        "duration_s": data.get("duration"),
        "captioned_url": data.get("video_url_caption", ""),
        "video_url": data.get("video_url", ""),
    })
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

config["status"] = "rendered"
config["total_duration_s"] = sum(s.get("duration_s", 0) for s in config["scenes"])
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"\nAll {len(config['scenes'])} chapter clips rendered.")
print(f"Total avatar runtime: {config['total_duration_s']:.1f}s")
print("Next: python3 assemble.py")
