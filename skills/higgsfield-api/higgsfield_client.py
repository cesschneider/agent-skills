#!/usr/bin/env python3
"""Thin client for Higgsfield's official REST API (https://platform.higgsfield.ai).

Auth: `Authorization: Key <HIGGSFIELD_API_KEY>:<HIGGSFIELD_API_SECRET>`
(matches the official `higgsfield-client` Python SDK's `HF_API_KEY`/`HF_API_SECRET`
convention).

Submit a job with `submit(model_id, arguments)` — `arguments` is sent as the
raw JSON body (no `{"input": ...}` wrapper). Then poll with
`get_status(request_id)` / `poll_until_done(request_id)`; the same endpoint
returns the final result payload once status is `completed`.
"""
import mimetypes
import os
import time

import requests

BASE_URL = "https://platform.higgsfield.ai"

DONE_STATUSES = {"completed", "failed", "nsfw", "canceled"}


def _credentials():
    key = os.environ.get("HIGGSFIELD_API_KEY", "").strip()
    secret = os.environ.get("HIGGSFIELD_API_SECRET", "").strip()
    if not key or not secret:
        raise RuntimeError("Set the HIGGSFIELD_API_KEY and HIGGSFIELD_API_SECRET environment variables")
    return key, secret


def _headers():
    key, secret = _credentials()
    return {
        "Authorization": f"Key {key}:{secret}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "higgsfield-client-py/1.0",
    }


def submit(model_id, arguments):
    """Submit a generation job. `arguments` is sent as-is as the JSON body
    (e.g. {"prompt": ..., "aspect_ratio": "16:9", "resolution": "1080p"}).
    Returns the request_id."""
    resp = requests.post(f"{BASE_URL}/{model_id}", headers=_headers(), json=arguments)
    resp.raise_for_status()
    body = resp.json()
    request_id = body.get("request_id")
    if not request_id:
        raise RuntimeError(f"No request_id in response: {body}")
    return request_id


def get_status(request_id):
    """Returns the status payload. Once status is "completed", this same
    payload also contains the result (e.g. images[].url, video.url —
    field names vary by model, inspect on first use)."""
    resp = requests.get(f"{BASE_URL}/requests/{request_id}/status", headers=_headers())
    resp.raise_for_status()
    return resp.json()


def get_result(request_id):
    """Alias for get_status — the status endpoint doubles as the result
    endpoint once the job is "completed"."""
    return get_status(request_id)


def cancel(request_id):
    """Cancel a queued request. Requests already processing cannot be cancelled."""
    resp = requests.post(f"{BASE_URL}/requests/{request_id}/cancel", headers=_headers())
    resp.raise_for_status()
    return resp.json()


def poll_until_done(request_id, interval_s=5, max_attempts=120, on_update=None):
    """Polls get_status until status is "completed", "failed", "nsfw", or
    "canceled". on_update(attempt, status, data), if given, is called after
    every poll."""
    for attempt in range(max_attempts):
        data = get_status(request_id)
        status = data.get("status", "unknown").lower()
        if on_update:
            on_update(attempt, status, data)
        if status == "completed":
            return data
        if status in DONE_STATUSES:
            raise RuntimeError(f"Higgsfield job {request_id} ended with status {status}: {data}")
        time.sleep(interval_s)
    raise TimeoutError(f"request_id={request_id} did not finish after {max_attempts * interval_s}s")


def upload_file(file_path):
    """Upload a local file (e.g. a reference image for image-to-video) and
    return its hosted URL, for use as `image_url` in a model's arguments."""
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    resp = requests.post(
        f"{BASE_URL}/files/generate-upload-url",
        headers=_headers(),
        json={"content_type": mime_type},
    )
    resp.raise_for_status()
    body = resp.json()
    public_url, upload_url = body["public_url"], body["upload_url"]

    with open(file_path, "rb") as f:
        put_resp = requests.put(upload_url, data=f, headers={"Content-Type": mime_type})
    put_resp.raise_for_status()

    return public_url
