from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class PatientBase(BaseModel):
    hadm_id: int
    subject_id: int
    gender: str
    age_corrected: Optional[int]
    admission_type: str
    diagnosis: str
    hospital_expire_flag: bool

class PatientResponse(PatientBase):
    ed_los_hours: Optional[float]
    total_los_hours: Optional[float]
    charttime: Optional[datetime]
    text_preview: Optional[str] = None
    
    class Config:
        from_attributes = True

class PatientDetail(PatientResponse):
    category: str
    description: str
    text: str

class PatientListResponse(BaseModel):
    patients: List[PatientResponse]
    total: int
    shown: int

class PatientCreate(BaseModel):
    hadm_id: int
    subject_id: int
    gender: str
    age_corrected: Optional[int] = None
    admission_type: str
    diagnosis: str
    hospital_expire_flag: bool = False
    ed_los_hours: Optional[float] = None
    total_los_hours: Optional[float] = None
    charttime: Optional[datetime] = None
    category: str = "Discharge summary"
    description: str = "Discharge summary"
    text: str