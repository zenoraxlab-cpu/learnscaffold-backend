from typing import List, Optional, Any
from pydantic import BaseModel


class QuizItem(BaseModel):
    q: str
    a: str


class PlanDay(BaseModel):
    day_number: int
    title: str
    goals: List[str]
    theory: str
    practice: List[str]
    summary: str
    quiz: List[QuizItem]
    # Новое поле: номера страниц оригинального документа,
    # к которым относится материал этого дня
    source_pages: Optional[List[int]] = None


class PlanBlock(BaseModel):
    days: List[PlanDay]


class AnalysisBlock(BaseModel):
    document_type: str
    main_topics: List[str]
    level: str
    summary: str
    recommended_days: int


class StudyPlanResponse(BaseModel):
    status: str
    file_id: str
    days: int
    analysis: AnalysisBlock
    structure: List[Any]
    plan: PlanBlock


class AnalyzeRequest(BaseModel):
    file_id: str
    days: int
    # На будущее можно использовать для промпта/логики нагрузки
    lesson_duration: Optional[int] = None


class PlanPdfRequest(BaseModel):
    # финальный текст плана (из textarea на фронте)
    content: str
    # ID исходного файла, для логов/сопоставления
    file_id: str
    # количество дней/уроков в плане
    days: int
