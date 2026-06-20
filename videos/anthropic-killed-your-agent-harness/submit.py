#!/usr/bin/env python3
"""Render "Anthropic Just Killed Your Agent Harness" as 8 per-chapter HeyGen
clips, plus one short card-narration clip per chapter.

Each scene is submitted as its OWN single-scene video (not one combined
multi-scene render) so assemble.py can insert a chapter-card slide between
chapters at a clean boundary. Each scene also gets a second, short
single-scene render of `card_script` (same avatar/voice, solid background)
— assemble.py keeps only that render's audio and pairs it with the
scene-images/NN.png slide, so the slide plays with a spoken explanation
instead of sitting silently. video_id/status/duration/video_url/
captioned_url (and the card_ equivalents) are written back onto each scene
in video-config.json as soon as they're known.

Run this, then run assemble.py to stitch intro + narrated cards + clips
into final.mp4.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "skills", "heygen-api"))
from heygen_client import get_remaining_quota, generate_video_v2, poll_until_done

config_path = os.path.join(os.path.dirname(__file__), "video-config.json")
with open(config_path) as f:
    config = json.load(f)

quota = get_remaining_quota()
print(f"Quota: {quota.get('remaining_quota')} API credits")


def submit_scene(scene, text, title_suffix, id_field, status_field):
    if scene.get(id_field) and scene.get(status_field) in ("processing", "completed"):
        print(f"Scene {scene['id']} ({scene['name']}) {title_suffix}: already submitted ({scene[id_field]}), skipping resubmit")
        return
    video_inputs = [{
        "character": {"type": "talking_photo", "talking_photo_id": config["avatar_id"]},
        "voice": {"type": "text", "input_text": text, "voice_id": config["voice_id"]},
        "background": {"type": "color", "value": config["background"]},
    }]
    video_id = generate_video_v2(
        title=f"{config['title']} — {scene['name']} {title_suffix}",
        video_inputs=video_inputs,
        dimension=config["dimension"],
        caption=config["caption"],
    )
    print(f"Scene {scene['id']} ({scene['name']}) {title_suffix}: submitted {video_id}")
    scene[id_field] = video_id
    scene[status_field] = "processing"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def poll_scene(scene, id_field, status_field, duration_field, captioned_field, url_field):
    if scene.get(status_field) == "completed":
        return
    print(f"Polling scene {scene['id']} ({scene['name']}) [{status_field}]...")
    data = poll_until_done(
        scene[id_field],
        on_update=lambda i, status, d, name=scene["name"]: print(f"  [{name}] [{i*15}s] {status}"),
    )
    scene[status_field] = "completed"
    scene[duration_field] = data.get("duration")
    scene[captioned_field] = data.get("video_url_caption", "")
    scene[url_field] = data.get("video_url", "")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


# --- Submit every chapter's main avatar clip and its card-narration clip
# first, saving each video_id immediately, so an interrupted run never
# loses progress and never resubmits a chapter that's already in flight. ---
for scene in config["scenes"]:
    submit_scene(scene, scene["script"], "(chapter)", "video_id", "status")
    if scene.get("card_script"):
        submit_scene(scene, scene["card_script"], "(card narration)", "card_video_id", "card_status")

# --- Poll every chapter and card-narration clip until completed/failed,
# writing results back as each one finishes. ---
for scene in config["scenes"]:
    poll_scene(scene, "video_id", "status", "duration_s", "captioned_url", "video_url")
    if scene.get("card_script"):
        poll_scene(scene, "card_video_id", "card_status", "card_duration_s", "card_captioned_url", "card_video_url")

config["status"] = "rendered"
config["total_duration_s"] = sum(s.get("duration_s", 0) for s in config["scenes"])
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"\nAll {len(config['scenes'])} chapter clips (+ card narrations) rendered.")
print(f"Total avatar runtime: {config['total_duration_s']:.1f}s")
print("Next: python3 ../../skills/social-video-production/assemble.py videos/anthropic-killed-your-agent-harness/")
