from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import (
    DAILY_OUTPUT_DIR,
    DEFAULT_KNOWLEDGE_BASE,
    DEFAULT_PROGRESS,
    DEFAULT_REVIEW_CARDS,
    display_path,
    ensure_project_dirs,
)
from .split_knowledge import extract_terms


B2_VOCAB_BANK = {
    "Opinar y matizar en temas cotidianos": [
        "matizar", "plantear", "sostener", "poner en duda", "resultar convincente",
        "a grandes rasgos", "desde mi punto de vista", "no obstante", "cabe destacar que",
        "tener en cuenta", "por una parte", "por otra parte", "llegar a la conclusión de que",
        "ser consciente de", "en definitiva",
    ],
    "Subjuntivo para valoración y duda": [
        "es probable que", "dudo que", "me sorprende que", "conviene que",
        "resulta imprescindible que", "no cabe duda de que", "es posible que",
        "es necesario que", "no parece que", "ojalá", "temo que", "a menos que",
        "siempre que", "antes de que", "para que",
    ],
    "Narrar experiencias y cambios": [
        "atravesar una etapa", "darse cuenta de", "solía", "a raíz de",
        "con el paso del tiempo", "marcar un antes y un después", "al principio",
        "más adelante", "acostumbrarse a", "cambiar de opinión", "superar una dificultad",
        "recordar con claridad", "poco a poco", "desde entonces", "al final",
    ],
    "Contrastar ventajas e inconvenientes": [
        "por un lado", "por otro lado", "a diferencia de", "en comparación con",
        "suponer una ventaja", "tener el inconveniente de", "merecer la pena",
        "a corto plazo", "a largo plazo", "depender de", "compensar", "resultar práctico",
        "presentar una desventaja", "en cambio", "a pesar de ello",
    ],
    "Expresar hipótesis y condiciones": [
        "si tuviera que", "en caso de que", "siempre que", "a menos que",
        "sería conveniente", "cabría esperar que", "por si acaso", "en el supuesto de que",
        "dependería de", "si fuera posible", "probablemente", "tal vez", "si se diera el caso",
        "bajo ciertas condiciones", "de ser así",
    ],
    "Escribir correos formales": [
        "me dirijo a usted", "quisiera solicitar", "les agradecería que", "quedo a la espera",
        "atentamente", "por medio de la presente", "con respecto a", "adjuntar",
        "solicitar información", "a la mayor brevedad posible", "lamentar las molestias",
        "recibir una respuesta", "ponerse en contacto", "hacer constar", "estimado/a",
    ],
    "Conectores para organizar argumentos": [
        "en primer lugar", "además", "por consiguiente", "en definitiva", "no obstante",
        "cabe destacar que", "por una parte", "por otra parte", "en cambio", "de hecho",
        "por ejemplo", "a pesar de ello", "por lo tanto", "sin embargo", "en resumen",
    ],
    "Describir datos, tendencias y cambios sociales": [
        "aumentar", "disminuir", "mantenerse estable", "tendencia al alza", "brecha",
        "en términos generales", "según los datos", "porcentaje", "la mayoría de",
        "una minoría", "notable", "a lo largo de", "cifra", "evolución", "factor",
    ],
    "Reformular y evitar repeticiones": [
        "es decir", "dicho de otro modo", "lo cual", "respectivamente", "en otras palabras",
        "hacer referencia a", "este aspecto", "dicha situación", "evitar repetir",
        "resumir", "aclarar", "matizar una idea", "reformular", "concretamente", "en este sentido",
    ],
    "Debatir soluciones y propuestas": [
        "proponer", "llevar a cabo", "poner en marcha", "sería recomendable que",
        "hacer frente a", "tomar medidas", "resolver un problema", "mejorar la situación",
        "colaborar", "recursos disponibles", "priorizar", "evaluar los resultados",
        "buscar una alternativa", "alcanzar un acuerdo", "tener impacto",
    ],
}

GRAMMAR_PROMPTS = {
    "subjuntivo": "Recuerda: después de valoración, duda o recomendación suele aparecer subjuntivo: Es importante que practiques.",
    "condicional": "Usa condicional para propuestas diplomáticas: Sería útil revisar este punto antes del examen.",
    "conectores": "En B2 no basta con unir frases; necesitas jerarquía: aunque, sin embargo, por consiguiente, en definitiva.",
    "narración": "Alterna pretérito para hechos terminados e imperfecto para contexto, hábitos o descripciones.",
}

