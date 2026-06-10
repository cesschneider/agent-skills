#!/usr/bin/env python3
"""Re-poll HeyGen status for the Higgsfield MCP video using the saved video_id."""

import json, os, sys, time, urllib.request, urllib.error

MCP_URL = os.environ.get("MCP_URL", "").strip()
API_KEY  = os.environ.get("API_KEY",  "").strip()
if not MCP_URL or not API_KEY:
    sys.exit("Set MCP_URL and API_KEY env vars")

SESSION_ID = None

def mcp(method, params):
    global SESSION_ID
    payload = json.dumps({"jsonrpc":"2.0","id":int(time.time()*1000),"method":method,"params":params}).encode()
    headers = {"Content-Type":"application/json","Accept":"application/json, text/event-stream","Authorization":f"Bearer {API_KEY}"}
    if SESSION_ID:
        headers["mcp-session-id"] = SESSION_ID
    req = urllib.request.Request(MCP_URL, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        sid = resp.headers.get("mcp-session-id")
        if sid: SESSION_ID = sid
        raw = resp.read().decode()
        for line in raw.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
        return json.loads(raw)

def tool(name, args):
    r = mcp("tools/call", {"name": name, "arguments": args})
    content = r.get("result", {}).get("content", [{}])
    text = (content[0].get("text","") if isinstance(content, list) and content else "")
    try: return json.loads(text)
    except: return text

config_path = os.path.join(os.path.dirname(__file__), "video-config.json")
with open(config_path) as f:
    config = json.load(f)

video_id = config["video_id"]

for attempt in range(15):
    try:
        mcp("initialize", {"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"check_status","version":"1.0"}})
        break
    except urllib.error.HTTPError as e:
        wait = min(60, 10 * (attempt + 1))
        print(f"initialize failed ({e}), retrying in {wait}s...")
        time.sleep(wait)
else:
    sys.exit("Could not initialize MCP session after retries")

print(f"Polling video_id={video_id}...")
for i in range(120):
    try:
        r = tool("heygen_get_video_status", {"video_id": video_id})
    except urllib.error.HTTPError as e:
        print(f"  [{i*15}s] proxy error ({e}), retrying...")
        time.sleep(15)
        continue
    data = r.get("data", {})
    status = data.get("status", "unknown")
    print(f"  [{i*15}s] {status}")
    if status == "completed":
        config.update({
            "status": "completed",
            "duration_s": data.get("duration"),
            "gif_url": data.get("gif_url",""),
            "captioned_url": data.get("captioned_video_url",""),
        })
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nDone — {data.get('duration')}s")
        print(f"GIF: {data.get('gif_url','')}")
        print(f"URL: {data.get('captioned_video_url','')[:100]}...")
        break
    if status == "failed":
        sys.exit(f"Failed: {data.get('failure_code')} — {data.get('failure_message')}")
    time.sleep(15)
