@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0webapp"

:: ── 日志文件 ──
set "TUNNEL_LOG=%TEMP%\cf_kb_tunnel.log"
if exist "%TUNNEL_LOG%" del /f "%TUNNEL_LOG%"

echo ============================================
echo   脑退行性疾病知识库 — 一键启动
echo ============================================
echo.

:: ── 0. 预检 ──
if not exist "%USERPROFILE%\cloudflared.exe" (
    echo [错误] 未找到 cloudflared.exe: %USERPROFILE%\cloudflared.exe
    pause
    exit /b 1
)

:: ── 1. 检查端口占用 ──
netstat -ano 2>nul | findstr ":5000.*LISTENING" >nul
if %errorlevel%==0 (
    echo [警告] 端口 5000 已被占用，正在释放...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000.*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

:: ── 2. 启动 Flask ──
echo [1/2] 启动 Flask 服务（端口 5000）...
start "知识库Flask服务" cmd /k "cd /d %CD% && python app.py"
echo        等待 Flask 启动...
timeout /t 4 /nobreak >nul

curl -s http://localhost:5000/health >nul 2>&1
if %errorlevel%==0 (
    echo        Flask 服务已就绪 [OK]
) else (
    echo        Flask 可能还在启动，稍后请检查新窗口
)

:: ── 3. 启动 Cloudflare 隧道 ──
::    关键：cmd /k 的双引号内，> 和 & 不会被外层解释
::    路径不含空格，直接传 %VAR% 展开值即可，无需嵌套引号
echo.
echo [2/2] 启动 Cloudflare 公网隧道...
echo        等待公网地址（约 5~10 秒）...

start "公网隧道-Cloudflare" cmd /k "cd /d %USERPROFILE% && cloudflared.exe tunnel --url http://localhost:5000 >%TUNNEL_LOG% 2>&1"

:: ── 4. 轮询日志文件 ──
set "TUNNEL_URL="
set "TRY=0"

:poll
timeout /t 2 /nobreak >nul
set /a TRY+=1

if not exist "%TUNNEL_LOG%" goto :check_timeout

:: 查找包含 trycloudflare.com 的行
findstr /c:"trycloudflare.com" "%TUNNEL_LOG%" 2>nul | findstr /c:"https://" >nul 2>&1
if !errorlevel! neq 0 goto :check_timeout

:: 用 PowerShell 从日志中提取 URL（行内可能含 | 等特殊字符）
for /f "usebackq tokens=*" %%u in (`powershell -NoProfile -Command ^
    "$m=[regex]::Match((Get-Content '%TUNNEL_LOG%' -Raw),'https://[a-zA-Z0-9.-]+\.trycloudflare\.com');if($m.Success){$m.Value}"`) do (
    if not "%%u"=="" set "TUNNEL_URL=%%u"
)
if defined TUNNEL_URL (
    :: 同步写入数字员工地址登记表
    echo !TUNNEL_URL!> "%USERPROFILE%\digital_employee\current_public_url.txt"
    goto :done
)

:check_timeout
if !TRY! lss 20 goto :poll

:: ── 5. 显示结果 ──
:done
echo.
echo ============================================
echo   启动完成！
echo.
echo   本地访问: http://localhost:5000
if defined TUNNEL_URL (
    echo   公网地址: !TUNNEL_URL!
) else (
    echo   公网地址: [未能自动获取]
    echo   ──────────────────────────────────────
    echo   请查看「公网隧道-Cloudflare」窗口中的
    echo   https://*.trycloudflare.com 链接
    echo   或查看日志: %TUNNEL_LOG%
)
echo ============================================
echo.
echo   提示: Flask 和隧道窗口保持打开
echo.
pause
