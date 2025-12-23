import re
from typing import List, Dict, Any

UPPER_RE = re.compile(r"[A-ZА-ЯЁ]")

def _get_title(item: Any) -> str:
    # structure может быть list[str] или list[dict] с ключом title/name/text
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("title") or item.get("name") or item.get("text") or "").strip()
    return str(item).strip()

def build_mvp_plan_text(structure: List[Any], days: int = 10, max_len: int = 120, max_items: int = 60) -> str:
    if not structure:
        return "План пуст: структура не найдена."

    # 1) чистим и фильтруем
    cleaned: List[str] = []
    for it in structure:
        s = _get_title(it)
        if not s:
            continue
        s = " ".join(s.split())  # убрать лишние пробелы
        if len(s) > max_len:
            continue
        if not UPPER_RE.search(s):
            continue
        cleaned.append(s)

    if not cleaned:
        return "План пуст: после фильтрации ничего не осталось."

    # 2) первые N
    cleaned = cleaned[:max_items]

    # 3) дни
    days = max(1, int(days or 1))
    per_day = max(1, (len(cleaned) + days - 1) // days)  # ceil

    lines: List[str] = [f"Учебный план на {days} дней", ""]
    idx = 0
    for d in range(1, days + 1):
        chunk = cleaned[idx: idx + per_day]
        idx += per_day
        if not chunk:
            break
        lines.append(f"День {d}")
        for j, title in enumerate(chunk, 1):
            lines.append(f"{j}. {title}")
        lines.append("")

    return "\n".join(lines).strip()
