# ensure-cli.ps1 — 检查/安装 pippit-tool-cli，确认登录状态
# 用法:
#   powershell -File scripts\ensure-cli.ps1              # 仅检查
#   powershell -File scripts\ensure-cli.ps1 -Install     # 未安装则自动安装
param(
  [switch]$Install
)

$cli = "pippit-tool-cli"
$cmd = Get-Command $cli -ErrorAction SilentlyContinue

if (-not $cmd) {
  if ($Install) {
    Write-Host "[ensure-cli] 未找到 $cli ，开始安装（npx @pippit-dev/cli@latest install）..."
    npx @pippit-dev/cli@latest install
    if ($LASTEXITCODE -ne 0) { Write-Host "[ensure-cli] 安装失败"; exit 1 }
  } else {
    Write-Host "[ensure-cli] 未找到 $cli 。请先安装: npx @pippit-dev/cli@latest install"
    exit 1
  }
}

Write-Host "--- 版本 ---"
& $cli --version

Write-Host "--- 登录状态 ---"
$statusRaw = & $cli status 2>$null | Out-String
Write-Host $statusRaw
if ($statusRaw -match '"logged_in"\s*:\s*true') {
  Write-Host "[ensure-cli] 已登录 ✓"
} else {
  Write-Host "[ensure-cli] 未登录。请运行: pippit-tool-cli login"
  Write-Host "         提示: 授权页登录的账号必须是「开通会员/有积分」的那个账号;"
  Write-Host "               授权完成后若浏览器提示跳回 127.0.0.1 本地地址, 选「允许/继续」。"
  exit 2
}
