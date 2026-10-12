---
name: bilibili-downloader
description: Download Bilibili (B站) videos to local disk at the highest available quality via Bilibili public web APIs and ffmpeg stream-copy muxing. Use when a user shares a bilibili.com video link or asks to download a Bilibili video, especially when yt-dlp or you-get fail with HTTP 412. Supports single videos, batch lists, and login cookies for up to 1080P.
agent_created: true
---

# Bilibili Downloader

## Overview

Download Bilibili videos to local files at the best quality the account can access, using
Bilibili's own Web APIs instead of third-party downloaders. Video and audio are stream-copied
(ffmpeg `-c copy`), so **no re-encoding and no quality loss** occur.

## When to use

- User supplies a `bilibili.com/video/BV...` link (or raw BVID) and asks to download it.
- User wants the highest available resolution preserved (explicitly "不要压缩"/"保持清晰度").
- Batch download of multiple Bilibili videos.
- yt-dlp / you-get fail with HTTP 412 or "Precondition Failed".

## Prerequisites

- **Python 3.7+** (standard library only — no pip install needed).
- **ffmpeg** on PATH (used only for lossless muxing of separated streams).
- Optional: a login **SESSDATA cookie** to unlock 1080P (anonymous tops out at 480P).

## Quick start

Run the bundled script `scripts/download_bilibili.py`.

```bash
# Single video (anonymous → up to 480P)
python scripts/download_bilibili.py "https://www.bilibili.com/video/BV1vHxXefEEV"

# Multiple videos / BVIDs in one command
python scripts/download_bilibili.py BV1vHxXefEEV BV17rtyz3EA9

# Batch from a text file (one URL/BVID per line, # comments allowed)
python scripts/download_bilibili.py -f urls.txt

# With login cookie for up to 1080P (account-dependent)
python scripts/download_bilibili.py -c "SESSDATA=xxxx; bili_jct=yyyy" BV1vHxXefEEV

# Or pass the cookie via environment variable (keeps it out of shell history)
export BILI_COOKIE="SESSDATA=xxxx; bili_jct=yyyy"
python scripts/download_bilibili.py BV1vHxXefEEV

# Custom output directory
python scripts/download_bilibili.py -d ./downloads BV1vHxXefEEV
```

Output files are named `<sanitized-title>__<BVID>.mp4`. Existing valid files are verified with
ffprobe and skipped, so re-running is safe.

## How it works (key points)

1. Parse the **BVID** from any link/argument.
2. `GET /x/web-interface/view?bvid=...` → obtain `cid` and title.
3. `GET /x/player/playurl?bvid=...&cid=...&qn=127&fnval=4048&fourk=1` → DASH streams.
   - `fnval=4048` forces DASH (separate video/audio `.m4s`). Without it, a legacy `durl`
     (already-muxed single URL) may be returned and is handled as a fallback.
   - Stream URLs carry **time-limited signed tokens** — request them fresh per run; never hard-code.
4. Pick the **highest-bandwidth `avc` (H.264) video stream** and highest-bandwidth audio stream.
5. Download both `.m4s` parts (with backup-URL retry).
6. Mux with `ffmpeg -c:v copy -c:a copy -movflags +faststart`.

## Quality rules (account-dependent)

- **No cookie → 480P cap**, even when `qn=127` is requested.
- **With SESSDATA cookie → up to 1080P (30fps)**.
- **1080P60 / 4K → require a 大会员 (premium) account** SESSDATA.
- The script always selects the highest-bandwidth AVC stream returned, automatically landing on
  the best quality the current credentials allow.

## Notes & gotchas

- Prefer direct API calls over yt-dlp/you-get: Bilibili returns HTTP 412 to those downloaders.
- Do **not** use `--cookies-from-browser`; on Windows it fails due to DPAPI encryption. Copy the
  raw cookie string from the browser devtools instead (see `references/api_reference.md`).
- Keep `SESSDATA` exactly as copied (it contains `%2C`/`%3D` encoding — do not decode).
- Space out requests to respect rate limits; verify downloaded files with ffprobe before skipping.

## Resources

### scripts/
- `download_bilibili.py` — main downloader. Supports single/batch, cookies, auto-cid lookup,
  DASH + legacy-durl fallback, ffprobe-verified skip, and ffmpeg stream-copy muxing.

### references/
- `api_reference.md` — API endpoints, DASH field reference, quality (qn) table, cookie
  acquisition steps, error-code table, and the ffmpeg mux command.
