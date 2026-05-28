from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from dele_b2_auto_study.generate_daily import build_lesson, choose_lesson_day
from dele_b2_auto_study.split_knowledge import build_knowledge_base, classify_chunk, extract_terms


class KnowledgeSplitTests(unittest.TestCase):
    def test_classifies_grammar_chunk(self) -> None:
        labels = classify_chunk("El subjuntivo se usa para expresar duda y valoración.")
        self.assertIn("gramática", labels)

    def test_extracts_relevant_terms(self) -> None:
        terms = extract_terms("argumentar argumentar propuesta conectores vocabulario", limit=3)
        self.assertEqual(terms[0], "argumentar")

    def test_builds_b2_plan_from_pages(self) -> None:
        pages = [
            {
                "page": 1,
                "text": "Subjuntivo y opinión\n\nNo creo que sea fácil, aunque conviene practicar.",
            },
            {
                "page": 2,
                "text": "Texto de lectura\n\nEste fragmento sirve para argumentar ventajas e inconvenientes.",
            },
        ]
        kb = build_knowledge_base(pages)
        self.assertGreater(kb["chunk_count"], 0)
        self.assertEqual(kb["target_level"], "DELE B2")
        self.assertTrue(kb["course_plan"][0]["source_chunk_ids"])


class DailyLessonTests(unittest.TestCase):
    def test_choose_lesson_day_is_date_based(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.json"
            day, state = choose_lesson_day(progress, date(2026, 5, 27), None, 10)
            self.assertEqual(day, 1)
            progress.write_text(json.dumps(state), encoding="utf-8")
            next_day, _ = choose_lesson_day(progress, date(2026, 5, 28), None, 10)
            self.assertEqual(next_day, 2)

    def test_choose_lesson_day_is_stable_without_progress_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "missing-progress.json"
            first_day, _ = choose_lesson_day(progress, date(2026, 5, 27), None, 10)
            second_day, _ = choose_lesson_day(progress, date(2026, 5, 28), None, 10)
            eleventh_day, state = choose_lesson_day(progress, date(2026, 6, 6), None, 10)
            self.assertEqual(first_day, 1)
            self.assertEqual(second_day, 2)
            self.assertEqual(eleventh_day, 11)
            self.assertEqual(state["cycle_day_number"], 1)

    def test_choose_lesson_day_clamps_old_local_start_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.json"
            progress.write_text(json.dumps({"start_date": "2026-05-26"}), encoding="utf-8")
            day, state = choose_lesson_day(progress, date(2026, 5, 28), None, 10)
            self.assertEqual(day, 2)
            self.assertEqual(state["start_date"], "2026-05-27")

    def test_lesson_contains_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = build_knowledge_base(
                [
                    {
                        "page": 1,
                        "text": "Aunque el tema parece sencillo, conviene argumentar con ejemplos concretos. "
                        "El texto propone comparar ventajas e inconvenientes y expresar una opinión matizada.",
                    }
                ]
            )
            cards_path = Path(tmp) / "cards.json"
            lesson = build_lesson(kb, 1, date(2026, 5, 26), cards_path)
            markdown = lesson["markdown"]
            for section in (
                "今日学习目标",
                "输入部分：先理解",
                "词汇",
                "句型",
                "语法",
                "精读",
                "分级输出练习",
                "写作任务",
                "小测试",
                "答案",
                "间隔复习",
            ):
                self.assertIn(section, markdown)

    def test_spaced_review_is_generated_from_dates_without_cards_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = build_knowledge_base(
                [
                    {
                        "page": 1,
                        "text": "Aunque el tema parece sencillo, conviene argumentar con ejemplos concretos. "
                        "El texto propone comparar ventajas e inconvenientes y expresar una opinión matizada.",
                    }
                ]
            )
            lesson = build_lesson(kb, 8, date(2026, 6, 3), Path(tmp) / "missing-cards.json")
            markdown = lesson["markdown"]
            self.assertIn("昨天 2 个词组", markdown)
            self.assertIn("3 天前 1 个句型", markdown)
            self.assertIn("7 天前 1 个语法点", markdown)
            self.assertIn("Día 1", markdown)
            self.assertNotIn("暂无对应日期的复习卡", markdown)

    def test_repeated_cycle_day_still_changes_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kb = build_knowledge_base(
                [
                    {
                        "page": 1,
                        "text": "Aunque el tema parece sencillo, conviene argumentar con ejemplos concretos. "
                        "El texto propone comparar ventajas e inconvenientes y expresar una opinión matizada.",
                    }
                ]
            )
            cards_path = Path(tmp) / "cards.json"
            first_cycle = build_lesson(kb, 1, date(2026, 5, 27), cards_path)["markdown"]
            second_cycle = build_lesson(kb, 11, date(2026, 6, 6), cards_path)["markdown"]
            self.assertIn("Día 1", first_cycle)
            self.assertIn("Día 11", second_cycle)
            self.assertNotEqual(first_cycle, second_cycle)


if __name__ == "__main__":
    unittest.main()
