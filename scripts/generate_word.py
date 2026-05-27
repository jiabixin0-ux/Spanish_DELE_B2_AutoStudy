from __future__ import annotations

import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VENDOR_DIR = PROJECT_ROOT / "vendor"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt


MARKDOWN_PATH = PROJECT_ROOT / "output" / "daily_lesson.md"
DOCX_PATH = PROJECT_ROOT / "output" / "daily_lesson.docx"
MARKDOWN_DISPLAY_PATH = Path("output") / "daily_lesson.md"
DOCX_DISPLAY_PATH = Path("output") / "daily_lesson.docx"


def set_run_font(run, size_pt: float = 11.0, bold: bool = False) -> None:
    run.font.name = "Arial"
    run.font.size = Pt(size_pt)
    run.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "PingFang SC")


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "PingFang SC")
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for style_name, size, space_before, space_after in (
        ("Heading 1", 20, 0, 12),
        ("Heading 2", 15, 12, 6),
    ):
        style = styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.bold = True
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "PingFang SC")
        style.paragraph_format.space_before = Pt(space_before)
        style.paragraph_format.space_after = Pt(space_after)


def strip_markdown_emphasis(text: str) -> str:
    text = text.replace("`", "")
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    return text.strip()


def add_text_paragraph(document: Document, text: str, style: str | None = None) -> None:
    paragraph = document.add_paragraph(style=style)
    paragraph.paragraph_format.space_after = Pt(6)
    for index, part in enumerate(split_spanish_chinese(text)):
        if index:
            paragraph.add_run().add_break()
        run = paragraph.add_run(part)
        set_run_font(run)


def add_list_paragraph(document: Document, text: str, numbered: bool = False) -> None:
    paragraph = document.add_paragraph(style="List Number" if numbered else "List Bullet")
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.left_indent = Inches(0.25)
    for index, part in enumerate(split_spanish_chinese(strip_markdown_emphasis(text))):
        if index:
            paragraph.add_run().add_break()
        run = paragraph.add_run(part)
        set_run_font(run)


def split_spanish_chinese(text: str) -> list[str]:
    text = strip_markdown_emphasis(text)
    if "：" in text:
        left, right = text.split("：", 1)
        if re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", left) and re.search(r"[\u4e00-\u9fff]", right):
            return [left.strip() + "：", right.strip()]
    if " - " in text:
        left, right = text.split(" - ", 1)
        if re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", left) and re.search(r"[\u4e00-\u9fff]", right):
            return [left.strip(), right.strip()]
    return [text]


def add_blockquote(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.left_indent = Inches(0.25)
    paragraph.paragraph_format.right_indent = Inches(0.1)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(8)
    p_pr = paragraph._p.get_or_add_pPr()
    border = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "12")
    left.set(qn("w:space"), "6")
    left.set(qn("w:color"), "B7C4D6")
    border.append(left)
    p_pr.append(border)
    run = paragraph.add_run(strip_markdown_emphasis(text))
    set_run_font(run, size_pt=10.5)
    run.italic = True


def markdown_to_docx(markdown: str, output_path: Path) -> None:
    document = Document()
    configure_document(document)

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# "):
            paragraph = document.add_heading(strip_markdown_emphasis(line[2:]), level=1)
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            continue
        if line.startswith("## "):
            document.add_heading(strip_markdown_emphasis(line[3:]), level=2)
            continue
        if line.startswith("- "):
            add_list_paragraph(document, line[2:], numbered=False)
            continue
        numbered_match = re.match(r"^(\d+)\.\s+(.*)$", line)
        if numbered_match:
            add_list_paragraph(document, numbered_match.group(2), numbered=True)
            continue
        if line.startswith("> "):
            add_blockquote(document, line[2:])
            continue
        add_text_paragraph(document, line)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def main() -> int:
    if not MARKDOWN_PATH.exists():
        raise SystemExit(f"缺少 {MARKDOWN_DISPLAY_PATH}，请先运行 scripts/generate_daily_lesson.py")
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    markdown_to_docx(markdown, DOCX_PATH)
    print(f"已生成 Word 附件：{DOCX_DISPLAY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
