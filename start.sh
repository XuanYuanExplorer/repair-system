#!/usr/bin/env bash
# 宿舍服务平台 · 一键启动脚本
# 用法：./start.sh              （默认 8000 端口）
#       PORT=9000 ./start.sh     （指定端口）
#       PYTHON=python3.11 ./start.sh
#
# 逻辑：优先复用系统 Python（已装依赖则跳过安装）；否则建 .venv 安装依赖。
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}
PORT=${PORT:-8000}
DEPS="import fastapi, sqlalchemy, aiosqlite, uvicorn, reportlab, PIL"

echo "==> 检查 Python"
$PY -V

RUN_PY=""
if $PY -c "$DEPS" >/dev/null 2>&1; then
  echo "==> 系统 Python 已具备依赖，跳过安装"
  RUN_PY=$PY
else
  if [ ! -d .venv ]; then
    echo "==> 创建虚拟环境 .venv"
    $PY -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  echo "==> 安装依赖（首次约 1-2 分钟）"
  pip install -q --upgrade pip || echo "!! pip 升级失败，继续尝试安装依赖"
  if ! pip install -q -r backend/requirements.txt; then
    echo ""
    echo "!! 依赖安装失败。常见原因与处理："
    echo "   1) 网络不通 / 需要代理：配置 HTTPS_PROXY 后重试，或使用国内镜像："
    echo "      pip install -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
    echo "   2) 公司网络证书校验失败：加 --trusted-host pypi.org --trusted-host files.pythonhosted.org"
    echo "   3) 已装好依赖但想跳过安装：pip install 完成后重新执行本脚本即可"
    exit 1
  fi
  RUN_PY=".venv/bin/python"
fi

# 前端构建产物缺失时，若本机有 pnpm 则自动构建（发布包已内置 dist，通常可跳过）
if [ ! -f frontend/dist/index.html ]; then
  if command -v pnpm >/dev/null 2>&1; then
    echo "==> 构建前端"
    (cd frontend && pnpm install && pnpm build)
  else
    echo "!! 未找到 frontend/dist，且本机没有 pnpm，将只能访问 API（/api/v1/docs）"
  fi
fi

echo ""
echo "==> 服务启动中：http://127.0.0.1:${PORT}"
echo "    演示账号：20223601 / Abc123456   （宿管 admin / Admin@123）"
echo "    API 文档：http://127.0.0.1:${PORT}/api/v1/docs"
echo "    按 Ctrl+C 停止"
echo ""

cd backend
exec "$RUN_PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
