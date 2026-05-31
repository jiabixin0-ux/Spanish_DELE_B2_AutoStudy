from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .config import (
    DEFAULT_COURSE_START_DATE,
    DAILY_OUTPUT_DIR,
    DEFAULT_KNOWLEDGE_BASE,
    DEFAULT_PROGRESS,
    DEFAULT_REVIEW_CARDS,
    DEFAULT_TIMEZONE,
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

B1_PHRASE_BANK = {
    "Opinar y matizar en temas cotidianos": [
        "estar de acuerdo", "no estar de acuerdo", "en mi opinión", "creo que",
        "me parece que", "tener razón", "decir la verdad", "exagerar un poco",
        "la calidad de", "me importa", "a veces", "por ejemplo",
    ],
    "Subjuntivo para valoración y duda": [
        "es necesario que", "es importante que", "puede que", "dudo que",
        "no creo que", "me parece normal que", "te importa que", "esperar un poco",
        "es mejor que", "es bueno que", "es posible que", "tener que",
    ],
    "Narrar experiencias y cambios": [
        "durante ese período", "empezar a", "volver a", "acabar de",
        "dar conferencias", "asistir a", "publicar un libro", "terminar una obra",
        "antes de", "después de", "por primera vez", "conocer a",
    ],
    "Contrastar ventajas e inconvenientes": [
        "por un lado", "por otro lado", "en cambio", "aunque",
        "tener la ventaja de", "tener el inconveniente de", "merecer la pena",
        "depender de", "ser más barato", "ser más cómodo", "a pesar de", "comparar con",
    ],
    "Expresar hipótesis y condiciones": [
        "si tengo tiempo", "si es posible", "en caso de", "a menos que",
        "por si acaso", "tal vez", "quizá", "depende de",
        "sería mejor", "me gustaría", "tener que", "para poder",
    ],
    "Escribir correos formales": [
        "me dirijo a usted", "quisiera solicitar", "le escribo para", "con respecto a",
        "muchas gracias por", "quedo a la espera", "un saludo cordial",
        "a la mayor brevedad posible", "solicitar información", "ponerse en contacto",
        "adjuntar un documento", "recibir una respuesta",
    ],
    "Conectores para organizar argumentos": [
        "en primer lugar", "además", "también", "por eso",
        "sin embargo", "por ejemplo", "en resumen", "por último",
        "es decir", "de esta manera", "por una parte", "por otra parte",
    ],
    "Describir datos, tendencias y cambios sociales": [
        "la mayoría de", "una minoría", "aumentar poco a poco", "disminuir mucho",
        "mantenerse estable", "según los datos", "en comparación con", "a lo largo de",
        "el porcentaje de", "un cambio importante", "cada vez más", "cada vez menos",
    ],
    "Reformular y evitar repeticiones": [
        "es decir", "dicho de otro modo", "en otras palabras", "hacer referencia a",
        "este tema", "esta situación", "por ejemplo", "en este sentido",
        "para explicar mejor", "volver a decir", "ser parecido a", "no solo",
    ],
    "Debatir soluciones y propuestas": [
        "proponer una solución", "tomar medidas", "hacer frente a", "mejorar la situación",
        "buscar una alternativa", "llegar a un acuerdo", "poner en marcha", "llevar a cabo",
        "sería recomendable", "sería útil", "trabajar juntos", "resolver el problema",
    ],
}

COMMON_B1_VOCAB = [
    "acuerdo", "anuncio", "calidad", "producto", "verdad", "marca", "dinero",
    "gente", "opinión", "ejemplo", "tema", "problema", "solución", "ciudad",
    "trabajo", "estudio", "tiempo", "familia", "viaje", "cambio", "persona",
    "lugar", "forma", "actividad", "experiencia", "resultado", "pregunta",
    "respuesta", "razón", "necesario", "importante", "posible", "mejor",
    "difícil", "fácil", "normal", "frecuente", "útil", "claro", "nuevo",
    "primero", "después", "antes", "durante", "siempre", "nunca", "también",
    "aunque", "porque", "cuando", "donde", "comprar", "estudiar", "leer",
    "escribir", "escuchar", "hablar", "pensar", "creer", "decir", "necesitar",
    "querer", "poder", "hacer", "tener", "estar", "ser", "ir", "volver",
]

B1_MEANINGS = {
    "acuerdo": "同意、一致", "anuncio": "广告", "calidad": "质量", "producto": "产品",
    "verdad": "事实、真相", "marca": "品牌", "dinero": "钱", "gente": "人们",
    "personas": "人们", "pisos": "公寓、住房", "ciudades": "城市", "hijos": "子女",
    "revista": "杂志", "poemas": "诗歌", "poeta": "诗人", "grandes": "大的、重要的",
    "vivienda": "住房", "soledad": "孤独",
    "precio": "价格", "mayores": "老年人", "saludos": "问候", "teléfono": "电话",
    "cuanto": "至于、就……而言",
    "opinión": "观点", "ejemplo": "例子", "tema": "主题", "problema": "问题",
    "solución": "解决办法", "ciudad": "城市", "trabajo": "工作", "estudio": "学习、研究",
    "tiempo": "时间、天气", "familia": "家庭", "viaje": "旅行", "cambio": "变化",
    "persona": "人", "lugar": "地方", "forma": "方式", "actividad": "活动",
    "experiencia": "经历", "resultado": "结果", "pregunta": "问题", "respuesta": "回答",
    "razón": "理由、道理", "necesario": "必要的", "importante": "重要的",
    "posible": "可能的", "mejor": "更好的", "difícil": "困难的", "fácil": "容易的",
    "normal": "正常的", "frecuente": "常见的", "útil": "有用的", "claro": "清楚的",
    "nuevo": "新的", "primero": "首先、第一", "después": "之后", "antes": "之前",
    "durante": "在……期间", "siempre": "总是", "nunca": "从不", "también": "也",
    "aunque": "虽然、即使", "porque": "因为", "cuando": "当……时候", "donde": "在……的地方",
    "comprar": "购买", "estudiar": "学习", "leer": "阅读", "escribir": "写",
    "escuchar": "听", "hablar": "说话", "pensar": "思考、认为", "creer": "相信、认为",
    "decir": "说", "necesitar": "需要", "querer": "想要", "poder": "能够",
    "hacer": "做", "tener": "有", "estar": "处于、在", "ser": "是", "ir": "去",
    "volver": "回来、再次",
}

PHRASE_MEANINGS = {
    "estar de acuerdo": "同意", "no estar de acuerdo": "不同意",
    "en mi opinión": "在我看来", "creo que": "我认为", "me parece que": "我觉得",
    "tener razón": "有道理、是对的", "decir la verdad": "说实话", "exagerar un poco": "稍微夸大",
    "la calidad de": "……的质量", "me importa": "我在意、对我重要", "a veces": "有时",
    "es necesario que": "有必要……", "es importante que": "重要的是……",
    "puede que": "可能……", "me parece normal que": "我觉得……很正常",
    "te importa que": "你介意……吗", "esperar un poco": "稍等一会儿",
    "es mejor que": "最好……", "es bueno que": "……是好的",
    "durante ese período": "在那段时期", "empezar a": "开始做……", "volver a": "重新/再次做……",
    "acabar de": "刚刚做完……", "dar conferencias": "做讲座", "asistir a": "参加、出席",
    "publicar un libro": "出版一本书", "terminar una obra": "完成一部作品",
    "por primera vez": "第一次", "conocer a": "认识某人",
    "tener la ventaja de": "有……优点", "ser más barato": "更便宜", "ser más cómodo": "更方便",
    "comparar con": "与……比较", "si tengo tiempo": "如果我有时间", "si es posible": "如果可能",
    "en caso de": "如果、万一", "depende de": "取决于", "sería mejor": "最好是……",
    "me gustaría": "我想……", "tener que": "必须、不得不", "hay que": "应该、需要",
    "para poder": "为了能够……", "quizá": "也许、可能",
    "tal vez": "也许", "le escribo para": "我写信是为了……",
    "muchas gracias por": "非常感谢……", "un saludo cordial": "诚挚问候",
    "adjuntar un documento": "附上一份文件", "también": "也", "por eso": "因此、所以",
    "por último": "最后", "de esta manera": "这样一来", "aumentar poco a poco": "逐渐增加",
    "disminuir mucho": "大幅减少", "un cambio importante": "一个重要变化",
    "cada vez más": "越来越多/越来越……", "cada vez menos": "越来越少",
    "para explicar mejor": "为了解释得更清楚", "volver a decir": "再说一遍",
    "ser parecido a": "与……相似", "proponer una solución": "提出一个解决办法",
    "trabajar juntos": "一起合作",
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


def choose_lesson_day(
    progress_path: Path,
    today: date,
    day_override: int | None,
    cycle_length: int,
    default_start_date: str = DEFAULT_COURSE_START_DATE,
) -> tuple[int, dict[str, Any]]:
    progress = load_json(progress_path, {})
    if day_override:
        progress.setdefault("start_date", today.isoformat())
        progress["last_generated_date"] = today.isoformat()
        progress["last_day_number"] = day_override
        progress["cycle_day_number"] = ((day_override - 1) % cycle_length) + 1
        return day_override, progress

    if "start_date" not in progress:
        progress["start_date"] = default_start_date
    elif date.fromisoformat(progress["start_date"]) < date.fromisoformat(default_start_date):
        progress["start_date"] = default_start_date
    start = date.fromisoformat(progress["start_date"])
    absolute_day = (today - start).days + 1
    if absolute_day < 1:
        absolute_day = 1
    progress["last_generated_date"] = today.isoformat()
    progress["last_day_number"] = absolute_day
    progress["cycle_day_number"] = ((absolute_day - 1) % cycle_length) + 1
    progress["absolute_day"] = absolute_day
    return absolute_day, progress


def current_lesson_date() -> date:
    return datetime.now(ZoneInfo(DEFAULT_TIMEZONE)).date()


def readability_score(text: str) -> int:
    words = SPANISH_WORD_RE.findall(text)
    non_latin_noise = sum(1 for char in text if ord(char) > 255 and char not in SPANISH_ALLOWED)
    symbol_noise = sum(1 for char in text[:120] if not (char.isalnum() or char.isspace() or char in SPANISH_ALLOWED))
    return len(words) * 4 - non_latin_noise - symbol_noise


def select_chunks(knowledge: dict[str, Any], topic: dict[str, Any], limit: int = 3, variant: int = 0) -> list[dict[str, Any]]:
    by_id = {chunk["id"]: chunk for chunk in knowledge["chunks"]}
    chunks = [by_id[chunk_id] for chunk_id in topic.get("source_chunk_ids", []) if chunk_id in by_id]
    readable_chunks = [chunk for chunk in chunks if len(chunk.get("text", "")) > 120]
    ranked = sorted(readable_chunks, key=lambda chunk: readability_score(chunk["text"]), reverse=True)
    return rotate_items(ranked, variant)[:limit]


def rotate_items(items: list[Any], offset: int) -> list[Any]:
    if not items:
        return []
    offset = offset % len(items)
    return items[offset:] + items[:offset]


def topic_for_lesson(plan: list[dict[str, Any]], lesson_day: int) -> dict[str, Any]:
    return plan[(lesson_day - 1) % len(plan)]


def variant_for_lesson(lesson_day: int, plan_length: int) -> int:
    return (lesson_day - 1) // plan_length


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


def build_vocab_entries(topic: dict[str, Any], source_terms: list[str], variant: int = 0) -> list[dict[str, str]]:
    topic_terms = B2_VOCAB_BANK.get(topic["title"], [])
    clean_source_terms = [
        term for term in source_terms
        if term in VOCAB_MEANINGS and term not in topic_terms
    ]
    candidate_terms = list(dict.fromkeys(topic_terms + clean_source_terms))
    selected = rotate_items(candidate_terms, variant * 3)[:6]
    entries = []
    for term in selected:
        example, translation = vocab_example(term, topic)
        entries.append(
            {
                "term": term,
                "meaning": VOCAB_MEANINGS.get(term, "与今日主题相关的常用表达"),
                "usage": vocab_usage(term, topic),
                "example": example,
                "translation": translation,
                "related": RELATED_EXPRESSIONS.get(term, "可结合今日句型替换使用"),
                "note": vocab_note(term),
            }
        )
    return entries


def vocab_note(term: str) -> str:
    if "que" in term:
        return "注意 que 后面的动词形式；表达怀疑、建议、评价时常会触发虚拟式。"
    if "de" in term:
        return "注意固定介词不要省略，也不要按中文语序随意移动。"
    if term in {"no obstante", "sin embargo", "en cambio", "por consiguiente"}:
        return "连接词要放在真正有逻辑关系的句子之间，不要为了显得高级而堆砌。"
    return "先用短句掌握这个表达，再放进较长段落里。"


def vocab_usage(term: str, topic: dict[str, Any]) -> str:
    if term.startswith(("es ", "no ", "dudo", "temo", "conviene", "resulta", "me ")):
        return "用来表达评价、怀疑、建议或情绪；后面常接 que 从句，是 B1 到 B2 过渡的高频结构。"
    if term in {"aunque", "no obstante", "sin embargo", "a pesar de ello", "en cambio"}:
        return "用来承认另一面或转折观点，适合让回答不显得绝对。"
    if term in {"por consiguiente", "por lo tanto", "en definitiva", "en resumen"}:
        return "用来总结或推出结论，适合放在段落后半部分。"
    if term in {"matizar", "plantear", "sostener", "poner en duda"}:
        return "用来让观点更细致：提出、坚持、补充或质疑一个看法。"
    if term in {"a grandes rasgos", "desde mi punto de vista", "por una parte", "por otra parte"}:
        return "用来组织观点开头，让听者或读者先看到你的表达框架。"
    return f"适合围绕“{topic['title']}”补充观点、例子或限制条件。"


def build_sentence_patterns(topic: dict[str, Any], variant: int = 0) -> list[dict[str, str]]:
    rows = rotate_items(PATTERN_LIBRARY.get(topic["title"], DEFAULT_PATTERNS), variant)[:3]
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


def build_grammar_points(topic: dict[str, Any], variant: int = 0) -> list[dict[str, Any]]:
    return rotate_items(GRAMMAR_LIBRARY[grammar_key(topic)], variant)[:1]


def chunk_text(chunks: list[dict[str, Any]]) -> str:
    return " ".join(str(chunk.get("text", "")) for chunk in chunks)


def pdf_terms(chunks: list[dict[str, Any]], limit: int = 30) -> list[str]:
    terms: list[str] = []
    blocked = {"david", "josé", "jose", "marta", "mariana", "lorca", "garcía", "garcia"}
    for chunk in chunks:
        terms.extend(str(term).lower() for term in chunk.get("terms", []))
        terms.extend(extract_terms(str(chunk.get("text", "")), limit=12))
    cleaned = [
        term for term in terms
        if term not in blocked and (term in B1_MEANINGS or term in VOCAB_MEANINGS or len(term) >= 5)
    ]
    return list(dict.fromkeys(cleaned))[:limit]


def phrase_candidates(topic: dict[str, Any], chunks: list[dict[str, Any]], variant: int = 0) -> list[str]:
    text = chunk_text(chunks).lower()
    pdf_first = [
        phrase for phrase in B1_PHRASE_BANK.get(topic["title"], [])
        if phrase.lower() in text or any(part in text for part in phrase.lower().split() if len(part) > 4)
    ]
    candidates = list(dict.fromkeys(pdf_first + B1_PHRASE_BANK.get(topic["title"], []) + B2_VOCAB_BANK.get(topic["title"], [])))
    return rotate_items(candidates, variant * 4)


def term_meaning(term: str) -> str:
    return PHRASE_MEANINGS.get(term) or B1_MEANINGS.get(term) or VOCAB_MEANINGS.get(term) or "与今日 PDF 主题相关的常用词"


def natural_example(term: str, topic: dict[str, Any], index: int = 0) -> tuple[str, str]:
    if term in EXAMPLE_OVERRIDES:
        return EXAMPLE_OVERRIDES[term]
    examples = {
        "estar de acuerdo": ("Estoy de acuerdo con esta opinión porque el ejemplo es claro.", "我同意这个观点，因为例子很清楚。"),
        "no estar de acuerdo": ("No estoy de acuerdo con la idea principal del texto.", "我不同意文本中的主要观点。"),
        "en mi opinión": ("En mi opinión, estudiar un poco cada día es más útil.", "在我看来，每天学一点更有用。"),
        "creo que": ("Creo que este método ayuda a recordar las palabras nuevas.", "我认为这个方法有助于记住新词。"),
        "me parece que": ("Me parece que la explicación es sencilla y práctica.", "我觉得这个解释简单而实用。"),
        "tener razón": ("La autora tiene razón cuando dice que necesitamos ejemplos.", "作者说我们需要例子时是有道理的。"),
        "decir la verdad": ("Es importante decir la verdad en una conversación.", "在对话中说实话很重要。"),
        "exagerar un poco": ("El anuncio exagera un poco la calidad del producto.", "广告稍微夸大了产品质量。"),
        "la calidad de": ("La calidad de este producto no siempre depende del precio.", "这个产品的质量并不总是取决于价格。"),
        "durante ese período": ("Durante ese período, Lorca escribió sus primeras obras.", "在那段时期，洛尔卡写了他的早期作品。"),
        "empezar a": ("Empecé a leer textos cortos para mejorar mi español.", "我开始读短文来提高西语。"),
        "volver a": ("Mañana voy a volver a revisar estas palabras.", "明天我要再复习这些词。"),
        "acabar de": ("Acabo de terminar el ejercicio de lectura.", "我刚刚完成阅读练习。"),
        "dar conferencias": ("El escritor viajó a otra ciudad para dar conferencias.", "这位作家去另一个城市做讲座。"),
        "asistir a": ("Muchos estudiantes asistieron a la clase de gramática.", "很多学生参加了语法课。"),
        "tener que": ("Tengo que repasar las palabras antes de dormir.", "我睡前必须复习单词。"),
        "hay que": ("Hay que leer el ejemplo antes de hacer el ejercicio.", "做练习前应该先读例句。"),
        "para poder": ("Leo en voz alta para poder recordar mejor las frases.", "我大声朗读，以便更好地记住句子。"),
        "si tengo tiempo": ("Si tengo tiempo, repaso cinco palabras antes de dormir.", "如果我有时间，我睡前复习五个单词。"),
        "si es posible": ("Si es posible, prefiero estudiar con ejemplos del texto.", "如果可能，我更喜欢用课文里的例子学习。"),
        "en caso de": ("En caso de duda, vuelvo a leer la frase completa.", "如果有疑问，我会重新读完整句子。"),
        "quizá": ("Quizá el texto parece difícil al principio.", "也许这篇文本一开始看起来有点难。"),
        "tal vez": ("Tal vez necesito escuchar el audio otra vez.", "也许我需要再听一遍音频。"),
        "sería mejor": ("Sería mejor escribir frases cortas y claras.", "最好写简短清楚的句子。"),
        "depende de": ("La respuesta depende de la situación del texto.", "答案取决于文本中的情况。"),
        "gente": ("Hay mucha gente que vive lejos del centro.", "有很多人住得离市中心很远。"),
        "personas": ("Muchas personas necesitan más tiempo para descansar.", "很多人需要更多时间休息。"),
        "tiempo": ("No tengo mucho tiempo, pero puedo leer un párrafo.", "我时间不多，但可以读一段。"),
        "pisos": ("En las grandes ciudades hay pocos pisos baratos.", "在大城市，便宜的公寓很少。"),
        "aunque": ("Aunque el texto es largo, las ideas son claras.", "虽然文本很长，但思路很清楚。"),
        "problema": ("La soledad es un problema importante en algunas ciudades.", "孤独是一些城市里的重要问题。"),
        "ciudades": ("En las ciudades grandes, la vida puede ser más cara.", "在大城市，生活可能更贵。"),
        "trabajo": ("Por el trabajo, muchas personas tienen poco tiempo libre.", "由于工作，很多人空闲时间很少。"),
        "hijos": ("Sus hijos la llaman por teléfono los domingos.", "她的子女星期天给她打电话。"),
        "ciudad": ("Mi ciudad tiene muchos espacios para estudiar.", "我的城市有很多学习空间。"),
        "revista": ("Leí una entrevista interesante en una revista.", "我在一本杂志上读到一篇有趣的采访。"),
        "poemas": ("Los poemas de Lorca son conocidos en muchos países.", "洛尔卡的诗在很多国家都很有名。"),
        "poeta": ("El poeta escribió sobre la vida de su ciudad.", "这位诗人写了关于他城市生活的内容。"),
        "grandes": ("Las grandes ciudades tienen problemas diferentes.", "大城市有不同的问题。"),
        "vivienda": ("La vivienda es cara en muchas ciudades.", "很多城市住房很贵。"),
        "soledad": ("La soledad afecta a muchas personas mayores.", "孤独影响很多老年人。"),
        "precio": ("El precio de la vivienda ha subido mucho.", "住房价格上涨了很多。"),
    }
    if term in examples:
        return examples[term]
    topic_hint = topic["title"].lower()
    templates = [
        (f"Podemos usar {term} en una frase sencilla sobre {topic_hint}.", f"我们可以在关于“{topic['title']}”的简单句中使用 {term}。"),
        (f"Este texto ayuda a entender mejor {term} en contexto.", f"这段文本有助于在语境中更好地理解 {term}。"),
        (f"Hoy voy a practicar {term} con ejemplos cortos.", f"今天我要用短例句练习 {term}。"),
    ]
    return templates[index % len(templates)]


def collocation_for(term: str) -> str:
    collocations = {
        "estar de acuerdo": "estar de acuerdo con alguien / con una idea",
        "no estar de acuerdo": "no estar totalmente de acuerdo",
        "en mi opinión": "en mi opinión + frase completa",
        "creo que": "creo que + indicativo",
        "me parece que": "me parece que + indicativo",
        "es necesario que": "es necesario que + subjuntivo",
        "es importante que": "es importante que + subjuntivo",
        "tener que": "tener que + infinitivo",
        "empezar a": "empezar a + infinitivo",
        "volver a": "volver a + infinitivo",
        "acabar de": "acabar de + infinitivo",
        "asistir a": "asistir a una clase / una reunión",
        "depender de": "depender de la situación / del tiempo",
        "por ejemplo": "idea + por ejemplo + caso concreto",
    }
    if term in collocations:
        return collocations[term]
    if "que" in term:
        return f"{term} + frase con verbo conjugado"
    if re.search(r"\bde\b", term):
        return f"{term} + sustantivo / infinitivo"
    return f"{term} + ejemplo concreto"


def b1_note_for(term: str) -> str:
    if term in {"creo que", "me parece que", "pienso que"}:
        return "表达肯定观点时后面通常用陈述式，不要一看到 que 就自动用虚拟式。"
    if term in {"es necesario que", "es importante que", "dudo que", "no creo que"}:
        return "que 后面常用虚拟式；先记住固定结构，再慢慢练变位。"
    if term.endswith(" a") or term in {"asistir a", "empezar a", "volver a"}:
        return "注意固定介词 a 不要漏掉。"
    if re.search(r"\bde\b", term):
        return "注意固定介词 de，不要按中文习惯省略。"
    return "先会在短句里自然使用，再放进小段落。"


def build_required_phrases(topic: dict[str, Any], chunks: list[dict[str, Any]], variant: int = 0) -> list[dict[str, str]]:
    selected = phrase_candidates(topic, chunks, variant)[:8]
    entries = []
    for index, term in enumerate(selected, start=1):
        example, translation = natural_example(term, topic, index)
        entries.append(
            {
                "term": term,
                "meaning": term_meaning(term),
                "usage": vocab_usage(term, topic) if term in VOCAB_MEANINGS else f"适合在“{topic['title']}”相关的阅读、对话或短写作中表达基本意思。",
                "example": example,
                "translation": translation,
                "collocation": collocation_for(term),
                "note": b1_note_for(term),
            }
        )
    return entries


def build_extended_vocab(topic: dict[str, Any], chunks: list[dict[str, Any]], required: list[dict[str, str]], variant: int = 0) -> list[dict[str, str]]:
    used = {entry["term"] for entry in required}
    candidates = [term for term in pdf_terms(chunks, 40) + COMMON_B1_VOCAB if term not in used]
    selected = rotate_items(list(dict.fromkeys(candidates)), variant * 5)[:15]
    rows = []
    for index, term in enumerate(selected, start=1):
        example, translation = natural_example(term, topic, index)
        rows.append(
            {
                "term": term,
                "meaning": term_meaning(term),
                "example": example.replace(f"{term}", term, 1),
                "translation": translation,
            }
        )
    return rows


def format_required_phrases(entries: list[dict[str, str]]) -> str:
    lines = []
    for index, entry in enumerate(entries, start=1):
        lines.extend(
            [
                f"### 词组 {index}：{entry['term']}",
                f"【意思】{entry['meaning']}",
                f"【使用场景】{entry['usage']}",
                "【例句】",
                entry["example"],
                "【翻译】",
                entry["translation"],
                f"【常见搭配】{entry['collocation']}",
                f"【注意】{entry['note']}",
            ]
        )
    return "\n".join(lines)


def format_extended_vocab(rows: list[dict[str, str]]) -> str:
    lines = ["| 西语 | 中文 | 简短例句 | 例句翻译 |", "|---|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['term']} | {row['meaning']} | {row['example']} | {row['translation']} |")
    return "\n".join(lines)


def reading_excerpt(chunks: list[dict[str, Any]], topic: dict[str, Any]) -> str:
    text = clean_excerpt(chunk_text(chunks), max_chars=1300)
    sentences = [sentence.strip() for sentence in SPANISH_SENTENCE_RE.split(text) if len(SPANISH_WORD_RE.findall(sentence)) >= 4]
    selected: list[str] = []
    word_count = 0
    for sentence in sentences:
        words = SPANISH_WORD_RE.findall(sentence)
        if word_count + len(words) > 150 and word_count >= 80:
            break
        selected.append(sentence)
        word_count += len(words)
        if word_count >= 110:
            break
    if selected and word_count >= 45:
        return " ".join(selected)
    fallback = (
        f"El texto de hoy trata sobre {topic['title'].lower()}. Presenta varias ideas y ejemplos que sirven para ampliar "
        "el vocabulario y practicar frases sencillas. La idea principal no es escribir mucho, sino entender bien las palabras, "
        "observar cómo se combinan y usar algunas expresiones en oraciones cortas. Así podemos consolidar el nivel B1 y avanzar "
        "poco a poco hacia una expresión más clara."
    )
    return fallback


def reading_translation(topic: dict[str, Any], source_pages: str) -> str:
    return (
        f"这段来自 PDF 的 {source_pages or '相关页面'}，主题是“{topic['title']}”。"
        "它主要帮助你理解文本中的常用词、固定搭配和基础句型。学习时不需要追求写很难的句子，"
        "重点是先看懂原文，再把其中几个表达放进自己的简单句里。"
    )


def build_pdf_reading(topic: dict[str, Any], chunks: list[dict[str, Any]], source_pages: str, required: list[dict[str, str]], extended: list[dict[str, str]]) -> dict[str, Any]:
    spanish = reading_excerpt(chunks, topic)
    expressions = [entry["term"] for entry in required[:5]] + [row["term"] for row in extended[:3]]
    return {
        "source": f"PDF 参考页：{source_pages or '知识库综合主题'}；如原文过长，已节选为适合 20-30 分钟学习的一小段。",
        "spanish": spanish,
        "chinese": reading_translation(topic, source_pages),
        "expressions": list(dict.fromkeys(expressions))[:8],
        "summary": f"这段主要围绕“{topic['title']}”展开，适合用来积累词汇、理解句子结构，并做轻量仿写。",
    }


def format_pdf_reading(reading: dict[str, Any]) -> str:
    expressions = "\n".join(f"- {item}" for item in reading["expressions"])
    return f"""来源说明：{reading['source']}

【西语原文】
{reading['spanish']}

【中文翻译】
{reading['chinese']}

【重点表达】
{expressions}

【一句话总结】
{reading['summary']}

【理解问题】
1. 这段话主要讨论了什么主题？
2. 从重点表达中选 2 个，说说它们在文中的作用。"""


B1_GRAMMAR_POINTS = [
    {
        "title": "tener que + infinitivo",
        "structure": "tener que + 动词原形",
        "explanation": "表示“必须、不得不”。这是 B1 高频结构，适合写日常计划、学习任务和建议。",
        "examples": [("Tengo que repasar las palabras nuevas.", "我必须复习新单词。"), ("Tenemos que leer el texto otra vez.", "我们得再读一遍课文。")],
        "mistake": "tener 要根据主语变位，不要写成 yo tener que。",
        "practice": ["Yo ______ estudiar todos los días. (tener que)", "把“我们必须读课文”翻译成西语。", "用 tener que 写一句关于学习的句子。"],
    },
    {
        "title": "hay que + infinitivo",
        "structure": "hay que + 动词原形",
        "explanation": "表示一般性的“应该、需要”，不强调具体是谁做。",
        "examples": [("Hay que escuchar el audio dos veces.", "需要听两遍音频。"), ("Hay que escribir frases cortas.", "应该写短句。")],
        "mistake": "hay que 后面直接接动词原形，不要变位。",
        "practice": ["Hay que ______ el ejemplo. (leer)", "把“应该复习词组”翻译成西语。", "用 hay que 写一句学习建议。"],
    },
    {
        "title": "porque / como 的基础区别",
        "structure": "porque 放在原因解释中；como 常放句首，引出原因",
        "explanation": "porque 回答“为什么”；como 放在句首时，先说明原因，再说结果。",
        "examples": [("No salgo porque tengo que estudiar.", "我不出门，因为我得学习。"), ("Como tengo poco tiempo, leo un texto corto.", "因为我时间少，所以读一篇短文。")],
        "mistake": "como 表原因时通常放句首；不要把所有“因为”都机械写成 porque。",
        "practice": ["No compro este producto ______ es caro.", "______ necesito practicar, escribo tres frases.", "用 porque 写一句关于今天词汇的句子。"],
    },
    {
        "title": "antes de / después de + infinitivo",
        "structure": "antes de / después de + 动词原形",
        "explanation": "用来表达两个动作的先后顺序，适合讲学习流程。",
        "examples": [("Antes de escribir, leo el ejemplo.", "写之前，我读例句。"), ("Después de estudiar, hago un pequeño test.", "学习之后，我做一个小测试。")],
        "mistake": "de 不要漏掉；后面接动词原形，不要变位。",
        "practice": ["Antes de ______, reviso las palabras. (escribir)", "把“学习之后我做练习”翻译成西语。", "用 después de 写一句自己的学习习惯。"],
    },
    {
        "title": "aunque + indicativo",
        "structure": "aunque + 陈述式",
        "explanation": "当你说的是已知事实或真实情况时，aunque 后面可以用陈述式，表示“虽然”。",
        "examples": [("Aunque el texto es corto, tiene palabras útiles.", "虽然文本很短，但有有用的词。"), ("Aunque la gramática parece difícil, el ejemplo es claro.", "虽然语法看起来难，但例子很清楚。")],
        "mistake": "当前阶段先掌握 aunque + indicativo，不要急着大量使用虚拟式。",
        "practice": ["Aunque el ejercicio ______ fácil, necesito practicar. (ser)", "把“虽然句子很短，但很有用”翻译成西语。", "用 aunque 写一句关于今天阅读的句子。"],
    },
]


def build_b1_grammar(topic: dict[str, Any], variant: int = 0) -> dict[str, Any]:
    key = grammar_key(topic)
    offset = {"conectores": 2, "subjuntivo": 4, "narración": 3, "condicional": 0}.get(key, 0)
    return B1_GRAMMAR_POINTS[(variant + offset) % len(B1_GRAMMAR_POINTS)]


def format_b1_grammar(point: dict[str, Any]) -> str:
    practice = "\n".join(f"{index}. {item}" for index, item in enumerate(point["practice"], start=1))
    example_1, translation_1 = point["examples"][0]
    example_2, translation_2 = point["examples"][1]
    return f"""【今日语法】{point['title']}

【结构】{point['structure']}
【中文解释】{point['explanation']}
【例句 1】
{example_1}
{translation_1}
【例句 2】
{example_2}
{translation_2}
【常见错误】{point['mistake']}
【小练习】
{practice}"""


def build_light_output(required: list[dict[str, str]], grammar: dict[str, Any], topic: dict[str, Any]) -> str:
    p1, p2, p3, p4, p5 = [entry["term"] for entry in required[:5]]
    return f"""### 第一层：控制练习

【填空 1】No estoy ______ acuerdo con esta idea. (de / con)
【填空 2】Antes de ______, leo el ejemplo. (escribir)
【填空 3】Hay que ______ las palabras nuevas. (repasar)

【中译西 1】我认为这个例子很清楚。
【中译西 2】我必须复习今天的词组。
【中译西 3】虽然文本很短，但是很有用。

### 第二层：仿写练习

【仿写 1】框架：En mi opinión, ...
提示：用 “{p1}” 或 “{p2}” 写一个简单观点句。

【仿写 2】框架：Tengo que ... antes de ...
提示：写一个自己的学习习惯。

【仿写 3】框架：Aunque ..., ...
提示：用今天的阅读主题写一句让步句。

### 第三层：小段输出

【写作任务】围绕“{topic['title']}”写 50-80 词的小段落。不要写长作文，目标是把今天词汇用稳。

【写作框架】
1. En mi opinión, ...
2. Por ejemplo, ...
3. Aunque ..., ...
4. Por eso, tengo que ...

【要求】至少使用 5 个今日词汇或词组：{p1}、{p2}、{p3}、{p4}、{p5}。"""


def build_b1_quiz(required: list[dict[str, str]], extended: list[dict[str, str]], grammar: dict[str, Any]) -> str:
    first = required[0]
    second = required[1]
    vocab = extended[0]
    return f"""1. 词汇选择：{first['term']} 的意思最接近：A. {first['meaning']} B. 完全相反 C. 专业术语
2. 词汇选择：{vocab['term']} 的中文意思是：A. {vocab['meaning']} B. 不知道 C. 与今天主题无关
3. 语法填空：{grammar['practice'][0]}
4. 中译西：我认为这个文本很有用。
5. 句型转换：把 “Leo el ejemplo. Después escribo una frase.” 改成 “Después de ...”。
6. 阅读理解：今天 PDF 精读段落的主要主题是什么？"""


def build_b1_answers(required: list[dict[str, str]], extended: list[dict[str, str]], grammar: dict[str, Any]) -> str:
    return f"""### 轻量输出训练参考答案

【答案 1】de
【解析】固定搭配是 estar de acuerdo。常见错误是漏掉 de。

【答案 2】escribir
【解析】antes de 后面接动词原形。记住 antes de + infinitivo。

【答案 3】repasar
【解析】hay que 后面接动词原形，不要写成 repasas。

【答案 4】Creo que este ejemplo es claro.
【解析】creo que 表达肯定观点，后面先用陈述式。记住 creo que + indicativo。

【答案 5】Tengo que repasar los grupos de palabras de hoy.
【解析】tener que + infinitivo 表示“必须”。tener 要按主语变位。

【答案 6】Aunque el texto es corto, es muy útil.
【解析】这里说的是事实，可以先用 aunque + indicativo。

### 今日小测试参考答案

【答案 1】A. {required[0]['meaning']}
【解析】{required[0]['term']} 是今天必背词组，要能从中文意思反推西语。

【答案 2】A. {extended[0]['meaning']}
【解析】扩展词汇不需要长篇背诵，但要能在例句里认出来。

【答案 3】参考语法小练习答案
【解析】今天语法点是 {grammar['title']}；做题时先看结构：{grammar['structure']}。

【答案 4】Creo que este texto es muy útil.
【解析】B1 阶段先把 creo que + 简单句写稳。

【答案 5】Después de leer el ejemplo, escribo una frase.
【解析】después de 后面接 infinitivo。常见错误是把 leer 变位。

【答案 6】答案可用中文概括：围绕今天 PDF 主题，理解常用词组、句型和文本意思。
【解析】阅读题重点不是猜难词，而是抓主题和高频表达。"""


def build_b1_spaced_review(plan: list[dict[str, Any]], current_day: int, today: date) -> str:
    def past_material(day_number: int) -> tuple[dict[str, Any], int]:
        topic = topic_for_lesson(plan, day_number)
        return topic, variant_for_lesson(day_number, len(plan))

    lines = []
    tasks = []
    if current_day > 1:
        target_day = current_day - 1
        topic, variant = past_material(target_day)
        phrases = build_required_phrases(topic, [], variant)[:5]
        lines.append(f"### 昨天的 5 个词组（Día {target_day}）")
        lines.extend(f"- {entry['term']}：{entry['meaning']}" for entry in phrases)
        tasks.append(f"1. 从昨天词组里选 2 个，各写一个短句。")
    else:
        lines.append("### 昨天的 5 个词组")
        lines.append("- 今天是第 1 天，还没有昨天内容；明天开始自动复习。")

    if current_day > 3:
        target_day = current_day - 3
        topic, variant = past_material(target_day)
        vocab = build_extended_vocab(topic, [], [], variant)[:5]
        lines.append(f"\n### 3 天前的 5 个词汇（Día {target_day}）")
        lines.extend(f"- {row['term']}：{row['meaning']}" for row in vocab)
        tasks.append("2. 从 3 天前词汇里选 2 个，口头造句。")
    else:
        lines.append("\n### 3 天前的 5 个词汇")
        lines.append("- 历史天数还不够，暂时跳过。")

    if current_day > 7:
        target_day = current_day - 7
        topic, variant = past_material(target_day)
        grammar = build_b1_grammar(topic, variant)
        lines.append(f"\n### 7 天前的 1 个语法点（Día {target_day}）")
        lines.append(f"- {grammar['title']}：{grammar['structure']}")
        tasks.append("3. 用 7 天前语法点写 1 个句子。")
    else:
        lines.append("\n### 7 天前的 1 个语法点")
        lines.append("- 历史天数还不够，暂时跳过。")

    if not tasks:
        tasks = ["1. 从今天内容中选 3 个最想记住的词，读两遍。"]
    lines.append("\n【复习小题】")
    lines.extend(tasks[:5])
    return "\n".join(lines)


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
                f"### 词汇 {index}：{entry['term']}",
                f"【意思】{entry['meaning']}",
                f"【使用场景】{entry['usage']}",
                "西语：",
                entry["example"],
                "中文：",
                entry["translation"],
                f"【注意】{entry['note']}",
            ]
        )
    return "\n".join(lines)


