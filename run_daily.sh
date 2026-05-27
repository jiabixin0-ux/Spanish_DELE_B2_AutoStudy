#!/bin/zsh
set -e
set -u
set -o pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

exec >> "cron.log" 2>&1

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 开始每日 DELE B2 自动学习任务 ====="

export PYTHONPATH="$PROJECT_DIR/src"

python3 scripts/generate_daily_lesson.py
python3 scripts/generate_word.py
python3 scripts/send_email.py

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 每日任务完成 ====="
