import asyncio
from health_ai_agent.services.database import engine, Base
from health_ai_agent.config import settings
from sqlalchemy import text
from health_ai_agent.services.database import AsyncSessionLocal
    
async def create_tables():
    """Create all database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created successfully!')


async def check_tables():
    """Check what tables exist"""
    
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        ))
        tables = [row[0] for row in result.fetchall()]
        print("Tables in database:", tables)

async def check_table_contents():
    """Check the contents of ai_summaries table"""
    print("\n Checking ai_summaries table contents...")
    
    async with AsyncSessionLocal() as session:
        # Count records
        result = await session.execute(text("SELECT COUNT(*) FROM ai_summaries"))
        count = result.scalar()
        print(f"   Total records: {count}")
        
        if count > 0:
            # Show sample records 
            result = await session.execute(text("""
                SELECT id, hadm_id, summary_text, original_length, processing_time, created_at
                FROM ai_summaries 
                WHERE summary_text IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            
            records = result.fetchall()
            print("\nRecent records:")
            for record in records:
                summary_preview = record[2][:100] + "..." if record[2] and len(record[2]) > 100 else record[2]
                print(f"   ID: {record[0]}, HADM_ID: {record[1]}")
                print(f"   Summary: {summary_preview}")
                print(f"   Original Length: {record[3]}, Processing Time: {record[4]:.2f}s")
                print(f"   Created: {record[5]}")
                print("\n ")


if __name__ == "__main__":
    print(__name__)
    #asyncio.run(check_table_contents())
    asyncio.run(create_tables())
    #asyncio.run(check_tables())

