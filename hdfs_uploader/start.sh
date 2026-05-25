#!/usr/bin/env bash
# ── 一键启动脚本 ──────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== DataPipe · HDFS 上传平台 ==="

# 检查 Python 版本
python3 --version || { echo "需要 Python 3.10+"; exit 1; }

# 安装依赖（首次运行）
if [ ! -d ".venv" ]; then
  echo ">> 创建虚拟环境..."
  python3 -m venv .venv
fi

echo ">> 激活虚拟环境..."
source .venv/bin/activate

echo ">> 安装依赖..."
pip install --quiet -r requirements.txt

# 创建上传目录
mkdir -p uploads

echo ">> 启动 Flask 服务 (http://0.0.0.0:5000)"
echo "   访问地址: http://localhost:5000"
echo ""
python3 app.py
