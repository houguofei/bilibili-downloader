#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili video downloader — fetch the highest available quality via official APIs.

Why this approach (and not yt-dlp / you-get):
  Bilibili now returns HTTP 412 ("Precondition Failed") to common downloaders
  because of aggressive anti-crawling. Calling the public Web APIs directly with
  a normal browser User-Agent + Referer sidesteps that, and lets us grab the raw
  DASH streams and mux them locally with ffmpeg (no re-encoding, no quality loss).

Quality rules (account-dependent, not request-dependent):
  * Without login cookie  -> API caps at 480P.
  * With SESSDATA cookie  -> up to 1080P (30fps). 1080P60 / 4K need 大会员.
  The code always picks the *highest-bandwidth AVC stream* Bilibili returns, so
  it automatically lands on the best quality the current account can access.

Dependencies:
  * Python 3.7+ (standard library only)
  * ffmpeg on PATH (used for stream-copy muxing)

Usage:
  python download_bilibili.py <url-or-bvid> [more urls/bvids ...]
  python download_bilibili.py -f urls.txt
  python download_bilibili.py -c "SESSDATA=xxxx; bili_jct=yyyy" BV1xx
  python download_bilibili.py --dir out --cookie-env BILI_COOKIE BV1xx

Cookie priority:
  1) --cookie / -c argument
  2) environment variable named by --cookie-env (default: BILI_COOKIE)
  3) none (anonymous, 480P cap)
