@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem ============================================================
rem  宿舍服务平台 · Windows 一键启动
rem  用法：双击本文件；或在 cmd 中执行  start.bat 9000  指定端口
rem ============================================================

set "PORT=8000"
if not "%~1"=="" set "PORT=%~1"

echo == 检查 Python ==
set "PY=python"
where py >nul 2>nul
if %errorlevel%==0 set "PY=py"

%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,11) else 1)"
if errorlevel 1 (
  echo.
  echo [错误] 未找到 Python 3.11 及以上版本。
  echo        请到 https://www.python.org/downloads/ 安装，安装时务必勾选 "Add python.exe to PATH"。
  echo.
  pause
  exit /b 1
)

%PY% -c "import fastapi, sqlalchemy, aiosqlite, uvicorn, reportlab, PIL" >nul 2>nul
if %errorlevel%==0 (
  echo == 依赖已就绪，跳过安装 ==
  set "RUNPY=%PY%"
) else (
  if not exist ".venv\Scripts\python.exe" (
    echo == 创建虚拟环境 .venv ==
    %PY% -m venv .venv
    if errorlevel 1 (
      echo [错误] 创建虚拟环境失败。
      pause
      exit /b 1
    )
  )
  set "RUNPY=.venv\Scripts\python.exe"

  echo == 安装依赖（首次约 1-2 分钟）==
  "%RUNPY%" -m pip install -q --upgrade pip >nul 2>nul
  "%RUNPY%" -m pip install -q -r backend\requirements.txt
  if errorlevel 1 (
    echo == 默认源安装失败，改用清华镜像重试 ==
    "%RUNPY%" -m pip install -q -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  )
  if errorlevel 1 (
    echo.
    echo [错误] 依赖安装失败，请检查网络后重试，或先配置代理。
    echo        代理示例：set HTTPS_PROXY=http://127.0.0.1:7890
    echo.
    pause
    exit /b 1
  )
)

if not exist "frontend\dist\index.html" (
  echo [提示] 未找到 frontend\dist，页面将无法打开，仅可访问 API。
  echo        如需构建前端：cd frontend ^&^& npm i -g pnpm ^&^& pnpm install ^&^& pnpm build
)

echo.
echo == 服务启动中：http://127.0.0.1:%PORT%
echo    演示账号：20223601 / Abc123456    宿管：admin / Admin@123
echo    API 文档：http://127.0.0.1:%PORT%/api/v1/docs
echo    关闭本窗口或按 Ctrl+C 停止
echo.

cd backend
"%RUNPY%" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

echo.
echo 服务已停止。
pause
