from __future__ import annotations

import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DISPLAY_PATH = Path("output") / "daily_lesson.md"
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dele_b2_auto_study import generate_daily, pdf_extract, split_knowledge


REQUIRED_SECTIONS = (
    "今日学习目标",
    "输入部分：先理解",
    "核心词汇与词组",
    "高频句型",
    "语法重点",
    "精读段落",
    "输出部分：再练习",
    "分级输出练习",
    "今日小测试",
    "答案与解析",
    "间隔复习",
)


def validate_lesson_structure(markdown: str) -> None:
    missing = [section for section in REQUIRED_SECTIONS if section not in markdown]
    if missing:
        raise ValueError("每日学习内容结构不完整，缺少：" + "、".join(missing))


def main() -> int:
    pdf_status = pdf_extract.main()
    if pdf_status != 0:
        return pdf_status

    split_status = split_knowledge.main()
    if split_status != 0:
        return split_status

    generate_status = generate_daily.main()
    if generate_status != 0:
        return generate_status

    latest_lesson = PROJECT_ROOT / "output" / "daily" / "latest_lesson.md"
    daily_lesson = PROJECT_ROOT / "output" / "daily_lesson.md"
    if not latest_lesson.exists():
        raise FileNotFoundError("Missing generated lesson: output/daily/latest_lesson.md")

    validate_lesson_structure(latest_lesson.read_text(encoding="utf-8"))
    daily_lesson.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(latest_lesson, daily_lesson)
    print(f"已生成每日学习内容：{OUTPUT_DISPLAY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