"""

import argparse
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

API_VIEW = "https://api.bilibili.com/x/web-interface/view"
API_PLAYURL = "https://api.bilibili.com/x/player/playurl"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
REFERER = "https://www.bilibili.com"

BV_PATTERN = re.compile(r"BV1[a-zA-Z0-9]{9}")


def build_headers(cookie):
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": REFERER,
        "Origin": REFERER,
    }
    if cookie:
        headers["Cookie"] = cookie
    return headers


def fetch_json(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_bvid(arg):
    """Extract a BVID from a raw BV id or any Bilibili video URL."""
    if BV_PATTERN.fullmatch(arg.strip()):
        return arg.strip()
    m = BV_PATTERN.search(arg)
    if m:
        return m.group(0)
    return None


def get_title_cid(bvid, headers):
    """Return (title, cid) for a given BVID."""
    url = f"{API_VIEW}?bvid={bvid}"
    data = fetch_json(url, headers)
    if data.get("code") != 0:
        raise RuntimeError(f"view API error: {data.get('message')} (code={data.get('code')})")
    d = data["data"]
    return d["title"], d["cid"]


def pick_streams(bvid, cid, headers):
    """
    Fetch playurl with fnval=4048 (DASH). Return (video_stream, audio_stream)
    dicts, or fall back to a single merged URL (durl) when DASH is unavailable.
    """
    url = (f"{API_PLAYURL}?bvid={bvid}&cid={cid}"
           f"&qn=127&fnval=4048&fourk=1")
    data = fetch_json(url, headers)
    if data.get("code") != 0:
        raise RuntimeError(f"playurl API error: {data.get('message')} (code={data.get('code')})")
    d = data["data"]

    if "dash" in d and d["dash"]:
        dash = d["dash"]
        videos = [v for v in dash.get("video", []) if v.get("codecs", "").startswith("avc")]
        if not videos:  # rare: only HEVC/AV1 available
            videos = dash.get("video", [])
        videos.sort(key=lambda v: v.get("bandwidth", 0), reverse=True)
        audios = sorted(dash.get("audio", []),
                        key=lambda a: a.get("bandwidth", 0), reverse=True)
        if not videos or not audios:
            raise RuntimeError("DASH present but no usable streams")
        return videos[0], audios[0], None

    # Fallback: legacy flv/durl response (already muxed, single URL)
    durl = d.get("durl")
    if durl:
        return None, None, durl[0]["url"]
    raise RuntimeError("No DASH or durl stream returned")


def download_file(url, out_path, label, headers, timeout=60, retries=3):
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                total = int(resp.headers.get("Content-Length", 0) or 0)
                got = 0
                with open(out_path, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
                        if total > 0:
                            pct = got * 100 // total
                            sys.stdout.write(
                                f"\r      {label}: {got/1e6:.1f}/{total/1e6:.1f} MB ({pct}%)")
                            sys.stdout.flush()
            sys.stdout.write("\n")
            return True
        except Exception as e:  # noqa: BLE001
            last_err = e
            sys.stdout.write(f"\n      {label} attempt {attempt} failed: {e}\n")
    return False


def download_stream(stream, out_path, label, headers):
    urls = [stream.get("baseUrl")] + list(stream.get("backupUrl", []) or [])
    for i, u in enumerate(urls):
        if download_file(u, out_path, f"{label}#{i+1}", headers):
            return True
    return False


def is_valid_video(path):
    if not os.path.exists(path) or os.path.getsize(path) < 1_000_000:
        return False
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=30)
        dur = out.stdout.strip()
        return bool(dur) and dur.replace(".", "", 1).isdigit() and float(dur) > 5
    except Exception:  # noqa: BLE001
        return False


def merge_streams(video_path, audio_path, out_path):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [ffmpeg, "-y", "-i", video_path, "-i", audio_path,
           "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", out_path]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg mux failed: {res.stderr[-400:]}")


def sanitize(name, maxlen=120):
    name = re.sub(r'[\\/:*?"<>|\n\r\t]', "_", name).strip()
    name = re.sub(r"\s+", " ", name)
    if len(name) > maxlen:
        name = name[:maxlen].rstrip()
    return name or "video"


def process(bvid, args, headers):
    try:
        title, cid = get_title_cid(bvid, headers)
        sys.stdout.write(f"\n=== {bvid} | {title} ===\n")
        fname = f"{sanitize(title)}__{bvid}.mp4"
        out_path = os.path.join(args.dir, fname)

        if os.path.exists(out_path) and is_valid_video(out_path):
            sys.stdout.write(f"[SKIP] valid file exists: {fname}\n")
            return True

        v_stream, a_stream, merged_url = pick_streams(bvid, cid, headers)

        if merged_url:  # legacy durl, already muxed
            sys.stdout.write("  Format: single-stream (legacy)\n")
            if download_file(merged_url, out_path, "video", headers):
                return True
            return False

        sys.stdout.write(
            f"  Quality: {v_stream['width']}x{v_stream['height']} "
            f"{v_stream['codecs']} {v_stream['bandwidth']//1000}kbps | "
            f"audio {a_stream['bandwidth']//1000}kbps\n")

        v_tmp = os.path.join(args.dir, f"_bili_v_{bvid}.m4s")
        a_tmp = os.path.join(args.dir, f"_bili_a_{bvid}.m4s")
        ok = True
        if not download_stream(v_stream, v_tmp, "video", headers):
            ok = False
        if ok and not download_stream(a_stream, a_tmp, "audio", headers):
            ok = False
        if ok:
            merge_streams(v_tmp, a_tmp, out_path)
        for t in (v_tmp, a_tmp):
            try:
                os.remove(t)
            except OSError:
                pass
        if not ok:
            return False
        sz = os.path.getsize(out_path)
        sys.stdout.write(f"  SAVED: {fname} ({sz/1e6:.1f} MB)\n")
        return True
    except Exception as e:  # noqa: BLE001
        sys.stdout.write(f"  ERROR processing {bvid}: {e}\n")
        return False


def read_bvids_from_file(path):
    bvids = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            b = extract_bvid(line)
            if b:
                bvids.append(b)
    return bvids


def main():
    parser = argparse.ArgumentParser(
        description="Download Bilibili videos at highest available quality via official APIs.")
    parser.add_argument("targets", nargs="*", help="Bilibili video URLs or BVIDs")
    parser.add_argument("-f", "--file", help="Text file, one BVID/URL per line")
    parser.add_argument("-c", "--cookie", help="Raw Cookie string (e.g. 'SESSDATA=...; bili_jct=...')")
    parser.add_argument("--cookie-env", default="BILI_COOKIE",
                        help="Env var holding the cookie string (default: BILI_COOKIE)")
    parser.add_argument("-d", "--dir", default=".", help="Output directory (default: current)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress per-chunk progress")
    args = parser.parse_args()

    if not args.targets and not args.file:
        parser.error("provide at least one URL/BVID or -f <file>")

    cookie = args.cookie or os.environ.get(args.cookie_env) or ""
    headers = build_headers(cookie)

    if not (shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")):
        sys.stderr.write("ERROR: ffmpeg not found on PATH. Install ffmpeg first.\n")
        sys.exit(2)

    os.makedirs(args.dir, exist_ok=True)

    bvids = []
    for t in args.targets:
        b = extract_bvid(t)
        if b:
            bvids.append(b)
        else:
            sys.stderr.write(f"WARNING: could not parse BVID from '{t}', skipped\n")
    if args.file:
        bvids.extend(read_bvids_from_file(args.file))

    if not bvids:
        sys.stderr.write("ERROR: no valid BVIDs found.\n")
        sys.exit(1)

    # de-dup preserving order
    seen, uniq = set(), []
    for b in bvids:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    bvids = uniq

    sys.stdout.write(f"Total videos to download: {len(bvids)}\n")
    ok = fail = 0
    for i, b in enumerate(bvids, 1):
        sys.stdout.write(f"\n[{i}/{len(bvids)}] {b}\n")
        if process(b, args, headers):
            ok += 1
        else:
            fail += 1
    sys.stdout.write(f"\n===== DONE: {ok} ok, {fail} failed =====\n")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
