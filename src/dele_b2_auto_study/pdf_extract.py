from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .config import DEFAULT_PDF, DEFAULT_PAGES_JSONL, DEFAULT_TEXT, display_path, ensure_project_dirs


SPACE_RE = re.compile(r"[ \t]+")
LINE_RE = re.compile(r"\n{3,}")
CONTROL_RE = re.compile(r"[\x01-\x08\x0b\x0c\x0e-\x1f]")


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = CONTROL_RE.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(SPACE_RE.sub(" ", line).strip() for line in text.splitlines())
    return LINE_RE.sub("\n\n", text).strip()


def extract_pages(pdf_path: Path) -> list[dict[str, object]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit(
            "缺少依赖 pypdf。请先运行：python3 -m pip install -r requirements.txt"
        ) from exc

    reader = PdfReader(str(pdf_path))
    pages: list[dict[str, object]] = []
    for index, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        pages.append(
            {
                "page": index,
                "text": normalize_text(raw),
                "char_count": len(raw),
            }
        )
    return pages


def write_jsonl(records: Iterable[dict[str, object]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_full_text(pages: list[dict[str, object]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for page in pages:
            fh.write(f"\n\n===== Página {page['page']} =====\n\n")
            fh.write(str(page["text"]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from the DELE source PDF.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--pages-jsonl", type=Path, default=DEFAULT_PAGES_JSONL)
    parser.add_argument("--text-output", type=Path, default=DEFAULT_TEXT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    ensure_project_dirs()
    if not args.pdf.exists():
        print(f"PDF 不存在：{display_path(args.pdf)}", file=sys.stderr)
        return 1

    if args.pages_jsonl.exists() and args.text_output.exists() and not args.force:
        print(f"已存在提取结果，跳过：{display_path(args.pages_jsonl)}")
        return 0

    pages = extract_pages(args.pdf)
    metadata = {
        "page": 0,
        "text": "",
        "metadata": {
            "source_pdf": display_path(args.pdf),
            "extracted_at": datetime.now().isoformat(timespec="seconds"),
            "page_count": len(pages),
        },
    }
    write_jsonl([metadata, *pages], args.pages_jsonl)
    write_full_text(pages, args.text_output)
    print(f"已提取 {len(pages)} 页：{display_path(args.pages_jsonl)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