VOCAB_MEANINGS = {
    "matizar": "使观点更细致、补充限制", "plantear": "提出问题、观点或方案", "sostener": "坚持、主张某种看法",
    "poner en duda": "质疑、对某事表示怀疑", "resultar convincente": "显得有说服力", "a grandes rasgos": "大体上、概括地说",
    "desde mi punto de vista": "在我看来", "no obstante": "然而、不过", "cabe destacar que": "值得强调的是",
    "tener en cuenta": "考虑到", "por una parte": "一方面", "por otra parte": "另一方面",
    "llegar a la conclusión de que": "得出……结论", "ser consciente de": "意识到", "en definitiva": "总之",
    "es probable que": "很可能……", "dudo que": "我怀疑……、我不认为……", "me sorprende que": "让我惊讶的是……",
    "conviene que": "最好……、有必要……", "resulta imprescindible que": "……是必不可少的", "no cabe duda de que": "毫无疑问……",
    "es posible que": "有可能……", "es necesario que": "有必要……", "no parece que": "看起来不像……",
    "ojalá": "但愿、希望", "temo que": "我担心……", "a menos que": "除非……",
    "siempre que": "只要……", "antes de que": "在……之前", "para que": "为了……",
    "atravesar una etapa": "经历一个阶段", "darse cuenta de": "意识到", "solía": "过去常常",
    "a raíz de": "由于……、在……之后", "con el paso del tiempo": "随着时间推移", "marcar un antes y un después": "成为转折点",
    "al principio": "起初", "más adelante": "后来", "acostumbrarse a": "习惯于",
    "cambiar de opinión": "改变看法", "superar una dificultad": "克服困难", "recordar con claridad": "清楚地记得",
    "poco a poco": "一点一点地", "desde entonces": "从那以后", "al final": "最后",
    "por un lado": "一方面", "por otro lado": "另一方面", "a diferencia de": "与……不同",
    "en comparación con": "与……相比", "suponer una ventaja": "构成一个优点", "tener el inconveniente de": "有……缺点",
    "merecer la pena": "值得", "a corto plazo": "短期来看", "a largo plazo": "长期来看",
    "depender de": "取决于", "compensar": "弥补、值得", "resultar práctico": "显得实用",
    "presentar una desventaja": "呈现一个缺点", "en cambio": "相反、而", "a pesar de ello": "尽管如此",
    "si tuviera que": "如果我必须……", "en caso de que": "如果……的话", "sería conveniente": "比较合适的是……",
    "cabría esperar que": "可以期待/推测……", "por si acaso": "以防万一", "en el supuesto de que": "假设……",
    "dependería de": "将取决于……", "si fuera posible": "如果可能的话", "probablemente": "很可能",
    "tal vez": "也许", "si se diera el caso": "如果出现这种情况", "bajo ciertas condiciones": "在某些条件下",
    "de ser así": "如果是这样", "me dirijo a usted": "我写信给您", "quisiera solicitar": "我想申请/请求",
    "les agradecería que": "如能……我将非常感谢", "quedo a la espera": "期待您的回复", "atentamente": "此致、谨上",
    "por medio de la presente": "通过此信", "con respecto a": "关于", "adjuntar": "附上",
    "solicitar información": "请求信息", "a la mayor brevedad posible": "尽快", "lamentar las molestias": "为不便表示抱歉",
    "recibir una respuesta": "收到回复", "ponerse en contacto": "联系", "hacer constar": "说明、记录",
    "estimado/a": "尊敬的", "en primer lugar": "首先", "además": "此外", "por consiguiente": "因此",
    "de hecho": "事实上", "por ejemplo": "例如", "por lo tanto": "因此", "sin embargo": "然而",
    "en resumen": "总结来说", "aumentar": "增加", "disminuir": "减少", "mantenerse estable": "保持稳定",
    "tendencia al alza": "上升趋势", "brecha": "差距", "en términos generales": "总体而言",
    "según los datos": "根据数据", "porcentaje": "百分比", "la mayoría de": "大多数",
    "una minoría": "少数", "notable": "显著的", "a lo largo de": "在……期间",
    "cifra": "数字、数据", "evolución": "演变、变化趋势", "factor": "因素",
    "es decir": "也就是说", "dicho de otro modo": "换句话说", "lo cual": "这一点",
    "respectivamente": "分别地", "en otras palabras": "换句话说", "hacer referencia a": "指的是、提到",
    "este aspecto": "这一方面", "dicha situación": "上述情况", "evitar repetir": "避免重复",
    "resumir": "总结", "aclarar": "澄清", "matizar una idea": "细化一个观点",
    "reformular": "重新表述", "concretamente": "具体来说", "en este sentido": "在这个意义上",
    "proponer": "提出", "llevar a cabo": "实施、开展", "poner en marcha": "启动",
    "sería recomendable que": "建议……", "hacer frente a": "应对", "tomar medidas": "采取措施",
    "resolver un problema": "解决问题", "mejorar la situación": "改善情况", "colaborar": "合作",
    "recursos disponibles": "可用资源", "priorizar": "优先考虑", "evaluar los resultados": "评估结果",
    "buscar una alternativa": "寻找替代方案", "alcanzar un acuerdo": "达成一致", "tener impacto": "产生影响",
}

RELATED_EXPRESSIONS = {
    "es probable que": "puede que / quizás", "dudo que": "no creo que", "conviene que": "es aconsejable que",
    "resulta imprescindible que": "es fundamental que", "no cabe duda de que": "es evidente que",
    "a menos que": "salvo que", "siempre que": "con la condición de que", "para que": "con el fin de que",
    "no obstante": "sin embargo", "en definitiva": "en resumen", "por consiguiente": "por lo tanto",
    "dicho de otro modo": "en otras palabras", "matizar": "precisar", "plantear": "presentar / proponer",
    "sostener": "defender", "hacer frente a": "afrontar", "tomar medidas": "adoptar medidas",
}

