from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, text, ForeignKey
from typing import AsyncGenerator
import structlog
from datetime import datetime

from health_ai_agent.config import settings

logger = structlog.get_logger()

# Async engine
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=3600,    # Recycle connections every hour
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()


class Patient(Base):
    __tablename__ = "mimic_discharge_summaries"
    
    
    hadm_id = Column(Integer, primary_key=True, name="HADM_ID")
    subject_id = Column(Integer, name="SUBJECT_ID")
    gender = Column(String, name="GENDER")
    age_corrected = Column(Integer, name="AGE_CORRECTED")
    admission_type = Column(String, name="ADMISSION_TYPE")
    diagnosis = Column(Text, name="DIAGNOSIS")
    hospital_expire_flag = Column(Boolean, name="HOSPITAL_EXPIRE_FLAG")
    ed_los_hours = Column(Float, name="ED_LOS_HOURS")
    total_los_hours = Column(Float, name="TOTAL_LOS_HOURS")
    charttime = Column(DateTime, name="CHARTTIME")
    category = Column(String, name="CATEGORY")
    description = Column(String, name="DESCRIPTION")
    text = Column(Text, name="TEXT")

class AISummary(Base):
    __tablename__ = "ai_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    hadm_id = Column(Integer, ForeignKey("mimic_discharge_summaries.HADM_ID"), nullable=False, index=True)
    summary_text = Column(Text, nullable=False)
    original_length = Column(Integer, nullable=False)
    processing_time = Column(Float, nullable=False)
    model_used = Column(String(100), default="m42-health/Llama3-Med42-8B")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", foreign_keys=[hadm_id])


# Dependency to get database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()


# Test database connection
async def test_connection():
    """Test if database connection works"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            row = result.fetchone()
            logger.info("Database connection successful", result=row[0])
            return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False
