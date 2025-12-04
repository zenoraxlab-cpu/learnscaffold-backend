# --------------------------------------------------------------
# Public function — generate full study plan for N days
# --------------------------------------------------------------
def generate_study_plan(
    total_days: int,
    document_type: str,
    main_topics: List[str],
    summary: str,
    structure: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Creates a full study plan consisting of multiple daily lessons.
    Each lesson is generated using generate_day_plan().
    """

    logger.info(f"[LLM_STUDY] Generating full plan for {total_days} days...")

    plan = []

    for day in range(1, total_days + 1):
        try:
            lesson = generate_day_plan(
                day_number=day,
                total_days=total_days,
                document_type=document_type,
                main_topics=main_topics,
                summary=summary,
                structure=structure,
            )
            plan.append(lesson)

        except Exception as e:
            logger.error(f"[LLM_STUDY] Failed to generate day {day}: {e}")
            plan.append({
                "day_number": day,
                "title": f"Day {day}",
                "goals": [],
                "theory": "",
                "practice": [],
                "summary": "",
                "quiz": [],
            })

    logger.info(f"[LLM_STUDY] Full study plan generated: {len(plan)} days")
    return plan