def format_patterns(patterns: list[dict[str, str]]) -> str:
    lines = []
    for index, pattern in enumerate(patterns, start=1):
        lines.extend(
            [
                f"### 句型 {index}：{pattern['structure']}",
                f"【结构】{pattern['structure']}",
                f"【中文解释】{pattern['explanation']}",
                f"【适用场景】{pattern['scene']}",
                "西语：",
                pattern["example"],
                "中文：",
                pattern["translation"],
                f"【仿写提示】先保留结构，只替换主题、动词和例子。{pattern['mode']}。",
            ]
        )
    return "\n".join(lines)


def format_grammar(points: list[dict[str, Any]]) -> str:
    lines = []
    for index, point in enumerate(points, start=1):
        lines.extend([f"### 语法点 {index}：{point['title']}", f"【核心规则】{point['rule']}"])
        for example_index, (example, translation) in enumerate(point["examples"][:3], start=1):
            lines.append(f"【例句 {example_index}】")
            lines.append("西语：")
            lines.append(example)
            lines.append("中文：")
            lines.append(translation)
        lines.append(f"【中国学生常错点】{point['mistake']}")
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

【阅读理解问题】这段话认为，一个 B2 回答为什么不能只停留在简单观点？

【仿写任务】仿照这段结构，用 3-4 句写一个关于你学习西语方法的小段落。"""


def build_controlled_practice(vocab_entries: list[dict[str, str]], patterns: list[dict[str, str]]) -> str:
    return f"""### 第一层：控制练习

