from fastapi import APIRouter
from ..services.database import test_connection
from ..services import ai_service

router = APIRouter()

@router.get("/")
async def health():
    return {"status": "healthy"}

@router.get("/database")
async def database_health():
    connection = await test_connection()
    return {"status":"Connection to database successful!"} if connection else {"status": "Database connection failed"}

@router.get("/ai")
async def ai_model_health():
    """Check AI model availability and connection status"""
    
    try:
        model_info = ai_service.get_model_info()
        
        return {
            "status": "ready" if model_info.get("is_available") else "unavailable",
            "model_name": model_info.get("model_name"),
            "is_loaded": model_info.get("is_available", False),
            "initialized": model_info.get("initialized", False)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
