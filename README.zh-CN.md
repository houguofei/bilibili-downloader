# bilibili-downloader

🌐 [English](README.md)

> 通过 B站官方 Web API 直接获取 DASH 视频 / 音频流，并用 ffmpeg 无损合并，将 B站视频下载到本地，保持最高可用画质。
> 本仓库是一个**可移植的 Skill**，适用于 WorkBuddy、Claude Code、Cursor、Cline 以及任何能运行 Python + ffmpeg 的 agent。

## 关于

`bilibili-downloader` 是一个零依赖的小型工具集，直接从 B站播放器官方 API 抓取视频 / 音频流，并在本地用 ffmpeg 合并（`-c copy`，无重编码）。它绕过了 `yt-dlp`、`you-get` 经常遇到的 `HTTP 412` 反爬限制，并作为一个可复用的 **Skill** 供多种 AI 编程 agent 使用。匿名下载最高 480P；登录 `SESSDATA` Cookie 可解锁最高 1080P。

## 为什么不用 yt-dlp / you-get

B站对常见下载器返回 **HTTP 412（Precondition Failed）** 反爬。本工具直接调用公开 API（配合常规浏览器 `User-Agent` + `Referer`），稳定得多。

## 功能

- 单视频或批量下载（命令行参数，或每行一个 URL/BVID 的文本文件）
- 可选登录 Cookie（`SESSDATA`）解锁最高 1080P（匿名上限 480P）
- 自动解析 `cid`，自动选择最高带宽的 H.264 (AVC) 视频流
- ffmpeg 流拷贝合并 —— **无重编码、无画质损失**
- 已下载文件经 `ffprobe` 校验后自动跳过，可安全重复运行

## 环境依赖

- Python 3.7+（仅标准库，无需 `pip install`）
- [ffmpeg](https://ffmpeg.org/)（需在 `PATH` 中，仅用于无损封装）

## 安装（独立 / 手动使用）

```bash
git clone https://github.com/houguofei/bilibili-downloader.git
cd bilibili-downloader
# 确保已安装 ffmpeg，然后运行：
python scripts/download_bilibili.py "https://www.bilibili.com/video/BV1vHxXefEEV"
```

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

# 通过环境变量传入（避免写入 shell 历史）
export BILI_COOKIE="SESSDATA=xxxx; bili_jct=yyyy"
python scripts/download_bilibili.py BV1vHxXefEEV

# 指定输出目录
python scripts/download_bilibili.py -d ./downloads BV1vHxXefEEV
```

输出文件命名为 `<标题净化后>__<BVID>.mp4`。

### 获取登录 Cookie（用于 1080P）

1. 登录 bilibili.com 后按 F12 → Application → Cookies（bilibili.com）
2. 复制 `SESSDATA`（以及可选的 `bili_jct`、`DedeUserID`）
3. **原样**粘贴 —— `SESSDATA` 中的 `%2C` / `%3D` 编码**不要解码**
4. 1080P60 / 4K 需要大会员账号的 `SESSDATA`

## 作为 Agent Skill 安装

本仓库本身已按可移植 Skill 结构组织：

```
bilibili-downloader/
├── SKILL.md                 # agent 指令（触发条件、工作流程、画质规则）
├── scripts/download_bilibili.py
├── references/api_reference.md
├── README.md
└── LICENSE
```

将整个文件夹复制到对应 agent 的 skills 目录即可。示例：

**WorkBuddy**
```bash
mkdir -p ~/.workbuddy/skills
cp -r bilibili-downloader ~/.workbuddy/skills/bilibili-downloader
```

**Claude Code**（skills 目录）
```bash
mkdir -p ~/.claude/skills
cp -r bilibili-downloader ~/.claude/skills/bilibili-downloader
```

**Cursor / Cline / 其他基于 VS Code 的 agent**
将文件夹复制到该 agent 的 skills 或自定义指令目录（如 `.cursor/skills/`，或项目的 agent rules 目录），并将 `SKILL.md` 作为指令来源引用。具体路径随版本而异，请参考对应 agent 的文档。

**任意 agent（通用）**
将 `SKILL.md` 作为系统指令交给 agent 即可；agent 随后可直接执行 `scripts/download_bilibili.py`，无需任何插件系统。

## 许可证

[MIT](LICENSE)
