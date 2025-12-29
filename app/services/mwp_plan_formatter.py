# app/services/mwp_plan_formatter.py
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


SEPARATOR = "\n\n----------------\n\n"


@dataclass
class DayPlan:
    day_index: int
    topics: List[str]
    understand: List[str]
    pages: str  # already normalized like "1–15" or "15"


def _to_dict(ai_plan: Any) -> Dict[str, Any]:
    """Accepts dict or JSON string or plain text. Returns dict when possible."""
    if isinstance(ai_plan, dict):
        return ai_plan
    if isinstance(ai_plan, str):
        s = ai_plan.strip()
        # try JSON
        try:
            return json.loads(s)
        except Exception:
            return {"_raw_text": s}
    return {"_raw_text": str(ai_plan)}


def _normalize_pages(p: Any) -> str:
    """
    Normalizes pages into "a–b" with en-dash.
    Supports: "1-15", "1–15", [1,15], {"from":1,"to":15}, "стр. 10-20", etc.
    """
    if p is None:
        return "—"

    # list/tuple like [1, 15]
    if isinstance(p, (list, tuple)) and len(p) >= 2:
        a, b = p[0], p[1]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            a_i, b_i = int(a), int(b)
            return f"{a_i}–{b_i}" if a_i != b_i else f"{a_i}"

    # dict like {"from":1,"to":15} or {"start":...,"end":...}
    if isinstance(p, dict):
        a = p.get("from") or p.get("start") or p.get("a")
        b = p.get("to") or p.get("end") or p.get("b")
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            a_i, b_i = int(a), int(b)
            return f"{a_i}–{b_i}" if a_i != b_i else f"{a_i}"
        # fallback: stringify dict compactly
        p = " ".join([str(v) for v in p.values() if v is not None]).strip()

    # string: extract first two numbers
    s = str(p).strip()
    # unify dash
    s = s.replace("—", "-").replace("–", "-")
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        a_i, b_i = int(nums[0]), int(nums[1])
        return f"{a_i}–{b_i}" if a_i != b_i else f"{a_i}"
    if len(nums) == 1:
        return str(int(nums[0]))
    return "—"


def _as_list(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    if isinstance(x, str):
        # split by lines / semicolons
        parts = re.split(r"[\n;•]+", x)
        return [p.strip(" \t-–•") for p in parts if p.strip(" \t-–•")]
    return [str(x).strip()] if str(x).strip() else []


def _extract_days(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accepts multiple possible shapes:
      - {"days": [ {...}, {...} ]}
      - {"plan": {"days": [...]}}
      - {"schedule": [...]}
      - Raw text -> returns empty (then caller makes 1-day fallback)
    """
    for key_path in (("days",), ("plan", "days"), ("schedule",), ("result", "days")):
        cur: Any = plan
        ok = True
        for k in key_path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, list) and cur:
            return [d if isinstance(d, dict) else {"_raw": d} for d in cur]
    return []


def _fallback_from_raw_text(raw: str) -> List[DayPlan]:
    """
    If ai_plan came as plain text and is not JSON, make a single-day plan.
    This guarantees you ALWAYS return a valid MWP output.
    """
    raw = raw.strip()
    topics = _as_list(raw[:1200])  # just to have something deterministic
    topics = topics[:8] if topics else ["Материал из PDF (неструктурированный)"]
    return [
        DayPlan(
            day_index=1,
            topics=topics,
            understand=["Выделить ключевые определения и связи между темами"],
            pages="—",
        )
    ]


def format_mwp_text(ai_plan: Any) -> str:
    """
    Main MWP formatter:
      ai_plan -> strict text:
      День 1
      Темы:
      - ...
      ...
      ----------------
      День 2 ...
    """
    plan = _to_dict(ai_plan)

    # raw text fallback
    if "_raw_text" in plan and not _extract_days(plan):
        days = _fallback_from_raw_text(plan["_raw_text"])
        return SEPARATOR.join(_render_day(d) for d in days)

    raw_days = _extract_days(plan)
    if not raw_days:
        # last resort: pack whatever dict we have into day 1
        dump = json.dumps(plan, ensure_ascii=False)[:1500]
        days = _fallback_from_raw_text(dump)
        return SEPARATOR.join(_render_day(d) for d in days)

    days: List[DayPlan] = []
    for i, d in enumerate(raw_days, start=1):
        topics = _as_list(
            d.get("topics")
            or d.get("themes")
            or d.get("sections")
            or d.get("study_topics")
            or d.get("_raw")
        )
        understand = _as_list(
            d.get("what_to_understand")
            or d.get("understand")
            or d.get("goals")
            or d.get("objectives")
        )
        pages = _normalize_pages(d.get("pages") or d.get("page_range") or d.get("pageRange"))
        # strict limits (MWP: no стен текста)
        topics = topics[:10] if topics else ["—"]
        understand = understand[:8] if understand else ["—"]

        days.append(DayPlan(day_index=i, topics=topics, understand=understand, pages=pages))

    return SEPARATOR.join(_render_day(d) for d in days)


def _render_day(d: DayPlan) -> str:
    topics_block = "\n".join([f"- {t}" for t in d.topics]) if d.topics else "- —"
    understand_block = "\n".join([f"- {u}" for u in d.understand]) if d.understand else "- —"
    return (
        f"День {d.day_index}\n"
        f"Темы:\n{topics_block}\n\n"
        f"Что понять:\n{understand_block}\n\n"
        f"Страницы:\n{d.pages}"
    )
