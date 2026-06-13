# Connecting Claude Code to Social Media Platforms

This guide is a plan for giving Claude Code (or any MCP-capable agent) read and, where
possible, write access to YouTube, X (Twitter), LinkedIn, Instagram, Medium, and
Substack — so skills and agents can pull posts, comments, and profile data, and act on
your behalf.

The connectivity layer is the **Model Context Protocol (MCP)**. Each platform gets its
own MCP server that holds credentials and exposes a small set of tools (`list_posts`,
`get_comments`, `post_update`, ...). Claude Code calls those tools directly — no
scraping, no browser automation.

Two skills already in this repo apply directly once the connections exist:

- [context-engineering](../skills/context-engineering/SKILL.md) — registering and scoping MCP servers
- [security-and-hardening](../skills/security-and-hardening/SKILL.md) — secrets management and the three-tier boundary system (Always / Ask First / Never)

## Reality Check: What Each Platform Actually Allows

Before configuring anything, understand the constraints — they vary a lot by platform
and drive how much automation is realistic. Verify against current docs/ToS before
relying on this table; platform APIs change frequently.

| Platform | Read your own posts/profile | Read others' posts/comments | Write (post/comment) | Official API | Auth |
|---|---|---|---|---|---|
| YouTube | Yes | Yes (public videos/comments) | Yes (comments, video metadata) | YouTube Data API v3 | API key (public read) + OAuth 2.0 (write/private) |
| X (Twitter) | Yes | Limited on Free tier; full on Basic+ paid tiers | Yes | X API v2 | OAuth 2.0 (user context) or App-only Bearer token |
| LinkedIn | Yes (own profile/org page) | No general feed/search access without Partner Program approval | Share posts via Member/Org Social API (basic apps) | LinkedIn REST API | OAuth 2.0 (3-legged) |
| Instagram | Yes, but **only Business/Creator accounts** linked to a Facebook Page | No (third-party feed reading is not available) | Yes, on your own Business/Creator account | Instagram Graph API (via Meta for Developers) | OAuth 2.0 (Facebook Login), long-lived tokens |
| Medium | Limited — public API for new integrations was discontinued; legacy Integration Tokens may still work for existing accounts | RSS only (`/feed/@username`) | Legacy token-based publishing only, if you still hold a token | Mostly deprecated | Legacy Integration Token, or none |
| Substack | RSS feed (`/feed`) for your own publication | RSS feed for any public publication | No official API | None (RSS only) | None |

**Takeaway:** YouTube and X are the most agent-friendly for two-way interaction.
LinkedIn and Instagram are effectively limited to managing *your own* account/page, with
real API access gated behind Meta/LinkedIn app review. Medium and Substack are
read-only via RSS — treat them as content sources, not interactive surfaces.

## The Plan

1. **Scope the request per platform.** For each network, decide whether you need
   read-only monitoring, posting on your own behalf, or both. Don't request write
   scopes you won't use — narrower scopes are easier to get approved and safer to hold.
2. **Register a developer app per platform** and obtain credentials (steps below).
3. **Store credentials outside the repo** — environment variables loaded from your
   shell profile or a local `.env` file that is git-ignored. Never put tokens in
   `.mcp.json`, skill files, or commits.
4. **Stand up one MCP server per platform** (or a single multi-tool server if you
   prefer), starting with read-only tools. Add write tools only after read access is
   working and reviewed.
5. **Register the servers in `.mcp.json`** (project-level) or `~/.claude.json`
   (user-level, for servers you want available across all projects).
6. **Smoke-test each tool manually** — list a few posts/comments — before wiring it
   into any skill or agent workflow.
7. **Document available tools in `CLAUDE.md`**, including rate limits and which write
   actions require explicit confirmation.
8. **Apply security-and-hardening boundaries**: read tools are "Always" (safe,
   reversible); write tools (post, comment, reply, delete) are "Ask First" — the agent
   proposes the content and waits for your go-ahead before calling the tool.

## Credential Storage

```bash
# ~/.env.social (chmod 600, NOT committed)
YOUTUBE_API_KEY=...
YOUTUBE_OAUTH_CLIENT_ID=...
YOUTUBE_OAUTH_CLIENT_SECRET=...
YOUTUBE_OAUTH_REFRESH_TOKEN=...

X_BEARER_TOKEN=...
X_CLIENT_ID=...
X_CLIENT_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...

LINKEDIN_CLIENT_ID=...
LINKEDIN_CLIENT_SECRET=...
LINKEDIN_ACCESS_TOKEN=...

META_APP_ID=...
META_APP_SECRET=...
IG_BUSINESS_ACCOUNT_ID=...
IG_ACCESS_TOKEN=...

MEDIUM_INTEGRATION_TOKEN=...   # legacy, optional
```

Add `.env.social` (or wherever you keep this) to `.gitignore` at the user/global level
— never the repo's tracked `.gitignore` if it could ever apply to a different file.
Source it from your shell profile (`source ~/.env.social`) so `.mcp.json` can reference
the variables without containing secrets itself.

## Platform Setup

