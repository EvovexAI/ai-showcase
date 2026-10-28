# query-result.ps1 — 查询生成任务状态并下载产物
# 用法:
#   powershell -File scripts\query-result.ps1 -ThreadId skill_xxx -RunId skill_xxx
#   powershell -File scripts\query-result.ps1 -ThreadId skill_xxx -RunId skill_xxx -DownloadDir "D:\out"
#   powershell -File scripts\query-result.ps1 -ThreadId skill_xxx -RunId skill_xxx -WaitSeconds 90   # 每 90s 轮询一次直到完成
param(
  [Parameter(Mandatory=$true)][string]$ThreadId,
  [Parameter(Mandatory=$true)][string]$RunId,
  [string]$DownloadDir = "",
  [int]$WaitSeconds = 30
)

if ($DownloadDir -eq "") { $DownloadDir = Join-Path $PSScriptRoot "..\output" }
New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null

$baseArgs = @("query-result", "--thread-id", $ThreadId, "--run-id", $RunId, "--download-dir", $DownloadDir)

while ($true) {
  $json = & pippit-tool-cli @baseArgs | Out-String
  Write-Host $json
  if ($json -match '"completed"\s*:\s*true') {
    Write-Host "[query-result] 任务完成 ✓  输出目录: $DownloadDir"
    break
  }
  Write-Host "[query-result] 生成中... ${WaitSeconds}s 后重试 (Ctrl+C 退出)"
  Start-Sleep -Seconds $WaitSeconds
}
