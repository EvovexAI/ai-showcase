@echo off
rem 视频分析 · 一键启动（双击运行）
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   视频分析 - 启动中...
echo   浏览器打开 http://127.0.0.1:8765
echo   关闭本窗口即停止服务
echo ============================================
python scripts\web_server.py
pause
