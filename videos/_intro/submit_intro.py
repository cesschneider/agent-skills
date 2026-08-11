#!/usr/bin/env python3
"""Render the reusable channel intro via HeyGen — run this ONCE.

Submits intro-config.json's script as a single-scene HeyGen video, polls
until done, downloads the result, and re-encodes it to the canonical spec
(1920x1080, 30fps, yuv420p H.264, 48kHz stereo AAC) so it concatenates
cleanly with any chapter clip in assemble.py. Writes the final file to
intro.mp4 and records video_id/duration/status back into intro-config.json.

Do not re-run this once intro.mp4 exists and is committed — every
video's assemble.py step reuses that one file. Only re-run if the
script or avatar/voice intentionally changes (and re-commit the new
intro.mp4 for every future video to stay consistent).
"""

import json
import os
import subprocess
import sys

import requests

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "..", "skills", "heygen-api"))
from heygen_client import get_remaining_quota, generate_video_v2, poll_until_done

import imageio_ffmpeg

config_path = os.path.join(HERE, "intro-config.json")
with open(config_path) as f:
    config = json.load(f)

quota = get_remaining_quota()
print(f"Quota: {quota.get('remaining_quota')} API credits")

video_inputs = [{
    "character": {"type": "talking_photo", "talking_photo_id": config["avatar_id"]},
    "voice": {"type": "text", "input_text": config["script"], "voice_id": config["voice_id"]},
    "background": {"type": "color", "value": config["background"]},
}]

print(f"Submitting intro ({config['words']} words)...")
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
data = poll_until_done(video_id, on_update=lambda i, status, d: print(f"  [{i*15}s] {status}"))

raw_path = os.path.join(HERE, "_intro_raw.mp4")
final_path = os.path.join(HERE, "intro.mp4")

print("Downloading raw render (captioned)...")
source_url = data.get("video_url_caption") or data["video_url"]
resp = requests.get(source_url, stream=True)
resp.raise_for_status()
with open(raw_path, "wb") as f:
    for chunk in resp.iter_content(chunk_size=1 << 20):
        f.write(chunk)

print("Normalizing to canonical spec (1920x1080, 30fps, h264, aac 48k stereo)...")
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([
    ffmpeg, "-y", "-i", raw_path,
    "-vf", "scale=1920:1080,fps=30",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
    "-c:a", "aac", "-ar", "48000", "-ac", "2",
    final_path,
], check=True)
os.remove(raw_path)

config.update({
    "status": "completed",
    "duration_s": data.get("duration"),
    "captioned_url": data.get("video_url_caption", ""),
    "video_url": data.get("video_url", ""),
})
with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"\nDone — intro.mp4 ready ({data.get('duration')}s)")
