# Lyric MV Producer

**简体中文** | [English](README.en.md)

一个给 AI Agent 用的歌词 MV 制作技能：你提供自己拥有权利的歌曲和歌词，它用代码画完整支片子。流水线覆盖速度与段落分析、LRC 歌词对时、320×180 索引色像素引擎、分镜与美术设定、程序化拟音、混音与 −14 LUFS 母带、1080p24 渲染、QA，以及交付（MP4、海报、SRT、字幕表）。

不用素材库、不用图像生成器、不用官方美术。每一帧都画进一块小的调色板索引帧缓冲，再以 6 倍最近邻放大，所以成片是确定的：同一个项目永远渲染出同样的帧和同样的混音。

## 创作风格

每一部都是代码绘制的像素歌词片，而不是配着歌放幻灯片：

- 320×180 索引色帧缓冲，6 倍最近邻放大到 1080p24，所有坐标取整。
- 每部片一套调色板，最多约 40 色，以 ENDESGA-32 为起点；避免大面积纯黑。
- 三档景别：远景（人物 16–40 px 高）、中景（60–90 px）、近景（100–150 px，只留给副歌和结尾）。
- 角色都是原创像素精灵；同人角色重新绘制，不直接取用官方精灵图。不使用图像生成器、素材库或 Logo。
- 歌词固定在底部居中，一到两行，1 px 描边，绝不压脸。
- 剪辑落在拍点或歌词起点；叠化克制使用；HUD 保持安静。
- 每部片单独写 Treatment、定调色板、角色和结构；引擎是画布，不是固定预设。

## 你会得到什么

- `song.mp4` — 1920×1080，24 fps，H.264，AAC 48 kHz 立体声，−14 LUFS
- `poster.jpg` — 取自尾奏的 16:9 海报
- `poster_4x3.jpg` — 1920×1440 横版封面
- `poster_3x4.jpg` — 1080×1440 竖版封面
- `song.srt` — 与画面共用同一份 cue 表
- `TREATMENT.md`、`CREDITS`、`lyrics.json`、`events.json`、`project.env`
- `build.sh` — 一条命令，从解码做到成片

三张封面都从同一张海报帧派生：先缩回 320×180 原生网格，横向裁切，再用最近邻放大，像素网格和宽高比都保持精确。`project.env` 里的 `COVER_X`（`0 = 左`、`0.5 = 中`、`1 = 右`）控制裁切窗口；3:4 封面只保留画面中间 42% 的宽度，所以海报构图必须照顾这一列。

## 环境要求