【填空 1】Es importante que el estudiante ______ los errores antes de entregar el texto. (revisar)

【填空 2】No creo que memorizar listas ______ suficiente para hablar mejor. (ser)

【句型替换 1】把 “Es bueno practicar cada día.” 改成 “Es + adjetivo + que + subjuntivo” 结构。

【句型替换 2】用 “{patterns[0]['structure']}” 改写：El tema es difícil, pero se puede explicar con ejemplos."""


def build_half_open_output(vocab_entries: list[dict[str, str]], patterns: list[dict[str, str]]) -> str:
    chosen_terms = "、".join(entry["term"] for entry in vocab_entries[:2])
    return f"""### 第二层：半开放练习

【造句 1】用今天的词组造句：{vocab_entries[0]['term']}。
提示：12-18 个词即可，先保证语法稳定。

【造句 2】用今天的词组造句：{vocab_entries[1]['term']}。
提示：可以模仿词汇表里的例句。

【段落回答】根据精读段落回答：¿Qué ayuda a que una respuesta sea más clara y organizada?
提示：回答 1-2 句即可，尽量使用 {chosen_terms}。"""


def build_dele_output(topic: dict[str, Any], patterns: list[dict[str, str]]) -> str:
    return f"""### 第三层：小输出

【写作任务】围绕“{topic['title']}”写 50-80 词。不要写长作文，只写一个清楚段落。

