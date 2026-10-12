# 抖音视频拆解系统集成指南 (起号拆解 Integration)

## 📋 项目结构

现在 `ai-video-decompose` 项目集成了完整的**起号拆解**系统，包含以下核心部分：

```
D:\dev\github\evo\edu\ai-demos\ai-video-decompose\
├── web/                          # Web UI (Vue 3 + Tailwind)
├── scripts/                       # 拆解核心脚本
│   ├── web_server.py             # Web 服务器主程序
│   ├── downloader.py              # 视频下载器
│   ├── analyzer.py                # 内容分析引擎
│   └── ...
├── productions/                   # 视频制作项目库
├── downloads/                     # 下载的视频存储
├── videos/                        # 已拆解视频素材
├── data/
│   ├── video_raw.mp4             # 样本视频 (43.5 MB, 4:50)
│   ├── ANALYSIS_DECOMPOSE.md     # 分析报告
│   └── frame_0001.jpg ~ frame_0145.jpg  # 145 个关键帧
├── skills/                        # Cursor 集成技能
├── cloud-run/                     # Google Cloud Run 部署配置
├── config/                        # 配置文件目录
└── miniprogram/                   # 微信小程序版本
```

## 🚀 快速开始

### 1. 启动 Web 服务器

```bash
cd D:\dev\github\evo\edu\ai-demos\ai-video-decompose
python scripts/web_server.py
```

访问：**http://127.0.0.1:8765**

### 2. Web UI 功能

- **✦ 粘贴拆解** - 输入抖音短链或完整链接进行拆解
- **📂 视频库** - 管理和浏览已拆解的视频
- **📝 制作策划** - 编辑分镜、配音、录屏操作
- **🎙 配音设置** - 配置火山 TTS 进行口播配音

### 3. 样本数据

项目已包含一个完整的拆解样本：

- **视频内容**: AI成本优化讲解 (Douyin)
- **时长**: 4 分 50 秒 (1920×1080)
- **关键帧**: 145 帧 (每0.5秒一帧)
- **分析报告**: `data/ANALYSIS_DECOMPOSE.md`

## 📊 核心功能

### 视频拆解流程

1. **下载** - yt-dlp 获取完整视频
2. **分析** - 提取关键帧、文字识别、场景分割
3. **编辑** - 制作分镜、标记重点、添加配音
4. **导出** - 生成成片或分镜库

### 关键帧提取

默认配置：
- **模式**: 口播一句一帧（按文本分段截图）
- **关键帧数**: 自动或自定义
- **格式**: JPG 图片 + 时间轴数据

### 配音系统

集成**火山 TTS** (Volcengine)：
- 支持多种音色
- 自动跳过纯录屏段
- 批量生成 MP3

## 🔧 配置

### 火山 TTS 配置

在 Web UI 的「配音设置」中填入：

```
API Key: ark-xxxx... (或从环境变量读取)
Resource ID: (可选)
Voice Type: seed-tts-2.0
```

或设置环境变量：
```powershell
$env:ARK_API_KEY = "ark-xxxx..."
$env:VOLCENGINE_SPEECH_API_KEY = "xxxx..."
```

### 数据库

- 使用 SQLite (本地)
- 存储: `productions/` 文件夹
- 自动持久化

## 📁 核心文件说明

| 文件 | 用途 |
|------|------|
| `scripts/web_server.py` | 启动 Web 服务器主程序 |
| `scripts/analyzer.py` | 内容分析和关键帧提取 |
| `scripts/downloader.py` | 抖音视频下载 |
| `web/` | Vue 3 前端界面 |
| `data/` | 样本数据 (视频 + 帧 + 报告) |
| `productions/` | 用户创建的项目库 |

## 🌐 部署选项

### 本地运行
```bash
python scripts/web_server.py
```

### Docker
```bash
docker build -t qihao-decompose .
docker run -p 8765:8765 qihao-decompose
```

### Google Cloud Run
配置在 `cloud-run/` 文件夹

### 微信小程序
源码在 `miniprogram/` 文件夹

## 💡 使用场景

1. **内容创作** - 快速拆解爆款视频提取创意
2. **教学演示** - 分析视频结构和节奏
3. **视频编辑** - 生成分镜草稿自动化剪辑
4. **数据分析** - 提取视频的时间轴数据和关键信息

## 📝 Git 提交

本集成已提交到分支 `feat/add-video-decomposition-sample`：

```
Commit: 94d5270
Message: chore: integrate Douyin video decomposition system (起号拆解)
Changes: 147 files, +233 insertions
- 完整的起号拆解代码
- 145 张关键帧
- 分析报告
- Web 服务器配置
```

## 🔗 相关文档

- `ANALYSIS_DECOMPOSE.md` - 样本视频的完整分析报告
- `WORKFLOW.md` - 完整工作流说明
- `DEMO.md` - 演示和优化文档
- `SUMMARY.md` - 项目总结

## ⚠️ 注意事项

1. **Cookie 要求** - 下载私密视频需要抖音登录 cookies
2. **网络** - 需要稳定的网络连接下载视频
3. **存储** - 视频和帧可能占用较大存储空间
4. **火山 Key** - 配音功能需要有效的火山 TTS API Key

## 🎯 下一步

1. 启动 Web 服务器体验界面
2. 上传样本视频进行拆解
3. 修改配音设置并生成 MP3
4. 导出分镜库用于后续制作

---

**起号拆解** × **ai-video-decompose** = 完整的视频内容分析和制作系统 🚀
