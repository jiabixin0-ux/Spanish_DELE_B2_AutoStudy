"""Prompt construction for daily Spanish study lessons."""

from __future__ import annotations

from collections.abc import Iterable


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return len(value) == 0
    except TypeError:
        return False


def _format_item(item) -> str:
    if isinstance(item, dict):
        parts = []
        for key, value in item.items():
            if _is_empty(value):
                continue
            parts.append(f"{key}: {value}")
        return "; ".join(parts) if parts else str(item)

    if isinstance(item, (list, tuple, set)):
        return " / ".join(str(part) for part in item if not _is_empty(part))

    return str(item)


def _format_items(items, empty_text: str = "无") -> str:
    if _is_empty(items):
        return empty_text

    if isinstance(items, str):
        return items.strip()

    if isinstance(items, dict):
        lines = []
        for key, value in items.items():
            if _is_empty(value):
                continue
            lines.append(f"- {key}: {_format_item(value)}")
        return "\n".join(lines) if lines else empty_text

    if isinstance(items, Iterable):
        lines = []
        for item in items:
            if _is_empty(item):
                continue
            lines.append(f"- {_format_item(item)}")
        return "\n".join(lines) if lines else empty_text

    return str(items)


def build_daily_lesson_prompt(
    day_number: int,
    date_str: str,
    reading_text: str,
    vocabulary_items=None,
    phrase_items=None,
    grammar_focus=None,
    review_items=None,
) -> str:
    """Build the user prompt for one daily Spanish lesson."""
    reading_text = reading_text.strip() if reading_text else ""
    reading_block = (
        reading_text
        if reading_text
        else "【今日 PDF 精读原文为空。必须明确说明未提供 PDF 原文；不要编造西语原文，也不要编造对应翻译。】"
    )

    grammar_block = _format_items(grammar_focus, empty_text="无指定语法点，请从原文中选择 1 个适合 B1 的语法点。")

    return f"""请根据下面输入，为中文母语者生成一份西班牙语每日学习内容。当前目标是先巩固 B1，再逐步过渡到 B2。

基本信息：
- Day number: {day_number}
- 日期: {date_str}

核心输入：今日 PDF 精读西语原文
{reading_block}

可参考的知识库词汇候选：
{_format_items(vocabulary_items)}

可参考的知识库词组候选：
{_format_items(phrase_items)}

今日语法点候选：
{grammar_block}

间隔复习候选：
{_format_items(review_items)}

生成要求：
- 必须输出 Markdown。
- 必须严格使用下面 11 个一级/二级标题结构，不要增删章节，不要改变标题文字。
- 不要输出代码块。
- 不要提到“我是 AI”。
- 内容适合邮件和 Word 阅读。
- 难度以 B1 为主，可以少量加入 B2 表达，但必须解释清楚。
- 用户词汇量偏弱，词汇和搭配解释要清楚、实用。
- 语法说明不要太学术、太难。
- PDF 精读部分必须以“核心输入”中的西语原文为准。
- “西语原文”必须保留当天原文，不要改写；如果原文为空，必须说明未提供原文，且不要编造。
- “中文翻译”必须逐段准确对应西语原文，不能生成与原文无关的中文内容；如果原文为空，不要编造翻译。
- 词汇、词组、句型、测试应优先围绕 PDF 原文和候选材料生成。

必须严格输出以下结构：

# 西语 B1 巩固与 B2 过渡 - Día {day_number}

## 1. 今日学习目标
- 用中文写 3 条具体目标。

## 2. PDF 精读：西语原文 + 准确中文翻译
### 西语原文
保留当天西语原文，不要改写。
### 中文翻译
必须逐段准确翻译西语原文，不能生成与原文无关的中文内容。

## 3. 逐句重点讲解
选择 3-6 个关键句，解释词义、结构和表达。

## 4. 今日核心词汇：25-35 个
每个词汇包含：
- 西语词
- 中文意思
- 常用搭配
- 简单例句
- 例句中文翻译

## 5. 高频词组：10-15 个
每个词组包含：
- 西语词组
- 中文意思
- 例句
- 例句中文翻译

## 6. 实用句型：3-5 个
每个句型包含：
- 句型结构
- 中文意思
- 西语例句
- 中文翻译

## 7. 今日语法小点：1 个
只讲一个适合 B1 的语法点，讲清楚但不要过难。

## 8. 轻量输出训练
给出 3 个中文句子，让用户用西语表达。

## 9. 间隔复习
复习旧词、旧词组或旧句型，数量适中。

## 10. 今日小测试：5 题
题型可以包括选择、填空、翻译、改写。

## 11. 答案与解析
给出全部答案和简短解析。"""
