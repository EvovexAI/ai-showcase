#requires -Version 5.1
<#
.SYNOPSIS
  视频拆解工作台(1004)一键接入 EvoFlow(UFO)：B1 扩展面板 + B2 技能装库 + B4 知识库同步。
  幂等：重复运行只做增量更新，不破坏已有配置。

.DESCRIPTION
  本脚本由 skills/evoflow-onboarding/SKILL.md 调用，也可直接运行：
    powershell -ExecutionPolicy Bypass -File scripts\install-into-evoflow.ps1

  自动完成：
    [B1] 注册 UI 扩展 douyin-video-pipeline（写 registry.json，link 模式只记路径）
    [B2] 安装技能 douyin-video-pipeline + evoflow-onboarding 到技能目录
    [B4] 创建/复用知识库「视频拆解报告库」并导入 data/reports（gateway HTTP API，幂等增量）
    [B3/B5] 员工与日常使用：输出核验指引（员工已存在则直接核验）

  已知坑（本脚本已绕开）：
    - 不用 `evoflow` CLI（本机 CLI 卡死），改走文件直写 + gateway HTTP API
    - 数据目录固定用用户正式环境 ~/.evoflow（不带 -dev，-dev 只是开发调试目录）
    - 知识库同步走 EvoFlow 内置 gateway（/api/knowledge/owned/*），不依赖外部 venv python
    - 反斜杠路径在 PowerShell 传给 JSON 时会被吞，统一用 Join-Path 拼绝对路径
    - PS5.1 的 Set-Content -Encoding UTF8 写出带 BOM 的文件，且管道会把单元素数组
      拆成裸对象——面板(Rust serde_json)两者都不认，扩展会「装了但不显示」。
      落盘一律 [IO.File]::WriteAllText + UTF8Encoding($false)，注册表写成数组。
.PARAMETER ProjectRoot
  项目根目录，默认取脚本所在目录的上一级。
.PARAMETER EvoHome
  EvoFlow 数据目录。默认 ~/.evoflow（用户正式环境，不带 -dev；-dev 仅用于本机调试）。
  可用 -EvoHome 参数或环境变量 EVOFLOW_EVOHOME 覆盖。
.PARAMETER Gateway
  EvoFlow gateway API 入口，默认 http://127.0.0.1:8382。
#>
param(
  [string]$ProjectRoot = "",
  [string]$EvoHome = "",
  [string]$Gateway = "http://127.0.0.1:8382"
)

$ErrorActionPreference = "Stop"

# ---------- 0. 路径解析 ----------
if (-not $ProjectRoot) { $ProjectRoot = Split-Path -Parent $PSScriptRoot }
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$Manifest = Join-Path $ProjectRoot "evoflow.extension.json"
if (-not (Test-Path $Manifest)) { throw "✗ 项目根找不到 evoflow.extension.json: $ProjectRoot" }

if (-not $EvoHome) {
  $EvoHome = $env:EVOFLOW_EVOHOME
}
if (-not $EvoHome) {
  $EvoHome = Join-Path $env:USERPROFILE ".evoflow"   # 用户正式环境（不带 -dev）
}
if (-not (Test-Path $EvoHome)) {
  New-Item -ItemType Directory -Path $EvoHome -Force | Out-Null
}
Write-Host "EvoFlow 数据目录: $EvoHome"

# ---------- B1 扩展注册（幂等 + 写前备份） ----------
function Register-Extension {
  param($EvoHome, $ProjectRoot, $Manifest)
  $regDir  = Join-Path $EvoHome "ui-extensions"
  $regFile = Join-Path $regDir "registry.json"
  if (-not (Test-Path $regDir)) { New-Item -ItemType Directory -Path $regDir -Force | Out-Null }

  $manifest = Get-Content $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
  $reg = @()
  if (Test-Path $regFile) {
    $raw = Get-Content $regFile -Raw -Encoding UTF8
    if ($raw -and $raw.Trim()) {
      $parsed = ConvertFrom-Json $raw
      if ($parsed) {
        if ($parsed -is [System.Array]) { $reg = $parsed } else { $reg = @($parsed) }
      }
    }
  }

  $found = $false
  for ($i = 0; $i -lt $reg.Count; $i++) {
    if ($reg[$i].id -eq $manifest.id) {
      $reg[$i].enabled       = $true
      $reg[$i].install_path  = $ProjectRoot
      $reg[$i].manifest      = $manifest
      $reg[$i].source        = "folder-link"
      $found = $true
      break
    }
  }
  if (-not $found) {
    $reg += [pscustomobject]@{
      enabled      = $true
      id           = $manifest.id
      install_path = $ProjectRoot
      installed_at = (Get-Date).ToUniversalTime().ToString("o")
      manifest     = $manifest
      source       = "folder-link"
    }
  }

  $bak = "$regFile.bak-$($manifest.id)-$([DateTimeOffset]::Now.ToUnixTimeMilliseconds())"
  if (Test-Path $regFile) { Copy-Item $regFile $bak -Force }
  # ★ 必须 UTF-8 无 BOM + 数组形态：面板(Rust serde_json)不吃 BOM，
  #   而 PS 管道会把单元素数组拆成裸对象——两者都表现为「脚本装了、面板不显示」。
  #   -InputObject 才能保住数组形态；UTF8Encoding($false) 才是无 BOM。
  $json = ConvertTo-Json -InputObject $reg -Depth 15
  [IO.File]::WriteAllText($regFile, $json, [Text.UTF8Encoding]::new($false))
  # 写后校验：JSON 合法、形态为数组、首字节无 BOM
  $check = Get-Content $regFile -Raw -Encoding UTF8 | ConvertFrom-Json
  if (-not ($check -is [System.Array])) { throw "✗ registry.json 写成了非数组形态（PS 管道拆包），检查 ConvertTo-Json -InputObject" }
  $head = (Get-Content $regFile -Encoding Byte -TotalCount 3) -join ','
  if ($head -eq '239,187,191') { throw "✗ registry.json 仍带 UTF-8 BOM，写盘函数未生效" }
  Write-Host "✓ [B1] 扩展已注册: $($manifest.id) → $regFile"
}

# ---------- B2 技能装库（幂等；写入正式环境） ----------
# gateway 实际从 ~/.evoflow/profiles/default/skills/custom 加载技能；
# .evoflow-dev 是开发调试环境，用户机器没有，不写入。
function Install-Skill {
  param($EvoHome, $ProjectRoot)
  $src = Join-Path $ProjectRoot "skills"
  if (-not (Test-Path $src)) { Write-Host "! [B2] 无 skills 目录，跳过"; return }
  $targets = @(
    (Join-Path $EvoHome "profiles\default\skills\custom"),
    (Join-Path $EvoHome "skills\custom")
  ) | Where-Object { $_ } | Select-Object -Unique
  foreach ($skill in @("douyin-video-pipeline", "evoflow-onboarding")) {
    $s = Join-Path $src $skill
    if (-not (Test-Path (Join-Path $s "SKILL.md"))) { continue }
    foreach ($t in $targets) {
      $d = Join-Path $t $skill
      New-Item -ItemType Directory -Path $d -Force | Out-Null
      Copy-Item (Join-Path $s "SKILL.md") (Join-Path $d "SKILL.md") -Force
    }
    Write-Host "✓ [B2] 技能已装库: $skill → $($targets -join ' ; ')"
  }
}

# ---------- B4 知识库同步（幂等：gateway HTTP API，不依赖外部 venv） ----------
# EvoFlow 桌面端内置 gateway 提供 /api/knowledge/owned/* 正式知识库服务；
# 不需要外部 venv python，也不依赖任何开发机调试路径（对用户环境开箱即用）。
function Sync-KnowledgeBase {
  param($ProjectRoot, $Gateway = "http://127.0.0.1:8382")
  $reports = Join-Path $ProjectRoot "data\reports"
  if (-not (Test-Path $reports)) { Write-Host "! [B4] data/reports 不存在，跳过"; return }

  Write-Host "   [B4] 通过 gateway 同步知识库..."
  $basesRaw = curl.exe -s -m 15 "$Gateway/api/knowledge/owned/bases"
  if (-not $basesRaw) { Write-Host "! [B4] gateway 不可达($Gateway)，跳过（面板起来后重跑本脚本即可）"; return }
  $bases = ($basesRaw | ConvertFrom-Json).items
  $kb = $bases | Where-Object { $_.name -eq "视频拆解报告库" } | Select-Object -First 1

  if (-not $kb) {
    Write-Host "   [B4] 知识库不存在，创建中..."
    $body = @{ name = "视频拆解报告库"; description = "抖音视频拆解报告案例库，来自 1004 data/reports，供写脚本时检索对标案例" } | ConvertTo-Json -Compress
    $created = curl.exe -s -m 30 -X POST "$Gateway/api/knowledge/owned/bases" -H "Content-Type: application/json" -d $body
    $kb = $created | ConvertFrom-Json
    if (-not $kb.id) { Write-Host "! [B4] 创建知识库失败: $created"; return }
    Write-Host "✓ [B4] 已创建知识库: $($kb.id)"
  } else {
    Write-Host "✓ [B4] 复用已有知识库: $($kb.id)"
  }

  $imp = @{ path = $reports; upsert = $true; pruneMissing = $false } | ConvertTo-Json -Compress
  # ★ 含中文路径的 JSON 先落盘再提交（PowerShell 直接传参会被拆分）；
  #   落盘必须无 BOM：curl --data-binary 原样发送，gateway 侧 json.loads 遇 BOM 直接报错
  $impFile = Join-Path $env:TEMP "sync-kb-1004-import.json"
  [IO.File]::WriteAllText($impFile, $imp, [Text.UTF8Encoding]::new($false))
  $res = curl.exe -s -m 120 -X POST "$Gateway/api/knowledge/owned/bases/$($kb.id)/import-folder" -H "Content-Type: application/json" --data-binary "@$impFile"
  Remove-Item $impFile -Force -ErrorAction SilentlyContinue
  Write-Host "✓ [B4] 报告目录已导入: $res"
}

# ---------- 执行 ----------
Register-Extension -EvoHome $EvoHome -ProjectRoot $ProjectRoot -Manifest $Manifest
Install-Skill      -EvoHome $EvoHome -ProjectRoot $ProjectRoot
Sync-KnowledgeBase -ProjectRoot $ProjectRoot -Gateway $Gateway

Write-Host ""
Write-Host "====== 接入完成，请逐项核验 ======"
Write-Host "B1 面板「扩展」出现「视频拆解」：重启面板或 设置→扩展→刷新"
Write-Host "B2 技能列表：douyin-video-pipeline / evoflow-onboarding"
Write-Host "B3 员工「视频拆解师」：新环境不存在，请按 skills\evoflow-onboarding\SKILL.md 第 3 节创建（挂双技能+绑知识库+工作空间设为解压路径）"
Write-Host "B4 知识库「视频拆解报告库」：搜「钩子」能命中即通过"
Write-Host "B5 日常使用：对 EvoFlow 说「让视频拆解师拆解:<链接>」"
