# Download Douyin video into videos/{aweme_id}/
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Url,
    [string]$Cookies,
    [switch]$AudioOnly
)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python (Join-Path $scriptDir "download-douyin.py") @(
    $Url
    $(if ($Cookies) { @("--cookies", $Cookies) })
    $(if ($AudioOnly) { "--audio-only" })
)
exit $LASTEXITCODE
