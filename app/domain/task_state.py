# app/domain/task_state.py
from enum import Enum

class TaskStatus(str, Enum):
    QUEUED = "queued"
    CLASSIFYING = "classifying"
    STRUCTURE = "structure"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"

def set_status(task_id: str, status: TaskStatus, **meta):
    # TODO: писать в Redis / DB / JSON
    pass
