#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# DataPipe · HDFS 上传平台 · 一键启动脚本
# ─────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╔════════════════════════════════════════════════════════╗"
echo "║      DataPipe · HDFS 数据清洗上传平台  v1.0            ║"
echo "╚════════════════════════════════════════════════════════╝"

# 检查 Python 版本
echo ">> 检查 Python 版本..."
python3 --version || { echo "❌ 需要 Python 3.10+"; exit 1; }

# 创建虚拟环境
if [ ! -d ".venv" ]; then
  echo ">> 创建虚拟环境..."
  python3 -m venv .venv
fi

# 激活虚拟环境
echo ">> 激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo ">> 安装依赖包..."
pip install --quiet -r requirements.txt

# 创建必要的目录
echo ">> 创建应用目录..."
mkdir -p uploads scripts

# 创建 .env 配置文件（如果不存在）
if [ ! -f ".env" ]; then
  echo ">> 创建 .env 配置文件..."
  cp .env.example .env
  echo "⚠️  请编辑 .env 文件配置 HDFS 和 MySQL 参数"
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║                 🚀 启动应用服务器                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "✨ Flask 服务已启动"
echo "   访问地址: http://localhost:5000"
echo "   上传页面: http://localhost:5000"
echo "   看板页面: http://localhost:5000/dashboard"
echo ""
echo "📝 日志输出:"
echo ""

# 启动应用
python3 app.py
