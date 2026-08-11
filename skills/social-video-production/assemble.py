#!/usr/bin/env python3
"""Assemble a video's final cut: intro -> [chapter card -> avatar clip] x N.

Usage:
    python3 assemble.py videos/<topic>/

Reads videos/<topic>/video-config.json, expects every scene to already
have a completed per-chapter HeyGen render (video_id/video_url/
captioned_url/duration_s — see that directory's submit.py), and expects
videos/<topic>/scene-images/01.png..NN.png (one per scene, in order,
from scene-images-config.json) to exist.

Reuses the channel intro at videos/_intro/intro.mp4 (rendered once by
videos/_intro/submit_intro.py — run that first if it doesn't exist yet).

Pipeline, per chapter:
  1. Card: if the scene has a `card_video_url`/`card_captioned_url` (a
     short HeyGen render of `card_script`, solid background, submitted
     by this video's submit.py purely for narration audio), the card
     plays the scene-images/NN.png slide as its visual for that clip's
     actual duration, with the rendered narration as its audio track —
     the avatar itself never appears during the slide. If no card
     narration was rendered, falls back to a silent CARD_DURATION-second
     card.
  2. Avatar clip: download the chapter's captioned avatar clip, normalize
     to the canonical spec (1920x1080, 30fps, yuv420p H.264, AAC 48kHz
     stereo).
  3. Chain intro + (card, avatar) x N with XFADE_DURATION-second
     crossfades (video: xfade, audio: acrossfade) into one ffmpeg
     filter_complex, output videos/<topic>/final.mp4.

Requires `pip install imageio-ffmpeg` (bundles a static ffmpeg binary —
no system ffmpeg needed).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import requests
import imageio_ffmpeg

CARD_DURATION = 2.8
XFADE_DURATION = 0.5
CANON_W, CANON_H, CANON_FPS = 1920, 1080, 30

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def normalize_video(src, dst):
    run([
        FFMPEG, "-y", "-i", src,
        "-vf", f"scale={CANON_W}:{CANON_H}:force_original_aspect_ratio=decrease,"
               f"pad={CANON_W}:{CANON_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={CANON_FPS}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        dst,
    ])


def download(url, dst):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(dst, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 20):
            f.write(chunk)


def render_card(image_path, dst, duration):
    fade = min(0.4, duration / 4)
    run([
        FFMPEG, "-y",
        "-loop", "1", "-i", image_path,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t", str(duration),
        "-vf", f"scale={CANON_W}:{CANON_H}:force_original_aspect_ratio=decrease,"
               f"pad={CANON_W}:{CANON_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={CANON_FPS},"
               f"fade=t=in:st=0:d={fade},fade=t=out:st={duration - fade}:d={fade}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-shortest",
        dst,
    ])


def render_narrated_card(image_path, narration_audio_path, dst, duration):
    """Slide image as the visual, narration audio as the soundtrack."""
    fade = min(0.4, duration / 4)
    run([
        FFMPEG, "-y",
        "-loop", "1", "-i", image_path,
        "-i", narration_audio_path,
        "-t", str(duration),
        "-vf", f"scale={CANON_W}:{CANON_H}:force_original_aspect_ratio=decrease,"
               f"pad={CANON_W}:{CANON_H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={CANON_FPS},"
               f"fade=t=in:st=0:d={fade},fade=t=out:st={duration - fade}:d={fade}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
        "-c:a", "aac", "-ar", "48000", "-ac", "2",
        "-shortest",
        dst,
    ])


def extract_audio(src, dst):
    run([FFMPEG, "-y", "-i", src, "-vn", "-c:a", "aac", "-ar", "48000", "-ac", "2", dst])


def main(topic_dir):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    intro_path = os.path.join(repo_root, "videos", "_intro", "intro.mp4")
    intro_config_path = os.path.join(repo_root, "videos", "_intro", "intro-config.json")
    if not os.path.exists(intro_path):
        sys.exit(
            "videos/_intro/intro.mp4 not found. Run videos/_intro/submit_intro.py "
            "once to render the reusable channel intro before assembling any video."
        )
    with open(intro_config_path) as f:
        intro_duration = json.load(f)["duration_s"]

    config_path = os.path.join(topic_dir, "video-config.json")
    with open(config_path) as f:
        config = json.load(f)

    scenes = config["scenes"]
    for scene in scenes:
        if scene.get("status") != "completed" or not scene.get("video_url"):
            sys.exit(
                f"Scene {scene['id']} ({scene['name']}) is not a completed per-chapter "
                f"render. Run this video's submit.py first."
            )

    scene_images_dir = os.path.join(topic_dir, "scene-images")
    image_paths = [
        os.path.join(scene_images_dir, f"{i+1:02d}.png") for i in range(len(scenes))
    ]
    for p in image_paths:
        if not os.path.exists(p):
            sys.exit(f"Missing chapter card image: {p}")

    tmp = tempfile.mkdtemp(prefix="assemble_")
    try:
        # intro is already normalized at render time (submit_intro.py)
        segments = [(intro_path, intro_duration)]

        for i, (scene, image_path) in enumerate(zip(scenes, image_paths)):
            card_path = os.path.join(tmp, f"card_{i+1:02d}.mp4")
            card_narration_url = scene.get("card_video_url")
            if scene.get("card_script") and scene.get("card_status") == "completed" and card_narration_url:
                print(f"Rendering narrated card {i+1}/{len(scenes)}: {scene['name']}")
                narration_raw = os.path.join(tmp, f"card_narration_{i+1:02d}_raw.mp4")
                narration_audio = os.path.join(tmp, f"card_narration_{i+1:02d}.aac")
                download(card_narration_url, narration_raw)
                extract_audio(narration_raw, narration_audio)
                os.remove(narration_raw)
                card_duration = scene["card_duration_s"]
                render_narrated_card(image_path, narration_audio, card_path, card_duration)
            else:
                print(f"Rendering silent card {i+1}/{len(scenes)}: {scene['name']}")
                card_duration = CARD_DURATION
                render_card(image_path, card_path, card_duration)
            segments.append((card_path, card_duration))

            raw_path = os.path.join(tmp, f"avatar_{i+1:02d}_raw.mp4")
            norm_path = os.path.join(tmp, f"avatar_{i+1:02d}.mp4")
            print(f"Downloading chapter {i+1}/{len(scenes)} avatar clip: {scene['name']}")
            source_url = scene.get("captioned_url") or scene["video_url"]
            download(source_url, raw_path)
            normalize_video(raw_path, norm_path)
            os.remove(raw_path)
            segments.append((norm_path, scene["duration_s"]))

        paths = [p for p, _ in segments]
        durations = [d for _, d in segments]
        n = len(segments)

        inputs = []
        for p in paths:
            inputs += ["-i", p]

        filter_parts = []
        cum = durations[0]
        v_label, a_label = "0:v", "0:a"
        for m in range(1, n):
            offset = cum - m * XFADE_DURATION
            v_out = f"v{m}"
            a_out = f"a{m}"
            filter_parts.append(
                f"[{v_label}][{m}:v]xfade=transition=fade:duration={XFADE_DURATION}:"
                f"offset={offset:.3f}[{v_out}]"
            )
            filter_parts.append(
                f"[{a_label}][{m}:a]acrossfade=d={XFADE_DURATION}[{a_out}]"
            )
            v_label, a_label = v_out, a_out
            cum += durations[m]

        filter_complex = ";".join(filter_parts)
        out_path = os.path.join(topic_dir, "final.mp4")

        print(f"Stitching {n} segments ({len(filter_parts)//2} crossfades)...")
        cmd = [
            FFMPEG, "-y", *inputs,
            "-filter_complex", filter_complex,
            "-map", f"[{v_label}]", "-map", f"[{a_label}]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            out_path,
        ]
        run(cmd)
        print(f"Done — {out_path}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 assemble.py videos/<topic>/")
    main(sys.argv[1].rstrip("/"))