【写作框架】
1. Para empezar, creo que ...
2. Un ejemplo claro es que ...
3. Aunque ..., conviene reconocer que ...
4. En definitiva, ...

【要求】至少使用 2 个今日词组和 1 个今日句型。今天的目标是说清楚，不是写很长。"""


def build_quiz(vocab_entries: list[dict[str, str]], patterns: list[dict[str, str]]) -> str:
    first = vocab_entries[0]["term"]
    first_meaning = vocab_entries[0]["meaning"]
    return f"""1. 词汇选择：No creo que esta explicación sea ______. A. suficiente B. suficientes C. suficiencia
2. 词汇选择：{first} 的中文意思最接近：A. {first_meaning} B. 完全否定 C. 过去常常
3. 语法填空：Es necesario que tú ______ con ejemplos. (practicar)
4. 翻译：我担心这个练习太难。
5. 句型转换：把 “Practicar es importante.” 改成 “Es importante que ...”
6. 阅读理解：精读段落提到哪两种方式可以让表达更有条理？"""


def build_answers(vocab_entries: list[dict[str, str]]) -> str:
    first = vocab_entries[0]["term"]
    return f"""### 控制练习参考答案

【答案 1】revise
【解析】Es importante que 后面用 subjuntivo，所以 revisar 变成 revise。常见错误是写成 revisa 或 revisas。

