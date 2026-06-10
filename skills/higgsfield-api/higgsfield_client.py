#!/usr/bin/env python3
"""Thin client for Higgsfield's official REST API (https://platform.higgsfield.ai).

Auth follows the fal.ai-style queue convention Higgsfield's own SDKs use:
`Authorization: Key <HIGGSFIELD_API_KEY>:<HIGGSFIELD_API_SECRET>`.

Submit a job with `submit(model_id, input)`, then poll with
`get_status(request_id)` / `poll_until_done(request_id)`, and fetch the
final payload with `get_result(request_id)`.
"""
import os
import time
import requests

BASE_URL = "https://platform.higgsfield.ai"


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
    }


def submit(model_id, input_payload):
    """Submit a generation job. Returns the request_id."""
    resp = requests.post(f"{BASE_URL}/{model_id}", headers=_headers(), json={"input": input_payload})
    resp.raise_for_status()
    body = resp.json()
    request_id = body.get("request_id") or body.get("id")
    if not request_id:
        raise RuntimeError(f"No request_id in response: {body}")
    return request_id


def get_status(model_id, request_id):
    resp = requests.get(f"{BASE_URL}/{model_id}/requests/{request_id}/status", headers=_headers())
    resp.raise_for_status()
    return resp.json()


def get_result(model_id, request_id):
    resp = requests.get(f"{BASE_URL}/{model_id}/requests/{request_id}", headers=_headers())
    resp.raise_for_status()
    return resp.json()


def poll_until_done(model_id, request_id, interval_s=5, max_attempts=120, on_update=None):
    for attempt in range(max_attempts):
        data = get_status(model_id, request_id)
        status = data.get("status", "unknown").upper()
        if on_update:
            on_update(attempt, status, data)
        if status == "COMPLETED":
            return get_result(model_id, request_id)
        if status in ("FAILED", "NSFW", "CANCELLED"):
            raise RuntimeError(f"Higgsfield job {request_id} ended with status {status}: {data}")
        time.sleep(interval_s)
    raise TimeoutError(f"request_id={request_id} did not finish after {max_attempts * interval_s}s")


def upload_file(file_path):
    """Upload a local file (e.g. a reference image for image-to-video) and return its hosted URL."""
    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/storage/upload",
            headers={"Authorization": _headers()["Authorization"]},
            files={"file": f},
        )
    resp.raise_for_status()
    body = resp.json()
    url = body.get("url") or body.get("file_url")
    if not url:
        raise RuntimeError(f"No URL in upload response: {body}")
    return url
