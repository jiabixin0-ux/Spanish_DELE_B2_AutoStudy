from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MATERIALS_DIR = PROJECT_ROOT / "materials"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
DAILY_OUTPUT_DIR = OUTPUT_DIR / "daily"
LOG_DIR = PROJECT_ROOT / "logs"

DEFAULT_PDF = MATERIALS_DIR / "dele_material.pdf"
DEFAULT_PAGES_JSONL = RAW_DIR / "dele_material_pages.jsonl"
DEFAULT_TEXT = RAW_DIR / "dele_material.txt"
DEFAULT_KNOWLEDGE_BASE = PROCESSED_DIR / "knowledge_base.json"
DEFAULT_PROGRESS = DATA_DIR / "progress.json"
DEFAULT_REVIEW_CARDS = DATA_DIR / "review_cards.json"


def ensure_project_dirs() -> None:
    for path in (RAW_DIR, PROCESSED_DIR, DAILY_OUTPUT_DIR, LOG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in ("", None) else default
