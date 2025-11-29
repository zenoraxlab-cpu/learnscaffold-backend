from typing import Optional
from pydantic import BaseModel


class StudyPlanRequest(BaseModel):
    document_id: str
    language: str = "en"
    days: int = 14

    # новые поля
    include_flashcards: bool = False
    flashcards_per_lesson: Optional[int] = None
