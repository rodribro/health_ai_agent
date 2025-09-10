from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy import delete
import time

from ..config import settings
from ..services.database import get_db, Patient, AISummary
from ..schemas.ai import SummarizeRequest, SummarySavedResponse, SummaryListResponse, SummaryListItem
from ..services import ai_service




router = APIRouter()


@router.post("/summarize", response_model=SummarySavedResponse)
async def summarize_discharge(request: SummarizeRequest, 
                              db: AsyncSession = Depends(get_db),
                              client = Depends(ai_service.get_client),
                              hadm_id: int = Query(..., description="Hospital admission ID to summarize", example=170490),):
    """Summarize endpoint that uses Llama3-Med42 to generate a summary of a patient's hospital stay information.
        Gets the data from Patient.text column (discharge text)"""
    
    # Patient data
    query = select(Patient).where(Patient.hadm_id == hadm_id)
    result = await db.execute(query)
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check it summary already exists or not (only 1 per patient)
    existing_summary_query = select(AISummary).where(AISummary.hadm_id == request.hadm_id)
    existing_result = await db.execute(existing_summary_query)
    existing_summary = existing_result.scalar_one_or_none()
    
    if existing_summary:
        print(f"Returning existing summary for HADM_ID: {request.hadm_id}")
        return SummarySavedResponse(
                id=existing_summary.id,
                hadm_id=existing_summary.hadm_id,
                summary=existing_summary.summary_text,
                original_length=existing_summary.original_length,
                created_at=existing_summary.created_at,
                processing_time=existing_summary.processing_time,
                message="Patient already has a corresponding summary. New summary was not generated."
            )


    
    messages = [
            {
            "role":"system",
            "content":"You are a helpful, respectful and honest medical assistant. You are a second version of Med42 developed by the AI team at M42. "
            "Always answer as helpfully as possible, while being safe. "
            "Your answers should not include any harmful, unethical, racist, sexist, toxic, dangerous, or illegal content. "
            "Please ensure that your responses are socially unbiased and positive in nature. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. "
            "If you don’t know the answer to a question, please don’t share false information."
            },
            {"role":"user",
             "content":f"Summarize this discharge summary concisely:\n\n{patient.text[:4000]}"
            }

        ]
    
    start_time = time.time()
    
    try:
        response = client.chat_completion(
            messages=messages,
            max_tokens=400,
            temperature=0.5
        )
        summary = response.choices[0].message.content

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")
    
    processing_time = time.time() - start_time

    try:
        new_summary = AISummary(  
            hadm_id=patient.hadm_id,
            summary_text=summary,  
            original_length=len(patient.text),
            processing_time=processing_time
        )

        db.add(new_summary)
        await db.commit()
        await db.refresh(new_summary)

        print(f"AI Summary saved with ID: {new_summary.id}")

        return SummarySavedResponse(
            id=new_summary.id,
            hadm_id=new_summary.hadm_id,
            summary=new_summary.summary_text,
            original_length=new_summary.original_length,
            created_at=new_summary.created_at,
            processing_time=new_summary.processing_time
        )

        
    except Exception as e:
        await db.rollback()  # Use await for async rollback
        print(f"Error saving AI summary: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    

@router.get("/summaries", response_model=SummaryListResponse)
async def list_recent_summaries(
    limit: int = Query(5, ge=1, le=50, description="Number of summaries to retrieve (1-50)"),
    db: AsyncSession = Depends(get_db)
):
    """Get recent AI-generated summaries with user-specified limit"""
    
    try:
        # Get total count
        count_result = await db.execute(select(func.count()).select_from(AISummary))
        total_count = count_result.scalar()
        
        # If no summary
        if total_count == 0:
            return SummaryListResponse(
                summaries=[],
                total_count=0,
                shown_count=0
            )
        
        # Recent summaries
        query = (
            select(AISummary)
            .where(AISummary.summary_text.isnot(None))
            .order_by(AISummary.created_at.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        summaries = result.scalars().all()
        
        
        summary_items = []
        for summary in summaries:
            summary_items.append(SummaryListItem(
                id=summary.id,
                hadm_id=summary.hadm_id,
                summary=summary.summary_text, 
                original_length=summary.original_length,
                processing_time=summary.processing_time,
                created_at=summary.created_at
            ))
        
        return SummaryListResponse(
            summaries=summary_items,
            total_count=total_count,
            shown_count=len(summary_items)
        )
        
    except Exception as e:
        print(f"Error retrieving summaries: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.delete("/summaries/patient/{hadm_id}")
async def delete_patient_summaries(
    hadm_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete summary of a specific patient"""
    
    try:
        
        existing_query = select(AISummary).where(AISummary.hadm_id == hadm_id)
        existing_result = await db.execute(existing_query)
        existing_summaries = existing_result.scalars().all()
        
        if not existing_summaries:
            raise HTTPException(status_code=404, detail=f"No summaries found for patient {hadm_id}")
        
        
        delete_stmt = delete(AISummary).where(AISummary.hadm_id == hadm_id)
        await db.execute(delete_stmt)
        await db.commit()
        
        return {
            "message": f"Successfully deleted summary for patient {hadm_id}",
            "hadm_id": hadm_id
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    