### YouTube — YouTube Data API v3

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **YouTube Data API v3** for that project.
3. For public read-only access (search videos, list comments on public videos):
   create an **API key** and restrict it to the YouTube Data API.
4. For access to your own channel (private playlists, posting comments, managing
   videos): create an **OAuth 2.0 Client ID** (Desktop app type), run the OAuth consent
   flow once to obtain a refresh token, and store the refresh token.
5. Scopes you'll typically need:
   - `https://www.googleapis.com/auth/youtube.readonly` — read channel/video/comment data
   - `https://www.googleapis.com/auth/youtube.force-ssl` — post/reply to comments
6. MCP tools to expose: `search_videos`, `get_video_details`, `list_comments`,
   `reply_to_comment`, `get_channel_stats`.

### X (Twitter) — X API v2

1. Apply for a developer account at [developer.x.com](https://developer.x.com).
2. Create a Project and an App. Note the tier — the **Free** tier is heavily
   restricted for reading (it's effectively post-only); reading timelines, mentions,
   and search at meaningful volume requires the **Basic** tier or higher.
3. Generate:
   - A **Bearer Token** for app-only, read-only calls against public data (within tier limits).
   - **OAuth 2.0** client credentials + user access/refresh tokens if the agent needs
     to act as your account (post tweets, like, reply).
4. MCP tools to expose: `search_tweets`, `get_user_timeline`, `get_mentions`,
   `post_tweet`, `reply_to_tweet`.
5. Respect rate limits aggressively — cache results and back off on 429s rather than
   retrying immediately.

### LinkedIn — LinkedIn REST API

1. Create an app at [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps).
2. Request the **Sign In with LinkedIn using OpenID Connect** product (for basic
   profile access) and, if you plan to post, the **Share on LinkedIn** /
   Community Management API product. Broader access to feeds, organization analytics,
   or other members' content requires LinkedIn's **Partner Program**, which has an
   approval process — most individual developer apps will not get this.
3. Run the OAuth 2.0 3-legged flow to get an access token scoped to `openid profile
   email w_member_social` (or your org's equivalent for organization pages).
4. MCP tools to expose: `get_my_profile`, `post_share`, `get_org_page_posts` (if you
   manage a Company Page with appropriate access).
5. Be explicit in `CLAUDE.md` that LinkedIn access is limited to your own
   profile/organization — agents should not assume they can read arbitrary feeds.

### Instagram — Instagram Graph API (via Meta)

1. Convert the target Instagram account to a **Business** or **Creator** account and
   link it to a Facebook Page (required — personal accounts are not supported by the
   Graph API).
2. Create an app in [Meta for Developers](https://developers.facebook.com/), add the
   **Instagram Graph API** product.
3. Generate a long-lived access token via Facebook Login for the linked Page/IG
   account, scoped to permissions like `instagram_basic`,
   `instagram_manage_comments`, `pages_show_list`.
4. Advanced permissions (beyond basic read of your own content) require **App Review**
   from Meta — plan for this if you need more than your own account's media/comments.
5. MCP tools to expose: `get_my_media`, `get_media_comments`, `reply_to_comment`,
   `get_account_insights`.
6. Scope expectations: this gives you access to *your own* Instagram Business account
   — not a general way to read other users' posts or profiles.

### Medium

Medium discontinued issuing new API Integration Tokens; if you registered one before
the cutoff it may still work for publishing, but treat this as legacy and don't build
new workflows around it.

For reading, use the public RSS feed — no auth required:

- A user's posts: `https://medium.com/feed/@<username>`
- A publication: `https://medium.com/feed/<publication-slug>`

MCP tool to expose: `get_medium_feed(url)` — a thin RSS fetch-and-parse tool. No write
capability should be assumed.

### Substack

No official API. For reading, every Substack publication exposes an RSS feed at
`https://<publication>.substack.com/feed` (public posts only — paywalled content is
excluded). There is no supported way to read comments or post programmatically;
don't build scraping-based write paths, as that violates Substack's terms.

MCP tool to expose: `get_substack_feed(publication)` — RSS fetch-and-parse, same shape
as the Medium tool. Read-only.

## MCP Server Architecture

Build one small MCP server per platform (Node/TypeScript with
`@modelcontextprotocol/sdk`, or Python with `mcp`), each wrapping that platform's
official SDK/REST client. Keep RSS-only platforms (Medium, Substack) as a single
shared "feeds" server since they need no auth.

Minimal shape for the YouTube server (`servers/youtube/index.ts`):

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { google } from "googleapis";

const youtube = google.youtube({
  version: "v3",
  auth: process.env.YOUTUBE_API_KEY, // read-only tools
});

const server = new Server({ name: "youtube", version: "1.0.0" });

server.tool("list_comments", { videoId: "string" }, async ({ videoId }) => {
  const res = await youtube.commentThreads.list({
    part: ["snippet"],
    videoId,
    maxResults: 20,
  });
  return res.data.items;
});

// Write tools (reply_to_comment, etc.) use a separate OAuth2 client built from
// YOUTUBE_OAUTH_* env vars and a stored refresh token.

await server.connect(new StdioServerTransport());
```

Apply the same pattern for X (`twitter-api-v2` package), LinkedIn, and Instagram
(direct `fetch` calls against their REST endpoints with the stored access token).

## Wiring into `.mcp.json`

```json
{
  "mcpServers": {
    "youtube": {
      "command": "node",
      "args": ["servers/youtube/index.js"],
      "env": {
        "YOUTUBE_API_KEY": "${YOUTUBE_API_KEY}",
        "YOUTUBE_OAUTH_CLIENT_ID": "${YOUTUBE_OAUTH_CLIENT_ID}",
        "YOUTUBE_OAUTH_CLIENT_SECRET": "${YOUTUBE_OAUTH_CLIENT_SECRET}",
        "YOUTUBE_OAUTH_REFRESH_TOKEN": "${YOUTUBE_OAUTH_REFRESH_TOKEN}"
      }
    },
    "x-twitter": {
      "command": "node",
      "args": ["servers/x/index.js"],
      "env": {
        "X_BEARER_TOKEN": "${X_BEARER_TOKEN}",
        "X_ACCESS_TOKEN": "${X_ACCESS_TOKEN}",
        "X_ACCESS_TOKEN_SECRET": "${X_ACCESS_TOKEN_SECRET}"
      }
    },
    "linkedin": {
      "command": "node",
      "args": ["servers/linkedin/index.js"],
      "env": { "LINKEDIN_ACCESS_TOKEN": "${LINKEDIN_ACCESS_TOKEN}" }
    },
    "instagram": {
      "command": "node",
      "args": ["servers/instagram/index.js"],
      "env": {
        "IG_ACCESS_TOKEN": "${IG_ACCESS_TOKEN}",
        "IG_BUSINESS_ACCOUNT_ID": "${IG_BUSINESS_ACCOUNT_ID}"
      }
    },
    "feeds": {
      "command": "node",
      "args": ["servers/feeds/index.js"]
    }
  }
}
```

The `${VAR}` syntax pulls from your environment at launch — keep the actual values in
`~/.env.social` (sourced by your shell) and never inline them here. For servers you
want everywhere (not just this project), register the same entries in `~/.claude.json`
instead of a project-level `.mcp.json`.

## Using These Connections from Skills and Agents

Once the servers are registered, Claude Code sees their tools automatically. Add a
short section to the project's `CLAUDE.md` so agents know what's available and what
requires confirmation:

```markdown
## Social Media Tools (MCP)

Read tools (safe, no confirmation needed):
- youtube: search_videos, get_video_details, list_comments, get_channel_stats
- x-twitter: search_tweets, get_user_timeline, get_mentions
- linkedin: get_my_profile
- instagram: get_my_media, get_media_comments, get_account_insights
- feeds: get_medium_feed, get_substack_feed (RSS, read-only)

Write tools (ALWAYS draft content and wait for explicit approval before calling):
- youtube: reply_to_comment
- x-twitter: post_tweet, reply_to_tweet
- linkedin: post_share
- instagram: reply_to_comment

Never call a write tool without showing the exact content to be posted first.
```

This mirrors the three-tier boundary system from
[security-and-hardening](../skills/security-and-hardening/SKILL.md): read operations
are "Always," write operations are "Ask First," and there is no "Never" tier here
because no tool should perform irreversible actions like account deletion.

A typical workflow once this is in place:

1. **Monitoring**: "Summarize comments on my last 3 YouTube videos and flag anything
   needing a response" — agent calls `list_comments` for each video, no confirmation needed.
2. **Cross-platform digest**: "Pull my latest Substack post and the top reactions to my
   last 5 tweets" — agent calls `get_substack_feed` and `get_user_timeline` /
   `search_tweets`.
3. **Drafting + posting**: "Draft a tweet announcing the new release and post it" —
   agent drafts the text, shows it to you, and only calls `post_tweet` after you confirm.

## Compliance, Rate Limits, and Caching

- **Respect each platform's ToS.** Don't build scraping fallbacks for platforms without
  an API (Substack, LinkedIn feeds, Instagram third-party feeds) — use RSS where
  offered and otherwise treat the data as unavailable.
- **Cache reads.** Most of these APIs have tight rate limits (especially X's lower
  tiers and Instagram's Graph API). Have MCP servers cache list/get responses for a
  few minutes to avoid burning quota on repeated agent queries.
- **Back off on errors.** Treat 429/rate-limit responses as a signal to wait, not retry
  immediately — surface the wait time to the agent so it doesn't loop.
- **Rotate and scope tokens.** Use the narrowest scopes that satisfy your use case, and
  rotate long-lived tokens (Instagram/Facebook tokens expire ~60 days and need refresh).

## Verification Checklist

- [ ] Credentials for each target platform are stored outside the repo and loaded via
      environment variables only
- [ ] `.mcp.json` (or `~/.claude.json`) references env vars, contains no literal secrets
- [ ] Each MCP server's read tools tested manually with real responses
- [ ] Write tools (if any) tested in a sandbox/test account before pointing at a real account
- [ ] `CLAUDE.md` documents available tools and which require confirmation before use
- [ ] Rate-limit/caching behavior confirmed for at least one read-heavy platform (X or Instagram)