EXAMPLE_OVERRIDES = {
    "es probable que": ("Es probable que muchas personas prefieran estudiar con ejemplos claros.", "很多人可能更喜欢用清楚的例子来学习。"),
    "dudo que": ("Dudo que sea eficaz memorizar reglas sin practicar frases completas.", "我怀疑只背规则而不练完整句是否有效。"),
    "me sorprende que": ("Me sorprende que el texto explique un tema difícil con palabras sencillas.", "让我惊讶的是，这篇文本用简单的话解释了一个难题。"),
    "conviene que": ("Conviene que revises los errores antes de escribir la versión final.", "你最好在写最终版本前检查错误。"),
    "resulta imprescindible que": ("Resulta imprescindible que el estudiante entienda cuándo usar el subjuntivo.", "学生必须理解什么时候使用虚拟式。"),
    "no cabe duda de que": ("No cabe duda de que la práctica diaria mejora la expresión oral.", "毫无疑问，每天练习会提升口语表达。"),
    "a menos que": ("No podremos avanzar a B2 a menos que consolidemos primero la base de B1.", "除非先巩固 B1 基础，否则我们无法推进到 B2。"),
    "siempre que": ("Puedes usar esta estructura siempre que quieras expresar una condición.", "只要你想表达条件，就可以使用这个结构。"),
    "para que": ("Te doy ejemplos traducidos para que puedas comparar las dos lenguas.", "我给你带翻译的例句，以便你能比较两种语言。"),
    "es posible que": ("Es posible que necesites varios ejemplos antes de usar bien la estructura.", "你可能需要几个例子之后，才能很好地使用这个结构。"),
    "es necesario que": ("Es necesario que practiques primero con frases cortas.", "有必要先用短句练习。"),
    "no parece que": ("No parece que esta regla sea imposible si la estudias paso a paso.", "如果你一步一步学，这条规则看起来并不是不可能掌握。"),
    "ojalá": ("Ojalá puedas usar esta estructura con más seguridad en el examen.", "希望你能在考试中更有把握地使用这个结构。"),
    "temo que": ("Temo que el ejercicio sea confuso si no vemos ejemplos traducidos.", "我担心如果不看带翻译的例子，这个练习会让人困惑。"),
    "antes de que": ("Conviene revisar la frase antes de que escribas la versión final.", "你最好在写最终版本之前检查句子。"),
    "no obstante": ("El ejercicio parece fácil; no obstante, exige atención al modo verbal.", "这个练习看起来容易，不过它要求注意动词式。"),
    "en definitiva": ("En definitiva, aprender poco a poco es más útil que escribir demasiado desde el primer día.", "总之，循序渐进学习比第一天就写太多更有用。"),
}

DEFAULT_PATTERNS = [
    ("Aunque ..., conviene reconocer que ...", "先让步，再提出自己的核心观点", "议论文、口语讨论", "Aunque el tema parece sencillo, conviene reconocer que tiene varios matices.", "虽然这个话题看起来简单，但应该承认它有多个细微层面。", "写作和口语都适合"),
    ("No se trata solo de ..., sino también de ...", "不是只涉及 A，也涉及 B", "扩展论点，避免观点单薄", "No se trata solo de memorizar palabras, sino también de usarlas en contexto.", "这不仅是背单词，也是在语境中使用它们。", "写作更适合"),
    ("Desde mi punto de vista, lo más relevante es que ...", "清楚表达个人立场", "口语开头或作文观点句", "Desde mi punto de vista, lo más relevante es que el aprendizaje sea constante.", "在我看来，最重要的是学习要持续。", "口语更自然"),
    ("Dicho de otro modo, ...", "换句话说，重新解释前一句", "解释抽象观点", "Dicho de otro modo, una respuesta B2 necesita ejemplos y no solo opiniones.", "换句话说，B2 回答需要例子，而不只是观点。", "写作和口语都适合"),
    ("Esto permite que + subjuntivo", "说明某事带来的效果", "解释方法、建议、措施", "Esto permite que el estudiante avance sin sentirse perdido.", "这能让学生在不迷失的情况下进步。", "写作更适合"),
]

PATTERN_LIBRARY = {
    "Subjuntivo para valoración y duda": [
        ("Es + adjetivo + que + subjuntivo", "用评价引出虚拟式", "表达必要性、重要性、好坏评价", "Es necesario que practiques con frases completas.", "有必要用完整句来练习。", "写作和口语都适合"),
        ("No creo / Dudo que + subjuntivo", "否定看法或怀疑后常用虚拟式", "表达不确定或不同意", "No creo que sea suficiente leer la regla una sola vez.", "我认为只读一遍规则是不够的。", "口语更常用，写作也可用"),
        ("Me parece + adjetivo + que + subjuntivo", "表达个人评价", "评论学习方法、社会现象、建议", "Me parece positivo que el curso combine lectura y práctica.", "我觉得课程把阅读和练习结合起来是积极的。", "写作更适合"),
        ("Para que + subjuntivo", "表示目的", "说明某个行动的目的", "Repito el ejemplo para que lo recuerdes mejor.", "我重复这个例子是为了让你记得更牢。", "写作和口语都适合"),
        ("A menos que + subjuntivo", "表示排除条件", "提出限制或例外", "No mejorarás la precisión a menos que corrijas tus errores frecuentes.", "除非你改正常见错误，否则准确性不会提高。", "写作更适合"),
    ],
    "Escribir correos formales": [
        ("Me dirijo a usted para + infinitivo", "正式邮件开头，说明目的", "投诉、申请、询问信息", "Me dirijo a usted para solicitar más información sobre el curso.", "我写信给您，是为了询问更多课程信息。", "写作更适合"),
        ("Le agradecería que + subjuntivo", "礼貌提出请求", "正式请求对方做某事", "Le agradecería que me enviara la información actualizada.", "如您能把最新信息发给我，我将非常感谢。", "写作更适合"),
        ("Quedo a la espera de + sustantivo", "正式结尾，等待回复", "邮件结尾", "Quedo a la espera de su respuesta.", "期待您的回复。", "写作更适合"),
        ("Con respecto a ..., quisiera aclarar que ...", "引出具体事项并澄清", "解释背景或补充信息", "Con respecto a la inscripción, quisiera aclarar que ya he enviado el formulario.", "关于报名，我想说明我已经提交了表格。", "写作更适合"),
    ],
}