【答案 2】sea
【解析】No creo que 表达否定看法，后面常用 subjuntivo。记住 no creo que sea。

【答案 3】Es bueno que practiques cada día.
【解析】中文仍然是“每天练习很好”，但西语要换成 que + subjuntivo。

【答案 4】Aunque el tema sea difícil, conviene reconocer que se puede explicar con ejemplos.
【解析】这里用 aunque + subjuntivo 表示让步假设；如果强调事实，也可以用 es。

### 今日小测试参考答案

【答案 1】A. suficiente
【解析】suficiente 修饰 explicación，单数形式不变。不要误写成名词 suficiencia。

【答案 2】A
【解析】{first} 的意思要按今天词汇表记忆，不要只凭单词外形猜。

【答案 3】practiques
【解析】Es necesario que + subjuntivo。常见错误是写 practicas。

【答案 4】Temo que este ejercicio sea demasiado difícil.
【解析】Temo que 后面通常用 subjuntivo。记住 temo que sea。

【答案 5】Es importante que practiques.
【解析】这个转换的重点是把名词化表达改成 que 从句。

【答案 6】可以通过具体例子和连接表达来让表达更有条理。
【解析】B2 不是单纯用难词，而是让观点、例子和逻辑关系更清楚。"""


def build_spaced_review(plan: list[dict[str, Any]], current_day: int, today: date) -> str:
    def past_topic(day_number: int) -> tuple[dict[str, Any], int]:
        topic = topic_for_lesson(plan, day_number)
        return topic, variant_for_lesson(day_number, len(plan))

    sections = []

    if current_day > 1:
        target_day = current_day - 1
        topic, variant = past_topic(target_day)
        vocab = build_vocab_entries(topic, [], variant)
        items = vocab[:2]
        quick_review = "\n".join(
            f"- {entry['term']}：{entry['meaning']}。例句：{entry['example']}"
            for entry in items
        )
        tasks = "\n".join(
            f"{index}. 用 “{entry['term']}” 写一个 10-15 个词的句子，并检查固定介词或 que 从句。"
            for index, entry in enumerate(items, start=1)
        )
    else:
        quick_review = "- 今天是第 1 天，还没有昨天的内容可复习。请把今天最有用的 2 个词组圈出来，明天会自动回收。"
        tasks = "1. 从今天词汇里选 1 个表达，写一个 10-15 个词的句子。"
    sections.append(f"""### 昨天 2 个词组
