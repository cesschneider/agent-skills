#!/usr/bin/env python3
"""Thin client for HeyGen's native REST API (https://api.heygen.com).

No MCP server, proxy, or gateway involved — every call goes straight to
HeyGen over HTTPS, authenticated with the `X-Api-Key` header.

Usage:
    from heygen_client import (
        get_remaining_quota, list_avatars, list_voices,
        upload_asset, generate_video_v2, get_video_status, poll_until_done,
    )

Requires the HEYGEN_API_KEY environment variable.
"""

import os
import time

import requests

BASE_URL = "https://api.heygen.com"


def _api_key():
    api_key = os.environ.get("HEYGEN_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Set the HEYGEN_API_KEY environment variable")
    return api_key


def _headers():
    return {
        "X-Api-Key": _api_key(),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _unwrap(resp):
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(f"HeyGen API error: {body['error']}")
    return body["data"]


def get_remaining_quota():
    """Returns {"remaining_quota": <credits>, "details": {...}}."""
    resp = requests.get(f"{BASE_URL}/v2/user/remaining_quota", headers=_headers())
    return _unwrap(resp)


def list_avatars():
    """Returns the list of available avatars (stock + custom)."""
    resp = requests.get(f"{BASE_URL}/v2/avatars", headers=_headers())
    return _unwrap(resp)["avatars"]


def list_voices():
    """Returns the list of available voices."""
    resp = requests.get(f"{BASE_URL}/v2/voices", headers=_headers())
    return _unwrap(resp)["voices"]


def upload_asset(file_path):
    """Uploads an image/video/audio/PDF file (max 32MB) and returns
    {"asset_id", "url", "mime_type", "size_bytes"}.

    Reference uploaded images as background.image_url (or asset_id, where
    supported) in generate_video_v2 video_inputs.
    """
    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/v3/assets",
            headers={"X-Api-Key": _api_key()},
            files={"file": f},
        )
    return _unwrap(resp)


def generate_video_v2(title, video_inputs, dimension, caption=True, test=False):
    """Submits a multi-scene (1-50 inputs) video. Returns the video_id."""
    payload = {
        "title": title,
        "video_inputs": video_inputs,
        "dimension": dimension,
        "caption": caption,
    }
    if test:
        payload["test"] = True
    resp = requests.post(f"{BASE_URL}/v2/video/generate", headers=_headers(), json=payload)
    return _unwrap(resp)["video_id"]


def get_video_status(video_id):
    """Returns the status payload: status, video_url, gif_url,
    video_url_caption, duration, thumbnail_url, error/failure_code/
    failure_message (when failed)."""
    resp = requests.get(
        f"{BASE_URL}/v1/video_status.get",
        headers=_headers(),
        params={"video_id": video_id},
    )
    return _unwrap(resp)


def poll_until_done(video_id, interval_s=15, max_attempts=120, on_update=None):
    """Polls get_video_status until status is 'completed' or 'failed'.

    on_update(attempt, status, data), if given, is called after every poll —
    useful for printing progress.
    """
    for attempt in range(max_attempts):
        data = get_video_status(video_id)
        status = data.get("status", "unknown")
        if on_update:
            on_update(attempt, status, data)
        if status == "completed":
            return data
        if status == "failed":
            raise RuntimeError(
                f"HeyGen video failed: {data.get('error') or data.get('failure_message')}"
            )
        time.sleep(interval_s)
    raise TimeoutError(f"video_id={video_id} did not finish after {max_attempts * interval_s}s")