GRAMMAR_LIBRARY = {
    "subjuntivo": [
        {
            "title": "评价、建议、必要性 + que + subjuntivo",
            "rule": "当主句表达评价、建议、必要性或情绪时，从句常用虚拟式。中文里没有这种动词式，所以不要按中文“事实陈述”的习惯直接用陈述式。",
            "examples": [
                ("Es importante que revises los conectores antes de escribir.", "重要的是你写作前复习连接词。"),
                ("Me alegra que entiendas mejor la diferencia.", "我很高兴你更理解这个区别了。"),
                ("Conviene que practiques con frases cortas primero.", "你最好先用短句练习。"),
            ],
            "mistake": "中国学生常把 Es importante que 后面写成 indicativo，例如 *Es importante que revisas*。这里应写 revises。",
        },
        {
            "title": "怀疑、否定看法 + que + subjuntivo",
            "rule": "dudo que, no creo que, no parece que 后面通常用虚拟式，因为说话人没有把后面的内容当作确定事实来呈现。",
            "examples": [
                ("Dudo que esta explicación sea demasiado difícil.", "我不认为这个解释会太难。"),
                ("No creo que memorizar listas sea suficiente.", "我认为只背清单是不够的。"),
                ("No parece que el ejercicio tenga una única respuesta.", "这个练习看起来不像只有一个答案。"),
            ],
            "mistake": "注意 no creo que + subjuntivo；但 creo que + indicativo，例如 Creo que es útil.",
        },
    ],
    "condicional": [
        {
            "title": "条件句：si + imperfecto de subjuntivo, condicional",
            "rule": "表达假设情况时，si 从句用过去未完成虚拟式，主句用条件式。这个结构适合 B2 口语和写作中提出假设、建议。",
            "examples": [
                ("Si tuviera más tiempo, revisaría los errores con calma.", "如果我有更多时间，我会慢慢检查错误。"),
                ("Si fuera posible, estudiaría un poco cada mañana.", "如果可能的话，我会每天早上学一点。"),
                ("Si el curso fuera más práctico, resultaría más útil.", "如果课程更实用，它会更有用。"),
            ],
            "mistake": "不要写 *Si tendría tiempo*。si 从句里要用 tuviera，不用 tendría。",
        }
    ],
    "narración": [
        {
            "title": "pretérito indefinido 与 imperfecto 的基本分工",
            "rule": "讲过去经历时，indefinido 用来讲完成的事件，imperfecto 用来描述背景、习惯和当时状态。B2 叙述要能在二者之间切换。",
            "examples": [
                ("Cuando era estudiante, solía leer textos cortos cada día.", "我还是学生时，过去常常每天读短文。"),
                ("Ayer terminé el ejercicio y corregí los errores.", "昨天我完成了练习并改了错误。"),
                ("Mientras preparaba el examen, descubrí una forma más eficaz de estudiar.", "备考时，我发现了一种更有效的学习方式。"),
            ],
            "mistake": "不要所有过去都用一个时态。背景用 imperfecto，动作推进用 indefinido。",
        }
    ],
    "conectores": [
        {
            "title": "连接词不只是“连接”，还要显示逻辑关系",
            "rule": "B2 写作和口语需要用连接词展示让步、对比、原因、结果和总结。不要只反复使用 y, pero, porque。",
            "examples": [
                ("Aunque el tema parece sencillo, exige una explicación precisa.", "虽然这个话题看起来简单，但它需要准确解释。"),
                ("El texto ofrece ejemplos; por consiguiente, resulta más fácil de entender.", "文本提供了例子，因此更容易理解。"),
                ("En definitiva, la práctica guiada ayuda a ganar seguridad.", "总之，有引导的练习有助于建立信心。"),
            ],
            "mistake": "sin embargo 和 no obstante 后面常接完整句；不要把它们当成 pero 随意插在两个词之间。",
        }
    ],
}

SPANISH_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
SPANISH_WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}")
SPANISH_ALLOWED = set("ÁÉÍÓÚÜÑáéíóúüñ¿¡")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def choose_lesson_day(progress_path: Path, today: date, day_override: int | None, cycle_length: int) -> tuple[int, dict[str, Any]]:
    progress = load_json(progress_path, {})
    if day_override:
        progress.setdefault("start_date", today.isoformat())
        progress["last_generated_date"] = today.isoformat()
        progress["last_day_number"] = day_override
        return day_override, progress

    if "start_date" not in progress:
        progress["start_date"] = today.isoformat()
    start = date.fromisoformat(progress["start_date"])
    absolute_day = (today - start).days + 1
    if absolute_day < 1:
        absolute_day = 1
    day_number = ((absolute_day - 1) % cycle_length) + 1
    progress["last_generated_date"] = today.isoformat()
    progress["last_day_number"] = day_number
    progress["absolute_day"] = absolute_day
    return day_number, progress


def readability_score(text: str) -> int:
    words = SPANISH_WORD_RE.findall(text)
    non_latin_noise = sum(1 for char in text if ord(char) > 255 and char not in SPANISH_ALLOWED)
    symbol_noise = sum(1 for char in text[:120] if not (char.isalnum() or char.isspace() or char in SPANISH_ALLOWED))
    return len(words) * 4 - non_latin_noise - symbol_noise