【快速回顾】
{quick_review}

【小题】
{tasks}""")

    if current_day > 3:
        target_day = current_day - 3
        topic, variant = past_topic(target_day)
        pattern = build_sentence_patterns(topic, variant)[0]
        target_date = (today - timedelta(days=3)).isoformat()
        quick_review = (
            f"- Día {target_day}（{target_date}）：{pattern['structure']}。"
            f"用法：{pattern['explanation']}。例句：{pattern['example']}"
        )
        tasks = f"1. 保留这个结构，换成你今天的学习主题写一句新句子。"
    else:
        quick_review = "- 还没到第 4 天，所以暂时没有 3 天前的句型可复习。"
        tasks = "1. 复述今天最重要的 1 个句型，并口头替换一个关键词。"
    sections.append(f"""### 3 天前 1 个句型
【快速回顾】
{quick_review}

【小题】
{tasks}""")

    if current_day > 7:
        target_day = current_day - 7
        topic, variant = past_topic(target_day)
        grammar = build_grammar_points(topic, variant)[0]
        example, translation = grammar["examples"][0]
        target_date = (today - timedelta(days=7)).isoformat()
        quick_review = (
            f"- Día {target_day}（{target_date}）：{grammar['title']}。"
            f"规则提醒：{grammar['rule']} 例句：{example} / {translation}"
        )
        tasks = "1. 用这个语法点写一个短句。2. 标出最容易写错的动词形式或连接词。"
    else:
        quick_review = "- 还没到第 8 天，所以暂时没有 7 天前的语法点可复习。"
        tasks = "1. 用今天的语法点写一句短句，明天继续回收。"
    sections.append(f"""### 7 天前 1 个语法点
