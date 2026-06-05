#!/usr/bin/env python3
"""
Re-submit OpenHuman video with diagram image backgrounds.

Requires MCP_URL and API_KEY environment variables.
Run when the Replit MCP proxy is live.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error


def trim(s):
    return s.strip()


MCP_URL = trim(os.environ.get("MCP_URL", ""))
API_KEY = trim(os.environ.get("API_KEY", ""))

if not MCP_URL or not API_KEY:
    sys.exit("ERROR: MCP_URL and API_KEY environment variables required")


def mcp_request(method, params, session_id=None):
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": method,
        "params": params,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {API_KEY}",
    }
    if session_id:
        headers["mcp-session-id"] = session_id

    req = urllib.request.Request(MCP_URL, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            new_session = resp.headers.get("mcp-session-id")
            raw = resp.read().decode()
            # SSE: extract data: lines
            for line in raw.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip()), new_session or session_id
            # Plain JSON fallback
            return json.loads(raw), new_session or session_id
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body[:200]}")


def mcp_init():
    print("Initializing MCP session...")
    result, session_id = mcp_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "submit.py", "version": "1.0"},
    })
    print(f"  session_id: {session_id}")
    return session_id


def call_tool(session_id, tool_name, tool_args):
    result, _ = mcp_request("tools/call", {
        "name": tool_name,
        "arguments": tool_args,
    }, session_id=session_id)
    if "error" in result:
        raise RuntimeError(f"{tool_name} error: {result['error']}")
    content = result.get("result", {}).get("content", [{}])
    if isinstance(content, list) and content:
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return result.get("result")


def upload_asset(session_id, url, label):
    print(f"  Uploading {label}...")
    resp = call_tool(session_id, "heygen_upload_asset", {
        "url": url,
        "type": "image",
    })
    # Response shape: {"code": 200, "data": {"asset_id": "...", "url": "..."}}
    if isinstance(resp, dict):
        asset_id = (resp.get("data") or {}).get("asset_id") or resp.get("asset_id")
        if asset_id:
            print(f"    asset_id: {asset_id}")
            return asset_id
    raise RuntimeError(f"Unexpected upload response: {resp}")


def poll_video(session_id, video_id, max_minutes=15):
    print(f"\nPolling video {video_id}...")
    for i in range(max_minutes * 6):
        time.sleep(10)
        resp = call_tool(session_id, "heygen_get_video_status", {"video_id": video_id})
        status = (resp.get("data") or {}).get("status") or resp.get("status", "unknown")
        print(f"  [{i*10}s] status: {status}")
        if status == "completed":
            url = (resp.get("data") or {}).get("video_url") or resp.get("video_url")
            print(f"  DONE — download URL: {url}")
            return url
        if status == "failed":
            code = (resp.get("data") or {}).get("failure_code") or ""
            msg = (resp.get("data") or {}).get("failure_message") or ""
            raise RuntimeError(f"Video failed: {code} — {msg}")
    raise TimeoutError(f"Video not complete after {max_minutes} min")


def main():
    config_path = os.path.join(os.path.dirname(__file__), "video-config.json")
    with open(config_path) as f:
        config = json.load(f)

    session_id = mcp_init()

    # Check quota first
    quota = call_tool(session_id, "heygen_get_remaining_quota", {})
    print(f"Remaining quota: {quota}")

    # Upload all 8 diagram images
    print("\n--- Uploading diagram assets ---")
    asset_ids = []
    for scene in config["scenes"]:
        asset_id = upload_asset(session_id, scene["diagram_url"], scene["name"])
        asset_ids.append(asset_id)
        time.sleep(1)  # gentle rate-limit

    print(f"\nAll {len(asset_ids)} assets uploaded.")

    # Build v2 multi-scene payload
    avatar_id = config["avatar_id"]
    # Use Cesar's cloned voice from production config
    voice_id = "c0a044792fc64b3fa7dfc0700da93016"

    video_inputs = []
    for scene, asset_id in zip(config["scenes"], asset_ids):
        video_inputs.append({
            "character": {
                "type": "talking_photo",
                "talking_photo_id": avatar_id,
            },
            "voice": {
                "type": "text",
                "input_text": scene["script"],
                "voice_id": voice_id,
            },
            "background": {
                "type": "image",
                "value": asset_id,
            },
        })

    payload = {
        "video_inputs": video_inputs,
        "aspect_ratio": "16:9",
        "caption": True,
        "title": config["title"],
    }

    print("\n--- Submitting video ---")
    resp = call_tool(session_id, "heygen_generate_video_v2", payload)
    video_id = (resp.get("data") or {}).get("video_id") or resp.get("video_id")
    if not video_id:
        raise RuntimeError(f"No video_id in response: {resp}")
    print(f"Submitted. video_id: {video_id}")

    # Save to config
    config["resubmitted_video_id"] = video_id
    config["asset_ids"] = asset_ids
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print("Config updated with video_id and asset_ids.")

    # Poll until done
    video_url = poll_video(session_id, video_id)
    config["resubmitted_video_url"] = video_url
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nFINAL URL: {video_url}")


if __name__ == "__main__":
    main()