| 需要 | 说明 |
|---|---|
| 歌曲 | 你自己的音频文件（MP3/WAV/FLAC） |
| 歌词 | 带时间轴的 LRC，或手动对时的纯文本 |
| Node.js | 20+ |
| ffmpeg | 解码、响度、混流、QA |
| Python | 3.11+（或 uv），含 `numpy`、`scipy`、`soundfile` |
| 浏览器 | Playwright 的 Chromium headless，由 `setup.sh` 自动安装 |
| 渲染器 | [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar)，需要 `core/render/video.mjs` |
| 中文字体 | [GNU Unifont](https://unifoundry.com/unifont/) 的 `.hex.gz`，仅中日韩歌词需要 |

## 安装

技能本身没有安装钩子。先克隆技能，再跑一次 `setup.sh`，它会连同 Lemo-Opuscar 渲染库一起装好。

```bash
# 1. 把技能装到 Agent 读取技能的目录。
git clone https://github.com/ZeroOneCN/lyric-mv-producer.git \
  ~/.qoder-cn/skills/lyric-mv-producer
# 用 Claude Code 的话，改成 ~/.claude/skills/lyric-mv-producer。

# 2. 一次性安装：检查工具链，安装 Lemo-Opuscar 及其依赖。
sh ~/.qoder-cn/skills/lyric-mv-producer/scripts/setup.sh
```

`setup.sh` 会检查 **Node 20+、ffmpeg、Python 3.11+（或 uv）**，把 Lemo-Opuscar 克隆到 `~/lemo-opuscar`，再安装它的 npm 包、Chromium headless 和 Python 核心依赖。它不会安装 Node、ffmpeg、Python 或系统浏览器；缺什么会直接报出来。

- `sh scripts/setup.sh --check`：只检查版本和路径，不做修改
- `sh scripts/setup.sh --lib DIR` 或 `LEMO_OPUSCAR_HOME=DIR`：把渲染库装到别处
- 已有 Lemo 库时会复用它，并按官方流程安装/更新依赖
- 装完后新开一个会话，或执行 `/skills reload`
- `build.sh` 会优先使用 `$LIB/.venv` 里的 Python；也可以用 `PY=` 覆盖

歌词含中文、日文或韩文时，从 <https://unifoundry.com/unifont/> 下载 GNU Unifont 的 `.hex.gz`，在 scaffold 时用 `--font` 传入，或放进项目的 `fonts/unifont.hex.gz`。纯拉丁歌词不需要。

## 使用

把歌曲和歌词放进同一个文件夹，除此之外不需要别的：

```
my-song/
├── song.mp3
└── song.lrc
```

安装好之后，直接说：

> 用 lyric-mv-producer 做一支 MV。

如果音频和 LRC 不在当前目录，再补一句路径：

> 用 lyric-mv-producer 做一支 MV，歌曲和歌词在 ./my-song。

也支持斜杠命令：`/lyric-mv-producer`。

Agent 会读取技能，缺什么只问一次（音频和 LRC、片名、语气、你最想记住的一个画面、权利状态、是否要先看分镜），然后开始跑流水线。项目和全部交付物会写到工作目录下的新文件夹里。

有具体要求，就并进同一句话：

> 用 lyric-mv-producer 把 ./my-song 做成像素风 MV，片名《纸月亮》，主色蓝金，副歌要一次大远景；封面人物放中间，方便裁 3:4。

这不是一键应用。`setup.sh` 会装好 Lemo-Opuscar 和它的依赖，但 Node、ffmpeg、Python 和浏览器仍需系统里已有；一部长片在普通笔记本上渲染要几十分钟。这些都齐了之后，上面那句话就是全部接口；下面的命令是 Agent 实际执行的内容，留在这里方便查看或手动重跑。

## 手动流程

```bash
SKILL="$HOME/.qoder-cn/skills/lyric-mv-producer"
LIB="$HOME/lemo-opuscar"

# 1. 建项目骨架
python "$SKILL/scripts/scaffold.py" ./my-film \
  --title "PAPER MOON" --slug paper-moon \
  --dur 180.0 --song "/path/to/song.mp3" \
  --font "/path/to/unifont.hex.gz"

# 2. 分析速度与段落，然后靠耳朵确认
python "$SKILL/scripts/analyze_song.py" "/path/to/song.mp3" \
  --ffmpeg ffmpeg --json my-film/analysis/song.json

# 3. LRC 对时，生成 cue 表
python "$SKILL/scripts/lrc_to_lyrics.py" lyrics.lrc \
  -o my-film/lyrics.json --offset 0 --min-dur 1.2 --max-dur 8

# 4. 写 Treatment，再用静帧验证画面
cd my-film
node "$LIB/core/render/still.mjs" . 1.2 10.5 43.0 87.5 178.0 --prefix look_

# 5. 构建并检查
LIB="$LIB" sh build.sh
python tools/check_delivery.py . --slug paper-moon --ffmpeg ffmpeg
```

`check_delivery.py` 必须输出 `RESULT PASS`，而且仍然要完整看一遍成片。静帧、接触表（contact sheet）、切点切片、同步和声音检查的步骤见 `references/qa.md`。

## 项目结构

```
my-film/
├── project.env          # SLUG TITLE SONG DUR FPS POSTER_T COVER_X
├── lyrics.json          # [{ "text", "t0", "t1" }]
├── events.json          # { dur, bpm, beds, ducks, ev }
├── TREATMENT.md
├── CREDITS
├── build.sh
├── index.html
├── engine/              # px.js, font.js, font_zh.js, main.js
├── tools/               # genfont, mix, master_audio, make_srt,
│                        # make_covers, check_delivery
├── audio/               # song.wav, mix.wav, master.wav
├── analysis/
├── stills/
└── out/
```

页面契约很小：`window.DUR`、`window.SUBS`、`window.EV`、`window.render(t)`、`window.READY`。`render(t)` 必须是纯函数、无状态。

## 文档

| 文件 | 内容 |
|---|---|
| `SKILL.md` | 操作摘要、阶段门、交付契约 |
| `scripts/setup.sh` | 一次性安装渲染库与依赖，检查工具链 |
| `references/sop.md` | 完整流程与阶段门 |
| `references/pixel-engine.md` | 帧缓冲、调色板、绘制、镜头技巧 |
| `references/audio.md` | 分析、对时、电平规划、母带 |
| `references/qa.md` | QA 流程与具体命令 |
| `references/rights.md` | 权利门与 CREDITS 规则 |

## 权利

本仓库不包含任何音乐、歌词、角色美术或其他制作素材。请只使用你有权使用的音频和歌词。任何用本技能制作的片子，公开发布都需要你自行取得词曲同步权、录音母带权、歌词复制/展示授权以及角色形象授权。技能的权利门和 CREDITS 模板见 `references/rights.md`。

## 署名

- 像素引擎改编自 **Lemo-Opuscar**（MIT），版权归 LemoLab。
- 调色板以 ENDESGA 的 **ENDESGA-32** 为基础。
- 可选的中日韩字形来自 **GNU Unifont**（GPL-2.0-or-later，含字体嵌入例外）；字体在构建时读取，不随仓库分发。

完整授权文本见 `THIRD_PARTY_NOTICES`。

## 许可

本技能自身的文字和脚本尚未声明许可证。上方列出的第三方组件保留各自的许可证。
