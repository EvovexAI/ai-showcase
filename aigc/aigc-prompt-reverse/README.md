# 1008 · AIGC 反推提示词工作台

把一条视频**反推**成可粘贴的视频生成提示词（即梦 / Seedance / 可灵等）。

**做法很简单**：抽少量关键帧图（约 20 秒 5～6 张）+ 音频 → 多模态模型看图听声 → 写出生成提示词。

本项目从 `1004` 复制并专项化，只做反推；内容起号请用 [`../../self-media/douyin-video-pipeline`](../../self-media/douyin-video-pipeline/)。

系统提示词（页面可改）：[`prompts/reverse-system.md`](prompts/reverse-system.md)。  
**全程本地**，端口 **8768**。

---

## 快速开始

```powershell
python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
python scripts/web_server.py
# → http://127.0.0.1:8768
```

1. 粘贴抖音分享文案 / 短链  
2. 关键帧默认约 3.5 秒一帧（约 20 秒 5～6 张）  
3. 点「开始反推」→ 用关键帧 + 音频反推生成提示词  

CLI：

```powershell
python scripts/analyze_douyin.py last --full `
  --analysis-mode prompt_reverse `
  --keyframe-mode interval --interval-seconds 3.5
```

---

## 与 1004 的分工

| 项目 | 做什么 | 端口 |
|------|--------|------|
| **1004** 抖音视频拆解工作台 | 内容拆解 / 起号 | 8765 |
| **1008** AIGC 反推提示词（本项目） | 反推 T2V/I2V Prompt | 8768 |

---

## EvoFlow 接入

见 [EVOFLOW-SETUP.md](EVOFLOW-SETUP.md)。员工：`aigc-prompt-reverser`；技能：`aigc-prompt-reverse`。
