#!/usr/bin/env python3
"""
Upload a HeyGen-generated video to YouTube.

SETUP (one time):
  1. Go to console.cloud.google.com → APIs & Services → Enable "YouTube Data API v3"
  2. Create OAuth 2.0 credentials (Desktop app) → download client_secret.json
  3. Run:  python3 publish_youtube.py --auth
     Opens a browser, consent, then saves YOUTUBE_REFRESH_TOKEN to .env

USAGE:
  python3 publish_youtube.py --video-id <heygen_video_id> [options]

  Or pipe a local file:
  python3 publish_youtube.py --file /path/to/video.mp4 [options]

ENVIRONMENT VARIABLES:
  MCP_URL                  HeyGen MCP proxy URL
  API_KEY                  HeyGen MCP proxy token
  YOUTUBE_CLIENT_ID        Google OAuth client ID
  YOUTUBE_CLIENT_SECRET    Google OAuth client secret
  YOUTUBE_REFRESH_TOKEN    Stored after first --auth run

DEPENDENCIES:
  pip install google-auth-oauthlib google-api-python-client requests
"""

import argparse
import json
import os
import sys
import tempfile
import time
import urllib.request

# ── YouTube API constants ──────────────────────────────────────────────────────

YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"

# Default video metadata — override via CLI flags
DEFAULT_CATEGORY = "28"        # Science & Technology
DEFAULT_PRIVACY  = "private"   # safe default; change to "public" to go live


# ── HeyGen helpers ─────────────────────────────────────────────────────────────

def _heygen_session():
    mcp_url = os.environ.get("MCP_URL", "").strip()
    api_key  = os.environ.get("API_KEY", "").strip()
    if not mcp_url or not api_key:
        sys.exit("ERROR: MCP_URL and API_KEY env vars required for HeyGen download.")

    session_id = None

    def call(method, params):
        nonlocal session_id
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {api_key}",
        }
        if session_id:
            headers["mcp-session-id"] = session_id
        req = urllib.request.Request(mcp_url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            sid = resp.headers.get("mcp-session-id")
            if sid:
                session_id = sid
            raw = resp.read().decode()
            for line in raw.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            return json.loads(raw)

    call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "publish_youtube", "version": "1.0"},
    })
    return call


def heygen_download(video_id: str, dest_path: str) -> None:
    """Poll until HeyGen video is complete, then download the captioned MP4."""
    call = _heygen_session()

    print(f"Polling HeyGen video {video_id}...")
    for attempt in range(90):
        r = call("tools/call", {"name": "heygen_get_video_status", "arguments": {"video_id": video_id}})
        content = r.get("result", {}).get("content", [{}])
        data_raw = (content[0].get("text", "{}") if isinstance(content, list) and content else "{}")
        data = json.loads(data_raw).get("data", {})
        status = data.get("status", "unknown")
        print(f"  [{attempt * 10}s] {status}")

        if status == "completed":
            # Prefer captioned version; fall back to raw video_url
            url = data.get("captioned_video_url") or data.get("video_url")
            if not url:
                sys.exit("No download URL in completed response.")
            print(f"  Downloading from HeyGen...")
            urllib.request.urlretrieve(url, dest_path)
            size_mb = os.path.getsize(dest_path) / 1_048_576
            print(f"  Saved {size_mb:.1f} MB → {dest_path}")
            return

        if status == "failed":
            sys.exit(f"HeyGen video failed: {data.get('failure_code')} — {data.get('failure_message')}")

        time.sleep(10)

    sys.exit("Timed out waiting for HeyGen video to complete.")


# ── YouTube OAuth ──────────────────────────────────────────────────────────────

def _build_youtube_client():
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit("Run:  pip install google-auth-oauthlib google-api-python-client")

    client_id     = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()

    if not all([client_id, client_secret, refresh_token]):
        sys.exit(
            "Missing YouTube credentials.\n"
            "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.\n"
            "Run  python3 publish_youtube.py --auth  to generate the refresh token."
        )

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=YOUTUBE_SCOPES,
    )
    return build(YOUTUBE_API_SERVICE, YOUTUBE_API_VERSION, credentials=creds)


def run_auth_flow():
    """One-time browser OAuth flow. Prints the refresh token to store in env."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("Run:  pip install google-auth-oauthlib")

    client_id     = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        sys.exit("Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET first.")

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, YOUTUBE_SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n✅  Auth complete. Store this refresh token:\n")
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}\n")
    print("Add it to your .env or environment before running uploads.")


# ── YouTube upload ─────────────────────────────────────────────────────────────

def youtube_upload(
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    category: str = DEFAULT_CATEGORY,
    privacy: str = DEFAULT_PRIVACY,
) -> str:
    """Upload video to YouTube. Returns the YouTube video ID."""
    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
    except ImportError:
        sys.exit("Run:  pip install google-api-python-client")

    youtube = _build_youtube_client()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True, chunksize=10 * 1024 * 1024)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print("Uploading to YouTube...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  {pct}%", end="\r", flush=True)

    yt_id = response["id"]
    print(f"\nUploaded: https://youtu.be/{yt_id}  (privacy: {privacy})")
    return yt_id


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Publish a HeyGen video to YouTube.")
    parser.add_argument("--auth",       action="store_true",  help="Run OAuth flow to get refresh token")
    parser.add_argument("--video-id",   metavar="ID",         help="HeyGen video ID to download and upload")
    parser.add_argument("--file",       metavar="PATH",       help="Local MP4 file to upload (skip HeyGen download)")
    parser.add_argument("--title",      default="",           help="YouTube video title")
    parser.add_argument("--description",default="",           help="YouTube video description")
    parser.add_argument("--tags",       default="",           help="Comma-separated tags")
    parser.add_argument("--privacy",    default=DEFAULT_PRIVACY, choices=["private","unlisted","public"])
    parser.add_argument("--category",   default=DEFAULT_CATEGORY, help="YouTube category ID (default: 28 = Science & Tech)")
    args = parser.parse_args()

    if args.auth:
        run_auth_flow()
        return

    if not args.video_id and not args.file:
        parser.print_help()
        sys.exit(1)

    # Resolve source file
    tmp = None
    if args.file:
        src = args.file
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.close()
        src = tmp.name
        heygen_download(args.video_id, src)

    try:
        yt_id = youtube_upload(
            file_path=src,
            title=args.title or os.path.basename(src),
            description=args.description,
            tags=[t.strip() for t in args.tags.split(",") if t.strip()],
            category=args.category,
            privacy=args.privacy,
        )
        print(f"\nDone → https://youtu.be/{yt_id}")
    finally:
        if tmp:
            os.unlink(src)


if __name__ == "__main__":
    main()
