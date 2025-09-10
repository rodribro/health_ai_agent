from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class SummarizeRequest(BaseModel):
    hadm_id: int

class SummarySavedResponse(BaseModel):
    id: int
    hadm_id: int
    summary: str
    original_length: int
    created_at: datetime
    processing_time: float
    message: Optional[str] = None

class SummaryListItem(BaseModel):
    id: int
    hadm_id: int
    summary: str
    original_length: int
    processing_time: float
    created_at: datetime

class SummaryListResponse(BaseModel):
    summaries: List[SummaryListItem]
    total_count: int
    shown_count: int