【快速回顾】
{quick_review}

【小题】
{tasks}""")

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
    new_items = [entry["term"] for entry in vocab[:4]] + [grammar_note]
    for index, item in enumerate(new_items, start=1):
        card_id = f"{today.isoformat()}-{topic['day_in_cycle']}-{index}"
        if card_id in existing:
            continue
        cards.append(
            {
                "id": card_id,
                "front": item,
                "back": f"用这个表达围绕“{topic['title']}”造一句 B1+ 风格的句子。",
                "created_at": today.isoformat(),
                "due_date": (today + timedelta(days=1)).isoformat(),
                "review_count": 0,
                "last_reviewed": None,
            }
        )
    return cards


def build_lesson(knowledge: dict[str, Any], day_number: int, today: date, cards_path: Path) -> dict[str, str]:
    _ = cards_path
    plan = knowledge["course_plan"]
    topic = topic_for_lesson(plan, day_number)
    variant = variant_for_lesson(day_number, len(plan))
    chunks = select_chunks(knowledge, topic, limit=4, variant=variant)
    required_phrases = build_required_phrases(topic, chunks, variant)
    extended_vocab = build_extended_vocab(topic, chunks, required_phrases, variant)
    grammar_point = build_b1_grammar(topic, variant)

    source_pages = ", ".join(
        f"p.{chunk['page_start']}" if chunk["page_start"] == chunk["page_end"] else f"p.{chunk['page_start']}-{chunk['page_end']}"
        for chunk in chunks
    )
    reading = build_pdf_reading(topic, chunks, source_pages, required_phrases, extended_vocab)
    review_block = build_b1_spaced_review(plan, day_number, today)

    markdown = f"""# 西语 B1 巩固与 B2 过渡 - Día {day_number}

