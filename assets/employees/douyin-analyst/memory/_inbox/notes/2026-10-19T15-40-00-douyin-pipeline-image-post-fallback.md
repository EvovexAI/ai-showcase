[experience] 抖音拆解流水线图文帖处理经验

背景：用户分享的图文作品（aweme_type=2），流水线脚本 `download-douyin.py` 会尝试下载视频，实际返回无效0字节mp4（图文无视频流），导致拆解失败。
- 现象：job 显示 step=download error，ffprobe 报 moov atom not found（因视频文件为空）
- 处置：
  1. 确认 aweme_type=2 是图文帖（images 数组存在，play_addr 为无效视频地址）
  2. 手动提取图文的下载图片 URL（url_list），通过 urllib 批量下载10张图
  3. 结合文案 + 图像分析（view_image）产出拆解报告，覆盖图文帖的结构、钩子、落地方法
- 教训：
  - 流水线原生只支持视频（aweme_type=0），图文帖需 fallback 手动拆解
  - 图文帖拆解需兼顾文案、图卡结构和落地行动指南，重点放在用户痛点和可模仿的行动

可复用清单（下次图文帖拆解照做）：
1. 提取分享页 images 数组的 URL（跳过 watermark 水印参数）
2. 手动下载图片（跳过流水线的 video.mp4 下载错误）
3. 按10张图的图卡内容，还原文案+视觉结构，产出拆解报告
4. 报告核心放在「痛点钩子」「结构密度」「行动门槛」这3个自媒体要点
