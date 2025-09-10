from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from typing import Optional
from datetime import datetime

from ..services.database import get_db, Patient
from ..schemas.patient import PatientResponse, PatientDetail, PatientListResponse, PatientCreate
from ..services.database import AISummary

router = APIRouter()

@router.post("/", response_model=PatientDetail)
async def create_patient(
    hadm_id: int = Query(..., description="Hospital admission ID", example=999999),
    subject_id: int = Query(..., description="Patient subject ID", example=12345),
    gender: str = Query(..., description="Patient gender (M/F)", example="M"),
    admission_type: str = Query(..., description="Type of admission", example="EMERGENCY"),
    diagnosis: str = Query(..., description="Primary diagnosis", example="Chest pain"),
    text: str = Query(..., description="Full discharge summary text", example="Patient presented with chest pain..."),
    age_corrected: Optional[int] = Query(None, description="Patient age", example=65),
    hospital_expire_flag: bool = Query(False, description="Did patient expire in hospital"),
    ed_los_hours: Optional[float] = Query(None, description="Emergency department length of stay", example=4.5),
    total_los_hours: Optional[float] = Query(None, description="Total length of stay", example=72.0),
    charttime: Optional[datetime] = Query(None, description="Chart time", example="2025-09-09T14:30:00Z"),
    category: str = Query("Discharge summary", description="Document category"),
    description: str = Query("Discharge summary", description="Document description"),
    db: AsyncSession = Depends(get_db)
):
    """Insert a new hospital admission (patient record)"""
    
    try:
        # Check if HADM_ID already exists
        existing_query = select(Patient).where(Patient.hadm_id == hadm_id)
        existing_result = await db.execute(existing_query)
        existing_patient = existing_result.scalar_one_or_none()
        
        if existing_patient:
            raise HTTPException(
                status_code=409, 
                detail=f"Patient with HADM_ID {hadm_id} already exists"
            )

        # Process charttime to avoid timezone conflicts
        processed_charttime = charttime.replace(tzinfo=None) if charttime else None
        
        # Create new patient record
        new_patient = Patient(
            hadm_id=hadm_id,
            subject_id=subject_id,
            gender=gender,
            age_corrected=age_corrected,
            admission_type=admission_type,
            diagnosis=diagnosis,
            hospital_expire_flag=hospital_expire_flag,
            ed_los_hours=ed_los_hours,
            total_los_hours=total_los_hours,
            charttime=processed_charttime,
            category=category,
            description=description,
            text=text
        )
        
        db.add(new_patient)
        await db.commit()
        await db.refresh(new_patient)
        
        return PatientDetail.model_validate(new_patient)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    

    
@router.delete("/{hadm_id}")
async def delete_patient_and_summaries(
    hadm_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a hospital admission and associated AI summary"""
    
    try:
        
        patient_query = select(Patient).where(Patient.hadm_id == hadm_id)
        patient_result = await db.execute(patient_query)
        patient = patient_result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient with HADM_ID {hadm_id} not found")
        
        # Associated summary before deleting
        summaries_query = select(AISummary).where(AISummary.hadm_id == hadm_id)
        summaries_result = await db.execute(summaries_query)
        summaries = summaries_result.scalars().all()
        summaries_count = len(summaries)
        
        # Delete summary
        if summaries_count > 0:
            delete_summaries_stmt = delete(AISummary).where(AISummary.hadm_id == hadm_id)
            await db.execute(delete_summaries_stmt)
        
        # Delete patient record
        await db.delete(patient)
        await db.commit()
        
        return {
            "message": f"Successfully deleted patient {hadm_id}",
            "hadm_id": hadm_id,
            "deleted_summaries": summaries_count,
            "patient_info": {
                "subject_id": patient.subject_id,
                "diagnosis": patient.diagnosis
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    


@router.get("/list", response_model=PatientListResponse)
async def list_patients(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results", example=100),
    q: Optional[str] = Query(None, min_length=2, description="Search term for diagnosis, admission type, or gender", example="ASTHMA"),
    gender: Optional[str] = Query(None, description="Filter by gender (M/F)", example="M"),
    admission_type: Optional[str] = Query(None, description="Filter by admission type", example="EMERGENCY"),
    age_min: Optional[int] = Query(None, ge=0, le=120, description="Minimum age", example=18),
    age_max: Optional[int] = Query(None, ge=0, le=120, description="Maximum age", example=65),
    db: AsyncSession = Depends(get_db)
):
    """List patients with optional search and filtering"""
    
    try:
        # Base query
        query = select(Patient)
        count_query = select(func.count()).select_from(Patient)
        
        # Search elements
        if q:
            search_condition = (
                Patient.diagnosis.ilike(f"%{q}%") |
                Patient.admission_type.ilike(f"%{q}%") |
                Patient.gender.ilike(f"%{q}%")
            )
            query = query.where(search_condition)
            count_query = count_query.where(search_condition)
        
        # Filters
        if gender:
            query = query.where(Patient.gender == gender.upper())
            count_query = count_query.where(Patient.gender == gender.upper())
        if admission_type:
            query = query.where(Patient.admission_type.ilike(f"%{admission_type}%"))
            count_query = count_query.where(Patient.admission_type.ilike(f"%{admission_type}%"))
        if age_min is not None:
            query = query.where(Patient.age_corrected >= age_min)
            count_query = count_query.where(Patient.age_corrected >= age_min)
        if age_max is not None:
            query = query.where(Patient.age_corrected <= age_max)
            count_query = count_query.where(Patient.age_corrected <= age_max)
        
        # Limit of patients to be displayed
        query = query.limit(limit)
        
        
        result = await db.execute(query)
        patients_data = result.scalars().all()
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        
        patients = []
        for patient in patients_data:
            text_preview = patient.text[:200] + "..." if patient.text and len(patient.text) > 200 else (patient.text or "")
            patient_response = PatientResponse.model_validate(patient)
            patient_response.text_preview = text_preview
            patients.append(patient_response)
        
        return PatientListResponse(
            patients=patients,
            total=total,
            shown=len(patients)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/{hadm_id}", response_model=PatientDetail)
async def get_patient(hadm_id: int = Path(description="Hospital admission ID", example=170490), db: AsyncSession = Depends(get_db)):
    
    query = select(Patient).where(Patient.hadm_id==hadm_id)
    result = await db.execute(query)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    
    return PatientDetail.model_validate(patient)


