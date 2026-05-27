from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from .config import DEFAULT_KNOWLEDGE_BASE, DEFAULT_PAGES_JSONL, display_path, ensure_project_dirs


SPANISH_WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}")
HEADING_RE = re.compile(r"^([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9 .,:;¿?¡!-]{2,70})$")

STOPWORDS = {
    "para",
    "como",
    "pero",
    "porque",
    "esta",
    "este",
    "estos",
    "estas",
    "también",
    "tiene",
    "tienen",
    "desde",
    "hasta",
    "sobre",
    "entre",
    "donde",
    "cuando",
    "todo",
    "todos",
    "todas",
    "algo",
    "muy",
    "más",
    "menos",
    "cada",
    "puede",
    "pueden",
    "hacer",
    "tener",
    "usted",
    "ustedes",
    "página",
    "texto",
    "tema",
    "claro",
    "algún",
    "llamo",
    "dicho",
    "hecho",
}

CLASS_KEYWORDS = {
    "gramática": {
        "subjuntivo",
        "indicativo",
        "pretérito",
        "imperfecto",
        "condicional",
        "pronombres",
        "ser",
        "estar",
        "por",
        "para",
        "oración",
        "concordancia",
        "verbo",
        "tiempo",
    },
    "vocabulario": {
        "vocabulario",
        "léxico",
        "palabras",
        "expresiones",
        "sinónimo",
        "antónimo",
        "familia",
        "definición",
    },
    "funciones": {
        "opinar",
        "pedir",
        "aconsejar",
        "argumentar",
        "expresar",
        "proponer",
        "reclamar",
        "solicitar",
    },
    "lectura": {
        "texto",
        "leer",
        "lectura",
        "comprensión",
        "artículo",
        "noticia",
        "fragmento",
        "preguntas",
    },
}


B2_SYLLABUS = [
    {
        "title": "Opinar y matizar en temas cotidianos",
        "focus": "conectores de opinión, contraste y matización",
        "b2_goal": "defender una postura con matices y ejemplos concretos",
        "keywords": ["opinar", "creo", "pienso", "aunque", "sin embargo", "argumentar"],
    },
    {
        "title": "Subjuntivo para valoración y duda",
        "focus": "es importante que, dudo que, no creo que + subjuntivo",
        "b2_goal": "formular valoraciones personales con precisión",
        "keywords": ["subjuntivo", "duda", "valoración", "creer", "importante"],
    },
    {
        "title": "Narrar experiencias y cambios",
        "focus": "pretérito, imperfecto, pluscuamperfecto y marcadores temporales",
        "b2_goal": "contar una experiencia organizada y relevante para el examen oral",
        "keywords": ["pretérito", "imperfecto", "experiencia", "antes", "después"],
    },
    {
        "title": "Contrastar ventajas e inconvenientes",
        "focus": "por una parte, en cambio, no obstante, mientras que",
        "b2_goal": "comparar opciones sin sonar demasiado simple",
        "keywords": ["ventajas", "inconvenientes", "contraste", "comparar", "mientras"],
    },
    {
        "title": "Expresar hipótesis y condiciones",
        "focus": "si + imperfecto de subjuntivo, condicional, quizá, tal vez",
        "b2_goal": "hablar de escenarios posibles con control gramatical",
        "keywords": ["condicional", "hipótesis", "quizá", "tal vez", "si"],
    },
    {
        "title": "Escribir correos formales",
        "focus": "solicitar, reclamar, agradecer, despedidas formales",
        "b2_goal": "producir un texto claro, cortés y con objetivo comunicativo",
        "keywords": ["correo", "carta", "solicitar", "reclamar", "agradecer"],
    },
    {
        "title": "Conectores para organizar argumentos",
        "focus": "en primer lugar, además, por consiguiente, en definitiva",
        "b2_goal": "mejorar cohesión en escritura y oralidad",
        "keywords": ["conectores", "además", "consiguiente", "definitiva", "organizar"],
    },
    {
        "title": "Describir datos, tendencias y cambios sociales",
        "focus": "aumentar, disminuir, mantenerse, en comparación con",
        "b2_goal": "explicar información visual o abstracta con vocabulario preciso",
        "keywords": ["datos", "aumentar", "disminuir", "comparación", "sociedad"],
    },
    {
        "title": "Reformular y evitar repeticiones",
        "focus": "es decir, o sea, dicho de otro modo, el cual, la cual",
        "b2_goal": "ganar fluidez y variedad sintáctica",
        "keywords": ["reformular", "decir", "modo", "cual", "pronombres"],
    },
    {
        "title": "Debatir soluciones y propuestas",
        "focus": "debería, convendría, sería recomendable que + subjuntivo",
        "b2_goal": "presentar propuestas realistas y justificadas",
        "keywords": ["proponer", "solución", "debería", "recomendable", "aconsejar"],
    },
]


