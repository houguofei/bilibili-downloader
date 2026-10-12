# bilibili-downloader

通过 B站官方 Web API 直接获取 DASH 视频 / 音频流，并用 ffmpeg 无损合并，将 B站视频下载到本地，保持最高可用画质。

Download Bilibili videos to local files at the highest available quality by calling Bilibili's public web APIs and muxing the DASH streams with ffmpeg (no re-encoding).

## 为什么不用 yt-dlp / you-get

B站对常见下载器返回 **HTTP 412**（反爬）。本工具直接调用公开 API（配合浏览器 UA + Referer），规避该限制，稳定可取流。

## 功能

- 单视频 / 批量下载（命令行参数，或每行一个 URL/BVID 的文本文件）
- 支持登录 Cookie（`SESSDATA`）解锁最高 **1080P**（匿名仅 480P）
- 自动获取 `cid`、自动选择最高带宽的 H.264 (AVC) 视频流
- ffmpeg 流拷贝（`-c copy`）合并，无重编码、无画质损失
- 已存在文件经 `ffprobe` 校验后跳过，可安全重复运行

## 依赖

- Python 3.7+（仅标准库，无需 `pip install`）
- [ffmpeg](https://ffmpeg.org/)（需在 `PATH` 中，仅用于无损封装）

## 用法

```bash
# 单个视频（匿名 → 最高 480P）
python scripts/download_bilibili.py "https://www.bilibili.com/video/BV1vHxXefEEV"

# 多个视频 / BVID
python scripts/download_bilibili.py BV1vHxXefEEV BV17rtyz3EA9

# 从文本文件批量（每行一个，# 开头为注释）
python scripts/download_bilibili.py -f urls.txt

# 带登录 Cookie 解锁 1080P
python scripts/download_bilibili.py -c "SESSDATA=xxxx; bili_jct=yyyy" BV1vHxXefEEV

# 通过环境变量传入 Cookie（避免写入 shell 历史）
export BILI_COOKIE="SESSDATA=xxxx; bili_jct=yyyy"
python scripts/download_bilibili.py BV1vHxXefEEV

# 指定输出目录
python scripts/download_bilibili.py -d ./downloads BV1vHxXefEEV
```

输出文件命名：`<标题>__<BVID>.mp4`。

### 获取登录 Cookie

1. 浏览器登录 bilibili.com 后按 F12 → Application → Cookies（bilibili.com）
2. 复制 `SESSDATA`（以及可选的 `bili_jct`、`DedeUserID`）
3. 原样粘贴，`SESSDATA` 中的 `%2C` / `%3D` 编码**不要解码**
4. 1080P60 / 4K 需要大会员账号的 `SESSDATA`

## 作为 WorkBuddy Skill 使用

将本仓库内容放入 `~/.workbuddy/skills/bilibili-downloader/`（保持 `SKILL.md`、`scripts/`、`references/` 结构），即可被 WorkBuddy 自动识别加载。

## 许可证

[MIT](LICENSE)