## 今日目标
【具体目标】今天掌握 8 个与“{topic['title']}”相关的常用词组，并能用其中 5 个写出简单句子。

【学习定位】以 PDF 的 B1 内容为主，先积累词汇和固定搭配，再做少量 B1+ 输出。

【预计用时】20-30 分钟。输入约 70%，输出约 30%。

【PDF 来源】{source_pages or '知识库综合复习'}

## 今日必背词组：8 个
{format_required_phrases(required_phrases)}

## 今日扩展词汇：10-15 个
{format_extended_vocab(extended_vocab)}

## PDF 精读：1 段
{format_pdf_reading(reading)}

## 今日语法小点：1 个
{format_b1_grammar(grammar_point)}

## 轻量输出训练
{build_light_output(required_phrases, grammar_point, topic)}

## 间隔复习
{review_block}

## 今日小测试（5-6 题）
{build_b1_quiz(required_phrases, extended_vocab, grammar_point)}

## 答案与解析
{build_b1_answers(required_phrases, extended_vocab, grammar_point)}
"""

    html_body = markdown_to_html(markdown)
    return {"markdown": markdown, "html": html_body, "subject": f"西语 B1 巩固与 B2 过渡 Día {day_number} - {topic['title']}"}


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
    parser = argparse.ArgumentParser(description="Generate today's B1 consolidation and B2 bridge lesson.")
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

    today = date.fromisoformat(args.lesson_date) if args.lesson_date else current_lesson_date()
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
