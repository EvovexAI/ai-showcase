@echo off
chcp 65001 >nul
setlocal
set DIR=D:\dev\github\feishu_downloads/ai-showcase/self-media/douyin-blogger-analyzer
set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if not exist "%CHROME%" set CHROME=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe

echo [1/2] 启动分析器 http://127.0.0.1:8787
start "douyin-analyzer" /min cmd /c "cd /d %DIR% && node server.js"

echo [2/2] 启动采集浏览器(带抖音登录态,独立目录)
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%DIR%\.chrome-profile" https://www.douyin.com

timeout /t 2 >nul
start "" http://127.0.0.1:8787

echo.
echo 完成。日常采集一条命令:
echo   node %DIR%\scripts\collect-douyin.js ^<博主主页URL^>
echo 首次请在弹出的浏览器里扫码登录抖音(以后免登录)。
pause