def select_chunks(knowledge: dict[str, Any], topic: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    by_id = {chunk["id"]: chunk for chunk in knowledge["chunks"]}
    chunks = [by_id[chunk_id] for chunk_id in topic.get("source_chunk_ids", []) if chunk_id in by_id]
    readable_chunks = [chunk for chunk in chunks if len(chunk.get("text", "")) > 120]
    return sorted(readable_chunks, key=lambda chunk: readability_score(chunk["text"]), reverse=True)[:limit]


def clean_excerpt(text: str, max_chars: int = 950) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = "".join(
        char if char.isascii() or char in SPANISH_ALLOWED else " "
        for char in text
    )
    text = re.sub(r"\s+", " ", text).strip()
    marker = text.find("Texto ")
    if 0 <= marker < 120:
        text = text[marker + len("Texto ") :].strip()
    text = re.sub(r"^[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ¿¡]+", "", text)
    if len(text) <= max_chars:
        return text
    sentences = SPANISH_SENTENCE_RE.split(text)
    result = ""
    for sentence in sentences:
        if len(result) + len(sentence) + 1 > max_chars:
            break
        result += sentence.strip() + " "
    return result.strip() or text[:max_chars].rstrip() + "..."


def infer_grammar_note(topic: dict[str, Any]) -> str:
    focus = str(topic.get("focus", "")).lower()
    if "subjuntivo" in focus:
        return GRAMMAR_PROMPTS["subjuntivo"]
    if "condicional" in focus or "hipótesis" in focus:
        return GRAMMAR_PROMPTS["condicional"]
    if "pretérito" in focus or "imperfecto" in focus:
        return GRAMMAR_PROMPTS["narración"]
    return GRAMMAR_PROMPTS["conectores"]


def grammar_key(topic: dict[str, Any]) -> str:
    focus = str(topic.get("focus", "")).lower()
    title = str(topic.get("title", "")).lower()
    if "subjuntivo" in focus or "subjuntivo" in title:
        return "subjuntivo"
    if "condicional" in focus or "hipótesis" in focus or "condiciones" in title:
        return "condicional"
    if "pretérito" in focus or "imperfecto" in focus or "narrar" in title:
        return "narración"
    return "conectores"


def vocab_example(term: str, topic: dict[str, Any]) -> tuple[str, str]:
    if term in EXAMPLE_OVERRIDES:
        return EXAMPLE_OVERRIDES[term]
    topic_title = topic["title"].lower()
    if "que" in term and not term.startswith("no cabe duda"):
        return (
            f"{term.capitalize()} el estudiante practique con frases breves y claras.",
            f"{VOCAB_MEANINGS.get(term, '这个表达')}：学生要用简短清楚的句子练习。",
        )
    return (
        f"En una respuesta sobre {topic_title}, podemos usar '{term}' para expresarnos con más precisión.",
        f"在关于“{topic['title']}”的回答中，我们可以使用“{term}”来表达得更准确。",
    )


def build_vocab_entries(topic: dict[str, Any], source_terms: list[str]) -> list[dict[str, str]]:
    topic_terms = B2_VOCAB_BANK.get(topic["title"], [])
    clean_source_terms = [
        term for term in source_terms
        if term in VOCAB_MEANINGS and term not in topic_terms
    ]
    selected = list(dict.fromkeys(topic_terms + clean_source_terms))[:15]
    entries = []
    for term in selected:
        example, translation = vocab_example(term, topic)
        entries.append(
            {
                "term": term,
                "meaning": VOCAB_MEANINGS.get(term, "与今日主题相关的常用表达"),
                "usage": f"DELE B2 中常用于围绕“{topic['title']}”表达观点、条件、原因或补充说明。",
                "example": example,
                "translation": translation,
                "related": RELATED_EXPRESSIONS.get(term, "可结合今日句型替换使用"),
            }
        )
    return entries


def build_sentence_patterns(topic: dict[str, Any]) -> list[dict[str, str]]:
    rows = PATTERN_LIBRARY.get(topic["title"], DEFAULT_PATTERNS)[:5]
    return [
        {
            "structure": row[0],
            "explanation": row[1],
            "scene": row[2],
            "example": row[3],
            "translation": row[4],
            "mode": row[5],
        }
        for row in rows
    ]


def build_grammar_points(topic: dict[str, Any]) -> list[dict[str, Any]]:
    return GRAMMAR_LIBRARY[grammar_key(topic)][:2]


def build_reading(topic: dict[str, Any], source_pages: str) -> dict[str, Any]:
    title = topic["title"]
    if "Subjuntivo" in title:
        spanish = (
            "Para avanzar de B1 a B2, no basta con conocer una regla de memoria. "
            "Es necesario que el estudiante observe cómo se usa la estructura en contextos reales y que practique poco a poco. "
            "Por ejemplo, cuando expresamos duda, valoración o recomendación, el subjuntivo ayuda a mostrar que no presentamos la idea como un hecho seguro. "
            "Aunque al principio parezca complicado, conviene que cada frase tenga una intención clara."
        )
        chinese = (
            "从 B1 过渡到 B2，光背一条规则是不够的。学生需要观察这个结构在真实语境中如何使用，并一点一点练习。"
            "例如，当我们表达怀疑、评价或建议时，虚拟式能帮助我们显示：后面的内容并不是被当作确定事实来陈述。"
            "虽然一开始看起来复杂，但最好让每个句子都有清楚的表达意图。"
        )
        expressions = ["no basta con + infinitivo", "Es necesario que + subjuntivo", "aunque + subjuntivo/indicativo", "conviene que + subjuntivo"]
        b2_reason = "这段把规则、语境和学习方法连接起来，句子不长，但已经包含 B2 常见的评价、目的和让步表达。"
    else:
        spanish = (
            f"En el tema de {title.lower()}, una respuesta de nivel B2 debe ir más allá de una opinión rápida. "
            "Primero conviene presentar la idea principal con claridad; después, añadir un ejemplo concreto y un matiz. "
            "De esta manera, el discurso resulta más organizado y el lector entiende no solo qué pensamos, sino también por qué lo pensamos. "
            "A grandes rasgos, la clave está en combinar vocabulario preciso, conectores y frases manejables."
        )
        chinese = (
            f"在“{title}”这个主题中，B2 水平的回答不能只是快速说一个观点。"
            "首先最好清楚提出主旨；然后补充一个具体例子和一个细微限制。"
            "这样一来，表达会更有条理，读者不仅能明白我们想什么，也能明白为什么这样想。"
            "大体上，关键在于结合准确词汇、连接词和可掌控的句子。"
        )
        expressions = ["ir más allá de", "conviene + infinitivo", "de esta manera", "no solo ..., sino también ...", "a grandes rasgos"]
        b2_reason = "这段适合 B1 到 B2 过渡：词汇不偏难，但要求你组织观点、补充例子并使用连接结构。"
    return {
        "source": f"参考材料页：{source_pages or '知识库综合主题'}；为适合 DELE B2 目标做了改写。",
        "spanish": spanish,
        "chinese": chinese,
        "expressions": expressions,
        "b2_reason": b2_reason,
    }


def format_vocab(entries: list[dict[str, str]]) -> str:
    lines = []
    for index, entry in enumerate(entries, start=1):
        lines.extend(
            [
                f"{index}. **{entry['term']}**",
                f"- 中文意思：{entry['meaning']}",
                f"- DELE B2 常见用法：{entry['usage']}",
                f"- 西语例句：{entry['example']}",
                f"- 中文翻译：{entry['translation']}",
                f"- 同义替换或相关表达：{entry['related']}",
            ]
        )
    return "\n".join(lines)


def format_patterns(patterns: list[dict[str, str]]) -> str:
    lines = []
    for index, pattern in enumerate(patterns, start=1):
        lines.extend(
            [
                f"{index}. **{pattern['structure']}**",
                f"- 中文解释：{pattern['explanation']}",
                f"- 使用场景：{pattern['scene']}",
                f"- 西语例句：{pattern['example']}",
                f"- 中文翻译：{pattern['translation']}",
                f"- 更适合：{pattern['mode']}",
            ]
        )
    return "\n".join(lines)


def format_grammar(points: list[dict[str, Any]]) -> str:
    lines = []
    for index, point in enumerate(points, start=1):
        lines.extend([f"{index}. **{point['title']}**", f"- 规则讲解：{point['rule']}"])
        for example, translation in point["examples"]:
            lines.append(f"- 例句：{example}")
            lines.append(f"- 翻译：{translation}")
        lines.append(f"- 中国学生常错点：{point['mistake']}")
    return "\n".join(lines)


def format_reading(reading: dict[str, Any]) -> str:
    expressions = "\n".join(f"- {item}" for item in reading["expressions"])
    return f"""来源说明：{reading['source']}

西语原文：
> {reading['spanish']}

中文翻译：
{reading['chinese']}

重点表达：
{expressions}

为什么适合 B2 学习：
{reading['b2_reason']}"""


def build_controlled_practice(vocab_entries: list[dict[str, str]], patterns: list[dict[str, str]]) -> str:
    terms = [entry["term"] for entry in vocab_entries]
    return f"""**填空题（3 题）**
1. Es importante que el estudiante ______ los errores antes de entregar el texto. (revisar)
2. No creo que memorizar listas ______ suficiente para hablar mejor. (ser)
3. ______ el estudiante entienda la idea principal con este ejemplo.（填入今天的一个概率表达）

**句型替换（2 题）**
1. 把 “Es bueno practicar cada día.” 改成 “Es + adjetivo + que + subjuntivo” 结构。
2. 用 “{patterns[0]['structure']}” 改写：El tema es difícil, pero se puede explicar con ejemplos.

**中译西（2 题）**
1. 我怀疑只读规则是否足够。
2. 最好先用短句练习，然后再写长段落。

**改错题（1-2 题）**
1. Es importante que revisas los conectores.
2. No creo que es una buena idea escribir demasiado el primer día."""


def build_half_open_output(vocab_entries: list[dict[str, str]], patterns: list[dict[str, str]]) -> str:
    chosen_terms = "、".join(entry["term"] for entry in vocab_entries[:3])
    chosen_patterns = "；".join(pattern["structure"] for pattern in patterns[:2])
    return f"""1. 用今天的 3 个词组造句：{chosen_terms}。
提示：每句 12-18 个词即可，不需要写成长段。

2. 用今天的 2 个句型仿写句子：{chosen_patterns}。
提示：先照着例句换主题，再逐步换动词。

3. 根据精读段落回答 2 个简单问题：
- ¿Por qué no basta con memorizar una regla?
- ¿Qué ayuda a que una respuesta sea más clara y organizada?"""


def build_dele_output(topic: dict[str, Any], patterns: list[dict[str, str]]) -> str:
    return f"""**写作任务（80-120 词）**
题目：围绕“{topic['title']}”，写一小段观点。要求只完成一个清楚段落：1 句引入 + 2 个理由或例子 + 1 句总结。请至少使用 2 个今日词组和 1 个今日句型。

**口语任务（1 分钟）**
表达框架：
- Para empezar, creo que ...
- Un ejemplo claro es que ...
- Aunque ..., conviene reconocer que ...
- En definitiva, ...

你可以先按框架说，不追求复杂。今天的目标是“说得清楚”，不是“说得很长”。"""


def build_quiz(vocab_entries: list[dict[str, str]], patterns: list[dict[str, str]]) -> str:
    first = vocab_entries[0]["term"]
    second = vocab_entries[1]["term"]
    first_meaning = vocab_entries[0]["meaning"]
    return f"""1. 词汇选择：No creo que esta explicación sea ______. A. suficiente B. suficientes C. suficiencia
2. 词汇选择：{first} 的中文意思最接近：A. {first_meaning} B. 完全否定 C. 过去常常
3. 语法填空：Es necesario que tú ______ con ejemplos. (practicar)
4. 语法填空：Dudo que esta respuesta ______ demasiado larga. (ser)
5. 句型转换：把 “Practicar es importante.” 改成 “Es importante que ...”
6. 翻译：我担心这个练习太难。
7. 翻译：为了让回答更清楚，我们需要例子。
8. 阅读理解：精读段落认为，从 B1 到 B2 过渡时，为什么不能只背规则？
9. 阅读理解：精读段落提到哪两种方式可以让表达更有条理？
10. 词汇应用：用 “{second}” 写一个短句。"""


def build_answers(vocab_entries: list[dict[str, str]]) -> str:
    first = vocab_entries[0]["term"]
    second = vocab_entries[1]["term"]
    if "que" in second:
        application = f"{second.capitalize()} esta estrategia funcione sin práctica diaria."
    else:
        application = f"Este ejemplo permite usar '{second}' en un contexto claro."
    return f"""**控制型练习参考答案**
1. revise。Es importante que 后面用 subjuntivo，所以 revisar -> revise。
2. sea。No creo que 表达否定看法，后面用 subjuntivo。
3. 可写：{first.capitalize()} el estudiante entienda la idea principal con este ejemplo. 这里重点是把概率表达放进完整句；如果表达后面接 que，要注意后面的动词形式。
4. Es bueno que practiques cada día. 注意 practiques 是 subjuntivo。
5. Aunque el tema sea difícil, conviene reconocer que se puede explicar con ejemplos. 如果强调事实，也可用 es；如果强调让步假设，用 sea。
6. Dudo que leer solo las reglas sea suficiente.
7. Conviene que practiques primero con frases cortas y luego escribas párrafos más largos.
8. 错句 *revisas* 应改为 revises，因为 Es importante que 后面用 subjuntivo。
9. 错句 *es* 应改为 sea，因为 No creo que 后面用 subjuntivo。

**今日小测试参考答案与解析**
1. A. suficiente。这里修饰 explicación，阴性单数时 suficiente 形式不变。
2. A。{first} 的中文意思要按今天词汇表记忆，不要只凭单词外形猜。
3. practiques。Es necesario que + subjuntivo。
4. sea。Dudo que + subjuntivo。
5. Es importante que practiques. 中文同样是“练习很重要”，但西语结构变了。
6. Temo que este ejercicio sea demasiado difícil. Temo que 后面用 subjuntivo。
7. Para que la respuesta sea más clara, necesitamos ejemplos. Para que 后面用 subjuntivo。
8. 因为 B2 不只考规则记忆，还要求在真实语境中表达怀疑、评价、建议和目的。
9. 可以通过具体例子和连接表达来让表达更有条理。
10. 示例：{application} 你的答案只要语法正确、意思清楚即可。"""


def build_spaced_review(cards: list[dict[str, Any]], today: date) -> str:
    sections = []
    for label, days in (("昨天内容", 1), ("3 天前内容", 3), ("7 天前内容", 7)):
        target = (today - timedelta(days=days)).isoformat()
        items = [card for card in cards if card.get("created_at") == target][:4]
        if items:
            input_items = "\n".join(f"- {card['front']}" for card in items[:3])
            output_items = "\n".join(
                f"{index}. 用 “{card['front']}” 写一个 10-15 个词的句子。"
                for index, card in enumerate(items[:3], start=1)
            )
        else:
            input_items = "- 暂无对应日期的复习卡。系统会从今天开始继续积累。"
            output_items = "1. 复述今天最重要的 1 个词组。\n2. 复述今天最重要的 1 个句型。\n3. 用今天的语法点写一个短句。"
        sections.append(f"""**{label}**
输入：快速回顾词组和句型
{input_items}

输出：3-5 道小题
{output_items}""")
    return "\n\n".join(sections)


def due_review_cards(cards_path: Path, today: date, limit: int = 8) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cards = load_json(cards_path, [])
    due: list[dict[str, Any]] = []
    for card in cards:
        if card.get("last_reviewed") == today.isoformat():
            continue
        if date.fromisoformat(card["due_date"]) <= today:
            due.append(card)
    due = due[:limit]

    for card in due:
        card["last_reviewed"] = today.isoformat()
        card["review_count"] = int(card.get("review_count", 0)) + 1
        next_interval = [1, 3, 7, 14, 30][min(card["review_count"], 4)]
        card["due_date"] = (today + timedelta(days=next_interval)).isoformat()
    return due, cards


def add_new_review_cards(cards: list[dict[str, Any]], today: date, topic: dict[str, Any], vocab: list[dict[str, str]], grammar_note: str) -> list[dict[str, Any]]:
    existing = {card["id"] for card in cards}
    new_items = [entry["term"] for entry in vocab[:5]] + [grammar_note]
    for index, item in enumerate(new_items, start=1):
        card_id = f"{today.isoformat()}-{topic['day_in_cycle']}-{index}"
        if card_id in existing:
            continue
        cards.append(
            {
                "id": card_id,
                "front": item,
                "back": f"用这个表达围绕“{topic['title']}”造一句 DELE B2 风格的句子。",
                "created_at": today.isoformat(),
                "due_date": (today + timedelta(days=1)).isoformat(),
                "review_count": 0,
                "last_reviewed": None,
            }
        )
    return cards


def build_lesson(knowledge: dict[str, Any], day_number: int, today: date, cards_path: Path) -> dict[str, str]:
    plan = knowledge["course_plan"]
    topic = plan[day_number - 1]
    chunks = select_chunks(knowledge, topic)
    source_terms = []
    for chunk in chunks:
        source_terms.extend(extract_terms(chunk["text"], limit=6))
    vocab_entries = build_vocab_entries(topic, source_terms)
    sentence_patterns = build_sentence_patterns(topic)
    grammar_points = build_grammar_points(topic)
    grammar_note = grammar_points[0]["title"]
    reviews, cards = due_review_cards(cards_path, today)
    cards = add_new_review_cards(cards, today, topic, vocab_entries, grammar_note)
    write_json(cards_path, cards)

    source_pages = ", ".join(
        f"p.{chunk['page_start']}" if chunk["page_start"] == chunk["page_end"] else f"p.{chunk['page_start']}-{chunk['page_end']}"
        for chunk in chunks
    )
    reading = build_reading(topic, source_pages)
    review_block = build_spaced_review(cards, today)
    due_note = "\n".join(f"- {card['front']}：{card['back']}" for card in reviews[:3]) or "- 今天没有额外到期卡片；按下方 1/3/7 天复习即可。"

    markdown = f"""# DELE B2 每日学习 - Día {day_number} - {today.isoformat()}

## 一、输入部分（约 50%）

## 1. 今日学习目标
今天主题：{topic['title']}

今天的目标不是“大量输出”，而是具体掌握一个小能力：围绕“{topic['title']}”说清楚一个观点，并能用 12-15 个核心表达、4-5 个高频句型和 1-2 个语法点，把 B1 的简单句升级成更稳定的 B2 表达。

B2 目标：{topic['b2_goal']}

材料来源：{source_pages or '知识库综合复习'}

额外到期复习卡：
{due_note}

## 2. 核心词汇与词组（12-15 个）
{format_vocab(vocab_entries)}

## 3. 高频句型（4-5 个）
{format_patterns(sentence_patterns)}

## 4. 语法重点（1-2 个）
{format_grammar(grammar_points)}

## 5. 精读段落（1 段）
{format_reading(reading)}

## 二、输出部分（约 50%）

## 6. 控制型练习
{build_controlled_practice(vocab_entries, sentence_patterns)}

## 7. 半开放输出
{build_half_open_output(vocab_entries, sentence_patterns)}

## 8. DELE B2 输出训练
{build_dele_output(topic, sentence_patterns)}

## 9. 今日小测试
{build_quiz(vocab_entries, sentence_patterns)}

## 10. 答案与解析
{build_answers(vocab_entries)}

## 11. 间隔复习
{review_block}
"""

    html_body = markdown_to_html(markdown)
    return {"markdown": markdown, "html": html_body, "subject": f"DELE B2 每日学习 Día {day_number} - {topic['title']}"}


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    html_lines = ["<html><body style='font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;line-height:1.55;color:#222;'>"]
    in_ul = False
    for line in lines:
        if line.startswith("# "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            if not in_ul:
                html_lines.append("<ul>")
                in_ul = True
            html_lines.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.startswith("> "):
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<blockquote style='border-left:4px solid #ddd;padding-left:12px;color:#444;'>{html.escape(line[2:])}</blockquote>")
        elif line.strip():
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append(f"<p>{html.escape(line)}</p>")
    if in_ul:
        html_lines.append("</ul>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate today's DELE B2 lesson.")
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE_BASE)
    parser.add_argument("--output-dir", type=Path, default=DAILY_OUTPUT_DIR)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--review-cards", type=Path, default=DEFAULT_REVIEW_CARDS)
    parser.add_argument("--date", dest="lesson_date", default=None, help="YYYY-MM-DD，默认今天")
    parser.add_argument("--day", type=int, default=None, help="手动指定循环中的第几天")
    args = parser.parse_args()

    ensure_project_dirs()
    if not args.knowledge.exists():
        raise SystemExit(f"缺少知识库：{display_path(args.knowledge)}。请先运行 split_knowledge.py。")

    today = date.fromisoformat(args.lesson_date) if args.lesson_date else date.today()
    knowledge = json.loads(args.knowledge.read_text(encoding="utf-8"))
    day_number, progress = choose_lesson_day(args.progress, today, args.day, len(knowledge["course_plan"]))
    lesson = build_lesson(knowledge, day_number, today, args.review_cards)
    write_json(args.progress, progress)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{today.isoformat()}_day_{day_number:02d}"
    md_path = args.output_dir / f"{stem}.md"
    html_path = args.output_dir / f"{stem}.html"
    subject_path = args.output_dir / "latest_subject.txt"
    md_path.write_text(lesson["markdown"], encoding="utf-8")
    html_path.write_text(lesson["html"], encoding="utf-8")
    subject_path.write_text(lesson["subject"], encoding="utf-8")
    shutil.copyfile(md_path, args.output_dir / "latest_lesson.md")
    shutil.copyfile(html_path, args.output_dir / "latest_lesson.html")
    print(display_path(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
