import asyncio
import pandas as pd
from health_ai_agent.services.database import AsyncSessionLocal, Patient
from health_ai_agent.config import settings
from sqlalchemy import text
import structlog
import sys


logger = structlog.get_logger()

async def load_parquet_data(parquet_file_path: str, batch_size: int = 1000):
    """Load MIMIC data from parquet file into PostgreSQL"""
    
    try:
        # Read parquet file
        logger.info("Reading parquet file", path=parquet_file_path)
        df = pd.read_parquet(parquet_file_path)
        logger.info("Original data", total_rows=len(df), unique_admissions=df['HADM_ID'].nunique())
        df_deduplicated = df.drop_duplicates(subset=['HADM_ID'], keep='last') # handle HADM_ID duplicate entries
        
        # Log basic info
        logger.info("Parquet file loaded", 
                   rows=len(df_deduplicated), 
                   columns=list(df_deduplicated.columns),
                   memory_usage_mb=df_deduplicated.memory_usage(deep=True).sum() / 1024**2)
        
        # Handle datetime columns - convert to proper datetime if they're strings
        if 'CHARTTIME' in df_deduplicated.columns:
            df_deduplicated['CHARTTIME'] = pd.to_datetime(df_deduplicated['CHARTTIME'], errors='coerce')
        
        # Handle NaN values
        df_deduplicated = df_deduplicated.fillna({
            'GENDER': 'Unknown',
            'ADMISSION_TYPE': 'Unknown', 
            'DIAGNOSIS': 'Not specified',
            'CATEGORY': 'Discharge summary',
            'DESCRIPTION': 'Discharge summary',
            'TEXT': '',
            'HOSPITAL_EXPIRE_FLAG': False
        })
        
        # Convert boolean columns
        if 'HOSPITAL_EXPIRE_FLAG' in df_deduplicated.columns:
            df_deduplicated['HOSPITAL_EXPIRE_FLAG'] = df_deduplicated['HOSPITAL_EXPIRE_FLAG'].astype(bool)
        
        total_rows = len(df_deduplicated)
        logger.info("Starting data insertion", total_rows=total_rows, batch_size=batch_size)
        
        # Process in batches for memory efficiency
        inserted_count = 0
        
        async with AsyncSessionLocal() as session:
            for start_idx in range(0, total_rows, batch_size):
                end_idx = min(start_idx + batch_size, total_rows)
                batch_df = df_deduplicated.iloc[start_idx:end_idx]
                
                # Create Patient objects for this batch
                patients = []
                for _, row in batch_df.iterrows():
                    # Map column names (handle case differences)
                    patient = Patient(
                        subject_id=int(row['SUBJECT_ID']) if pd.notna(row['SUBJECT_ID']) else None,
                        gender=str(row['GENDER']) if pd.notna(row['GENDER']) else 'Unknown',
                        hadm_id=int(row['HADM_ID']) if pd.notna(row['HADM_ID']) else None,
                        admission_type=str(row['ADMISSION_TYPE']) if pd.notna(row['ADMISSION_TYPE']) else 'Unknown',
                        diagnosis=str(row['DIAGNOSIS']) if pd.notna(row['DIAGNOSIS']) else 'Not specified',
                        hospital_expire_flag=bool(row['HOSPITAL_EXPIRE_FLAG']) if pd.notna(row['HOSPITAL_EXPIRE_FLAG']) else False,
                        age_corrected=int(row['age_corrected']) if pd.notna(row['age_corrected']) else None,
                        ed_los_hours=float(row['ed_los_hours']) if pd.notna(row['ed_los_hours']) else None,
                        total_los_hours=float(row['total_los_hours']) if pd.notna(row['total_los_hours']) else None,
                        charttime=row['CHARTTIME'] if pd.notna(row['CHARTTIME']) else None,
                        category=str(row['CATEGORY']) if pd.notna(row['CATEGORY']) else 'Discharge summary',
                        description=str(row['DESCRIPTION']) if pd.notna(row['DESCRIPTION']) else 'Discharge summary',
                        text=str(row['TEXT']) if pd.notna(row['TEXT']) else ''
                    )
                    patients.append(patient)
                
                # Add batch to session
                session.add_all(patients)
                
                # Commit every batch
                await session.commit()
                
                inserted_count += len(patients)
                logger.info("Batch inserted", 
                           batch=f"{start_idx+1}-{end_idx}", 
                           inserted=inserted_count, 
                           total=total_rows,
                           progress_pct=round(100 * inserted_count / total_rows, 1))
        
        logger.info("Data loading completed successfully", 
                   total_inserted=inserted_count,
                   database=settings.postgres_db)
        
        return inserted_count
        
    except Exception as e:
        logger.error("Data loading failed", error=str(e))
        raise

async def check_data_count():
    """Check how many records are in the database"""
    from sqlalchemy import text
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM mimic_discharge_summaries"))
        count = result.scalar()
        logger.info("Database record count", count=count)
        return count

async def show_sample_data(limit: int = 5):
    """Show sample data from the database"""
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text('SELECT "SUBJECT_ID", "HADM_ID", "GENDER", "AGE_CORRECTED", "ADMISSION_TYPE", LENGTH("TEXT") as text_length FROM mimic_discharge_summaries LIMIT :limit'),
            {"limit": limit}
        )
        rows = result.fetchall()
        
        logger.info("Sample data from database")
        for row in rows:
            print(f"Subject: {row[0]}, HADM: {row[1]}, Gender: {row[2]}, Age: {row[3]}, Type: {row[4]}, Text Length: {row[5]}")

async def clear_table():
    async with AsyncSessionLocal() as session:
        # Delete AI summaries
        await session.execute(text('DELETE FROM ai_summaries'))
        # Delete patients  
        await session.execute(text('DELETE FROM mimic_discharge_summaries'))
        await session.commit()
        print('Tables cleared')



async def load_pipeline(parquet_path: str):
        
       

        await clear_table()
        
        # Load the data
        count = await load_parquet_data(parquet_path)
        
        # Verify the data
        await check_data_count() 
        await show_sample_data()
        
        print(f"\n Successfully loaded {count} discharge summaries!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_data.py <path_to_parquet_file>")
        sys.exit(1)
    
    parquet_path = sys.argv[1]
    asyncio.run(load_pipeline(parquet_path=parquet_path))
    
    
    
    