def load_pages(path: Path) -> list[dict[str, object]]:
    pages: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            if int(record.get("page", 0)) > 0 and str(record.get("text", "")).strip():
                pages.append(record)
    return pages


def split_page_into_chunks(page: int, text: str, max_chars: int = 1800) -> list[dict[str, object]]:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks: list[dict[str, object]] = []
    current: list[str] = []
    heading = ""

    for paragraph in paragraphs:
        if HEADING_RE.match(paragraph) and len(paragraph.split()) <= 10:
            heading = paragraph
        if sum(len(p) for p in current) + len(paragraph) > max_chars and current:
            chunks.append({"page_start": page, "page_end": page, "heading": heading, "text": "\n\n".join(current)})
            current = []
        current.append(paragraph)

    if current:
        chunks.append({"page_start": page, "page_end": page, "heading": heading, "text": "\n\n".join(current)})
    return chunks


def classify_chunk(text: str) -> list[str]:
    lowered = text.lower()
    scores: Counter[str] = Counter()
    for label, keywords in CLASS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[label] += 1
    if not scores:
        return ["lectura"]
    return [label for label, _score in scores.most_common(3)]


def extract_terms(text: str, limit: int = 12) -> list[str]:
    words = [w.lower() for w in SPANISH_WORD_RE.findall(text)]
    counts = Counter(w for w in words if w not in STOPWORDS and len(w) > 4)
    return [word for word, _count in counts.most_common(limit)]


def score_chunk_for_topic(chunk: dict[str, object], topic: dict[str, object]) -> int:
    text = str(chunk["text"]).lower()
    score = 0
    for keyword in topic["keywords"]:
        score += text.count(str(keyword).lower()) * 3
    for category in chunk["categories"]:
        if category in {"gramática", "funciones", "lectura"}:
            score += 1
    return score


def build_knowledge_base(pages: list[dict[str, object]]) -> dict[str, object]:
    chunks: list[dict[str, object]] = []
    for page in pages:
        for chunk in split_page_into_chunks(int(page["page"]), str(page["text"])):
            chunk_id = f"chunk-{len(chunks) + 1:05d}"
            chunk["id"] = chunk_id
            chunk["categories"] = classify_chunk(str(chunk["text"]))
            chunk["terms"] = extract_terms(str(chunk["text"]))
            chunks.append(chunk)

    plan = []
    for index, topic in enumerate(B2_SYLLABUS, start=1):
        ranked = sorted(
            chunks,
            key=lambda item: (score_chunk_for_topic(item, topic), -int(item["page_start"])),
            reverse=True,
        )
        source_ids = [str(item["id"]) for item in ranked[:8]]
        plan.append({**topic, "day_in_cycle": index, "source_chunk_ids": source_ids})

    return {
        "version": 1,
        "source_level": "B1 aproximadamente",
        "target_level": "DELE B2",
        "strategy": "The source PDF is reorganized by communicative and grammar goals instead of page order.",
        "chunk_count": len(chunks),
        "chunks": chunks,
        "course_plan": plan,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Split extracted PDF text into a B2-oriented knowledge base.")
    parser.add_argument("--input", type=Path, default=DEFAULT_PAGES_JSONL)
    parser.add_argument("--output", type=Path, default=DEFAULT_KNOWLEDGE_BASE)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    ensure_project_dirs()
    if not args.input.exists():
        print(f"缺少 PDF 提取结果：{display_path(args.input)}", file=sys.stderr)
        return 1
    if args.output.exists() and not args.force:
        print(f"已存在知识库，跳过：{display_path(args.output)}")
        return 0

    pages = load_pages(args.input)
    knowledge_base = build_knowledge_base(pages)
    args.output.write_text(json.dumps(knowledge_base, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成知识库：{display_path(args.output)}，共 {knowledge_base['chunk_count']} 个知识块")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
