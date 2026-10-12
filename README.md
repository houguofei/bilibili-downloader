# bilibili-downloader

🇨🇳 [中文文档](README.zh-CN.md)

> Download Bilibili (B站) videos to local files at the highest available quality — by calling
> Bilibili's public web APIs and losslessly muxing the DASH streams with ffmpeg.
> Structured as a **portable skill** that works with WorkBuddy, Claude Code, Cursor, Cline,
> and any agent capable of running Python + ffmpeg.

## About

`bilibili-downloader` is a small, dependency-free toolkit that grabs Bilibili video/audio
streams directly from the site's official player APIs and merges them locally with ffmpeg
(`-c copy`, no re-encoding). It sidesteps the `HTTP 412` anti-crawl blocks that break
`yt-dlp` and `you-get`, and ships as a reusable **skill** usable across multiple AI coding
agents. Anonymous downloads cap at 480P; a login `SESSDATA` cookie unlocks up to 1080P.

## Why not yt-dlp / you-get?

Bilibili returns **HTTP 412 (Precondition Failed)** to common downloaders because of
aggressive anti-crawling. This tool calls the public APIs directly (with a normal browser
`User-Agent` + `Referer`), which is far more reliable.

## Features

- Single video or batch download (CLI args, or a text file with one URL/BVID per line)
- Optional login cookie (`SESSDATA`) to unlock up to 1080P (anonymous is capped at 480P)
- Auto-resolves `cid`, auto-selects the highest-bandwidth H.264 (AVC) video stream
- ffmpeg stream-copy muxing — **no re-encoding, no quality loss**
- Already-downloaded files are verified with `ffprobe` and skipped, so re-runs are safe

## Requirements

- Python 3.7+ (standard library only — no `pip install` needed)
- [ffmpeg](https://ffmpeg.org/) on `PATH` (used only for lossless muxing)

## Install (standalone / manual use)

```bash
git clone https://github.com/houguofei/bilibili-downloader.git
cd bilibili-downloader
# ensure ffmpeg is installed, then run:
python scripts/download_bilibili.py "https://www.bilibili.com/video/BV1vHxXefEEV"
```

## Usage

```bash
# Single video (anonymous → up to 480P)
python scripts/download_bilibili.py "https://www.bilibili.com/video/BV1vHxXefEEV"

# Multiple videos / BVIDs
python scripts/download_bilibili.py BV1vHxXefEEV BV17rtyz3EA9

# Batch from a text file (one URL/BVID per line, # for comments)
python scripts/download_bilibili.py -f urls.txt

# With a login cookie to unlock 1080P
python scripts/download_bilibili.py -c "SESSDATA=xxxx; bili_jct=yyyy" BV1vHxXefEEV

# Via environment variable (keeps the cookie out of shell history)
export BILI_COOKIE="SESSDATA=xxxx; bili_jct=yyyy"
python scripts/download_bilibili.py BV1vHxXefEEV

# Custom output directory
python scripts/download_bilibili.py -d ./downloads BV1vHxXefEEV
```

Output files are named `<sanitized-title>__<BVID>.mp4`.

### Getting a login cookie (for 1080P)

1. Open bilibili.com while logged in, press F12 → Application → Cookies (bilibili.com).
2. Copy `SESSDATA` (and optionally `bili_jct`, `DedeUserID`).
3. Paste it **as-is** — the `%2C` / `%3D` encoding inside `SESSDATA` must NOT be decoded.
4. 1080P60 / 4K require a 大会员 (premium) account's `SESSDATA`.

## Install as an Agent Skill

This repository is already structured as a portable skill:

```
bilibili-downloader/
├── SKILL.md                 # agent instructions (trigger, workflow, quality rules)
├── scripts/download_bilibili.py
├── references/api_reference.md
├── README.md
└── LICENSE
```

Copy the whole folder into your agent's skills directory. Examples:

**WorkBuddy**
```bash
mkdir -p ~/.workbuddy/skills
cp -r bilibili-downloader ~/.workbuddy/skills/bilibili-downloader
```

**Claude Code** (skills directory)
```bash
mkdir -p ~/.claude/skills
cp -r bilibili-downloader ~/.claude/skills/bilibili-downloader
```

**Cursor / Cline / other VS Code-based agents**
Copy the folder into the agent's skills or custom-instructions path (e.g.
`.cursor/skills/`, or your project's agent rules directory), then reference `SKILL.md`
as an instruction source. Exact paths vary by version — consult your agent's docs.

**Any agent (generic)**
Point the agent at `SKILL.md` as a system instruction; the agent can then execute
`scripts/download_bilibili.py` directly. No special plugin system required.

## License

[MIT](LICENSE)
