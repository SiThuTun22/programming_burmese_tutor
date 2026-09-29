LANG = "မြန်မာဘာသာဖြင့်သာ ရှင်းပြပါ"

BOOKS = {
    "programming_basic": ("Programming Basic", "Saturngod"),
    "database": ("Database Basic", "Saturngod"),
    "javascript": ("JavaScript - On Point", "Ei Maung"),
    "php": ("PHP - On Point", "Ei Maung"),
    "react": ("React - On Point", "Ei Maung"),
    "laravel": ("Laravel - On Point", "Ei Maung"),
    "api": ("API - On Point", "Ei Maung"),
    "bootstrap": ("Bootstrap - On Point", "Ei Maung"),
    "pwd": ("Professional Web Developer 2023", "Ei Maung"),
    "dsa": ("Data Structure & Algorithm In Burmese", "Hlaing Tin Htun"),
}

PREFIX = {
    "programming_basic": "pb",
    "database": "db",
    "javascript": "js",
    "php": "php",
    "react": "react",
    "laravel": "laravel",
    "api": "api",
    "bootstrap": "bs",
    "pwd": "pwd",
    "dsa": "dsa",
}

SPLIT_QUOTA = {
    "programming_basic": (18, 12),
    "database": (8, 5),
    "javascript": (6, 4),
    "php": (6, 4),
    "react": (5, 3),
    "laravel": (5, 3),
    "api": (4, 2),
    "bootstrap": (3, 2),
    "pwd": (3, 1),
    "dsa": (5, 3),
}


def item(task, question, output, terms, chapter, code=""):
    instruction = question.strip()
    if LANG not in instruction:
        instruction = f"{instruction} {LANG}"
    return {
        "task_type": task,
        "instruction": instruction,
        "input": code,
        "output": output.strip(),
        "source_chapter": chapter,
        "terms": terms,
    }
