# generate-ad.ps1 — 提交创意广告生视频任务（参数化封装 pippit-tool-cli generate-video）
# 用法示例:
#   powershell -File scripts\generate-ad.ps1 -Prompt "一只小猫在城市天际线穿梭奔跑，卡点" -Model Seedance_2.5 -Duration 10 -Ratio 9:16 -Resolution 720p
#   powershell -File scripts\generate-ad.ps1 -Prompt "..." -Model Seedance_2.5_draft -Draft -Duration 10 -Ratio 9:16     # 480p 样片
#   powershell -File scripts\generate-ad.ps1 -Prompt "..." -Model Seedance_2.5 -GenerateType 1 -Images "首帧.jpg","尾帧.jpg" -Ratio 9:16  # 首尾帧
#   powershell -File scripts\generate-ad.ps1 -Prompt "卡点广告" -Model Seedance_2.5 -Audio "bgm.mp3" -Duration 15 -Ratio 9:16  # 卡点 BGM 参考
param(
  [Parameter(Mandatory=$true)][string]$Prompt,
  [string]$Model = "Seedance_2.5",
  [int]$Duration = 10,
  [string]$Ratio = "9:16",
  [string]$Resolution = "720p",
  [int]$GenerateType = 0,
  [string]$TaskType = "",           # auto / reference / edit / extend
  [switch]$Draft,                   # 提交 480p 样片（Seedance_2.5_draft）
  [string]$DraftTaskId = "",        # 转成片时填样片的 draft_task_id（可省略 Prompt）
  [string[]]$Images = @(),          # 参考图 / 首尾帧图片（本地路径，可多个）
  [string[]]$Videos = @(),          # 参考视频（本地路径，可多个）
  [string[]]$Audios = @(),          # 参考音频/BGM（.mp3/.wav，可多个）
  [string]$Seed = "",
  [string]$Source = "doubao_office" # 宿主来源统计
)

$argsList = @("generate-video", "--prompt", $Prompt, "--model", $Model, "--duration", "$Duration", "--ratio", $Ratio, "--resolution", $Resolution, "--source", $Source)
if ($GenerateType -ne 0) { $argsList += @("--generate-type", "$GenerateType") }
if ($TaskType -ne "")     { $argsList += @("--task-type", $TaskType) }
if ($Draft)               { $argsList += "--draft" }
if ($DraftTaskId -ne "")  { $argsList += @("--draft-task-id", $DraftTaskId) }
if ($Seed -ne "")         { $argsList += @("--seed", $Seed) }
foreach ($img in $Images) { $argsList += @("--image", $img) }
foreach ($vid in $Videos) { $argsList += @("--video", $vid) }
foreach ($aud in $Audios) { $argsList += @("--audio", $aud) }

Write-Host "[generate-ad] 提交任务: model=$Model duration=${Duration}s ratio=$Ratio res=$Resolution"
if ($Draft) { Write-Host "[generate-ad] 模式: Draft 480p 样片" }

$json = & pippit-tool-cli @argsList | Out-String
Write-Host $json

# 解析 thread_id / run_id 供下一步查询
if ($json -match '"thread_id"\s*:\s*"([^"]+)"') { $script:tid = $Matches[1] }
if ($json -match '"run_id"\s*:\s*"([^"]+)"')    { $script:rid = $Matches[1] }
if ($script:tid -and $script:rid) {
  Write-Host ""
  Write-Host "[generate-ad] 下一步查询下载:"
  Write-Host "  powershell -File scripts\query-result.ps1 -ThreadId $script:tid -RunId $script:rid"
}
