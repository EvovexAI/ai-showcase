# draft-to-final.ps1 — Draft 样片 → 1080p 成片
# 前置: 已有样片任务且用户确认；draft_task_id 取样片 query-result 返回的 videos[].draft_task_id
# 用法:
#   powershell -File scripts\draft-to-final.ps1 -DraftTaskId <draft_task_id>
param(
  [Parameter(Mandatory=$true)][string]$DraftTaskId,
  [string]$Model = "Seedance_2.5_draft",
  [string]$Source = "doubao_office"
)

Write-Host "[draft-to-final] 提交成片: draft_task_id=$DraftTaskId model=$Model (服务端固定 1080p)"
$json = & pippit-tool-cli generate-video --model $Model --draft-task-id $DraftTaskId --source $Source | Out-String
Write-Host $json

if ($json -match '"thread_id"\s*:\s*"([^"]+)"') { $script:tid = $Matches[1] }
if ($json -match '"run_id"\s*:\s*"([^"]+)"')    { $script:rid = $Matches[1] }
if ($script:tid -and $script:rid) {
  Write-Host ""
  Write-Host "[draft-to-final] 成片任务已提交，查询下载:"
  Write-Host "  powershell -File scripts\query-result.ps1 -ThreadId $script:tid -RunId $script:rid"
}
