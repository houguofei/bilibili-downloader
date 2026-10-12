# Bilibili Download — API & Reference

## Core endpoints

### 1. Get video metadata (title + cid)
```
GET https://api.bilibili.com/x/web-interface/view?bvid=<BV1xxxxxxxxx>
Headers: User-Agent (browser), Referer: https://www.bilibili.com
Response: { "code":0, "data": { "title": "...", "cid": <int>, "aid": <int>, ... } }
```
- `cid` is the page id required by the playurl API. A video with multiple parts has multiple cids.

### 2. Get playable streams (DASH)
```
GET https://api.bilibili.com/x/player/playurl?bvid=<BV>&cid=<CID>&qn=127&fnval=4048&fourk=1
Headers: same + optional Cookie (SESSDATA)
Response: { "code":0, "data": { "quality":<int>, "accept_quality":[...], "dash": {...}, "durl":[...] } }
```
- `qn=127` requests the highest quality; the server still returns only what the account is entitled to.
- `fnval=4048` forces DASH format (separate video/audio streams). Without it, `durl` (legacy, already-muxed) may be returned instead.
- With `Cookie: SESSDATA=...` the account is treated as logged in → up to 1080P.

## DASH stream fields
`data.dash.video[]` and `data.dash.audio[]` are arrays of:
```
{ "id":<int>, "baseUrl":"https://...m4s?...", "backupUrl":[...],
  "codecs":"avc1.640033", "width":1920, "height":1080,
  "frame_rate":"30.000", "bandwidth":<int> }
```
- `baseUrl` and `backupUrl` carry **time-limited signed tokens** (usually expire in a few hours). Always request fresh — never hard-code.
- Pick the **highest `bandwidth`** entry. Prefer `codecs` starting with `avc` (H.264) for maximum player compatibility; HEVC/AV1 (`hvc1`/`av01`) decode on fewer devices.
- Video and audio come as **separate `.m4s` files**; mux them with ffmpeg (`-c:v copy -c:a copy`).

## Quality (qn) levels
| qn | label |
|----|-------|
| 116 | 高清 1080P60 (needs 大会员) |
| 80  | 高清 1080P |
| 64  | 高清 720P |
| 32  | 清晰 480P |
| 16  | 流畅 360P |

Anonymous (no cookie) tops out at 480P even when `qn=127` is requested.

## Obtaining a login cookie
1. Open https://www.bilibili.com in a browser while logged in.
2. Press F12 → Network / Application → Cookies for `bilibili.com`.
3. Copy at least `SESSDATA` (and optionally `bili_jct`, `DedeUserID`).
4. Pass as `Cookie` header: `SESSDATA=xxxx; bili_jct=yyyy; DedeUserID=zzzz`.
   - In this skill, prefer `-c "..."` or the `BILI_COOKIE` env var.
- NOTE: `SESSDATA` contains `%2C`/`%3D` style URL-encoding — keep it **as-is**, do not decode.
- 1080P60 / 4K require a 大会员 (premium) account's SESSDATA.

## Common error codes
| code | meaning | action |
|------|---------|--------|
| 0    | success | — |
| -404 | video/cid not found | check BVID |
| -412 | request blocked (anti-crawl) | ensure browser UA + Referer; do NOT hit too fast |
| -101 | not logged in (quality locked) | add SESSDATA cookie |
| -104 | too many requests / forbidden region | retry later / use cookie |

## ffmpeg mux command
```
ffmpeg -y -i video.m4s -i audio.m4s -c:v copy -c:a copy -movflags +faststart out.mp4
```
Stream copy (`-c copy`) avoids re-encoding, preserving original quality.

## Notes / gotchas
- Browser cookie extraction tools (`--cookies-from-browser`) often fail on Windows due to DPAPI encryption incompatibility; prefer copying the raw cookie string manually.
- yt-dlp / you-get frequently get HTTP 412 from Bilibili; direct API calls are more reliable.
- Respect Bilibili's rate limits: space out requests, avoid hammering the same video.
- For personal/backup use only; comply with Bilibili ToS and copyright.
