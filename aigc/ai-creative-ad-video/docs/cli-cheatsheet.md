# pippit-tool-cli 命令速查（已验证 v1.0.41，2026-10-15）

官方仓库：<https://github.com/Pippit-dev/cli> ｜ npm：`@pippit-dev/cli`

## 安装 / 更新

```powershell
npx @pippit-dev/cli@latest install        # 安装 CLI + 3 个官方技能（~/.agents/skills/）
pippit-tool-cli update                     # 更新到 latest
pippit-tool-cli --version                  # 查版本
```

## 登录 / 授权

```powershell
pippit-tool-cli login                      # 浏览器授权（凭证存系统安全库）
pippit-tool-cli status                     # 看登录状态
pippit-tool-cli logout                     # 退出
```

⚠️ 三个坑（实测踩过）：
1. 授权页登录的**必须是开通会员/有积分的那一个账号**，否则页面只会引导你"开会员"；
2. 授权完成后页面跳回 `127.0.0.1:xxxxx` 本地回调，浏览器提示时**选允许/继续**，否则 CLI 收不到回调、超时失败；
3. CI/Agent 场景可设 `XYQ_ACCESS_KEY` 环境变量代替网页登录。

## 模型

```powershell
pippit-tool-cli model list                            # 全部视频模型（缓存 5 分钟）
pippit-tool-cli model list --type image               # 图片模型
pippit-tool-cli model list --refresh                  # 强制刷新
pippit-tool-cli model describe Seedance_2.5           # 模型参数详情
```

实测可用视频模型（以 `model list` 实际返回为准）：
`Seedance_2.5_draft`（样片/成片）｜`Seedance_2.5`（最强）｜`seedance2.0_fast_vision`｜`seedance2.0_vision`｜`Seedance_2.0_mini_lite`｜`Seedance_2.0_mini`｜`wan3.0`（写实）｜`happyhorse-1.1`（动态喜剧）

## 生视频

```powershell
# 常规（参数: prompt 必填, model 必填）
pippit-tool-cli generate-video --prompt "..." --model Seedance_2.5 --duration 10 --ratio 9:16 --resolution 720p --source doubao_office

# 参考素材（可多个, 自动上传）
pippit-tool-cli generate-video --prompt "..." --model Seedance_2.5 --image a.jpg --video b.mp4 --audio bgm.mp3 --ratio 9:16 --resolution 720p

# 首尾帧（按 首帧、尾帧 顺序传 --image, 固定 --generate-type 1）
pippit-tool-cli generate-video --prompt "..." --model Seedance_2.5 --image first.jpg --image last.jpg --generate-type 1 --ratio 9:16 --resolution 720p

# Draft 480p 样片
pippit-tool-cli generate-video --model Seedance_2.5_draft --draft --prompt "..." --task-type reference --ratio 9:16 --duration 10

# Draft 转成片（只需模型 + 样片 draft_task_id, 服务端固定 1080p）
pippit-tool-cli generate-video --model Seedance_2.5_draft --draft-task-id <draft_task_id>
```

返回：`thread_id` / `run_id` / `web_thread_link`（异步任务，须轮询查询）。

## 查询 / 下载

```powershell
pippit-tool-cli query-result --thread-id skill_xxx --run-id skill_xxx --download-dir "D:\out"
# completed=true 时 videos[].output_path 为本地文件；样片结果含 draft_task_id
```

## 视频处理

```powershell
pippit-tool-cli video-super-resolution --video src.mp4 --output-resolution 1080p [--tool-version standard]   # 超分: 720p/1080p/2k/4k
pippit-tool-cli erase-video-subtitle --video src.mp4                                                          # 擦字幕
```

## 积分

```powershell
pippit-tool-cli get-credit-balance            # {"total_remain_amount":"6196"}
pippit-tool-cli get-credit-balance --with-log-id
```

## 生图

```powershell
pippit-tool-cli model list --type image
pippit-tool-cli generate-image --prompt "..." --model "智能图片V2.5 Fast" --ratio 6 --generate-image-count 1
```

## Canvas（专业画布工作流，进阶）

```powershell
pippit-tool-cli canvas create --title "..." --wait
pippit-tool-cli canvas command list                       # 语义命令目录
pippit-tool-cli canvas command describe <cmd>             # 命令参数
pippit-tool-cli canvas command guide                      # 离线指南索引（storyboard / prompt-references / time / timeline / scene3d）
pippit-tool-cli canvas command guide prompt-references    # 提示词引用规范
```

## 其他

```powershell
pippit-tool-cli short-drama +submit-run --message "写一个赛博朋克短剧开头"   # 短剧工作流
pippit-tool-cli short-drama +upload-file --path ./ref.doc                    # 上传参考（.doc/.docx/.txt）
pippit-tool-cli get-thread --thread-id xxx --run-id xxx                      # 会话详情
pippit-tool-cli list-thread-file --thread-id xxx --page-num 1 --page-size 200
pippit-tool-cli download-result --output-path ./out.mp4 --url <url> --updated-at <ts>
```

## 素材格式与限制

- 图片：jpg / jpeg / png / gif / bmp / webp / svg
- 视频：mp4 / avi / mov / wmv / flv / webm / mkv / m4v
- 音频：mp3 / wav
- 单文件 < 500 MB（500000000 字节）
