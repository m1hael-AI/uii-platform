import asyncio
import json
import sys
import os
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Webinar
from database import async_session_factory
from config import settings

# Custom encoder for Date/Datetime
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

async def dump_webinars():
    print(f"Connecting to DB...")
    # Patch for local execution (host machine -> docker mapped port)
    original_url = settings.database_url
    patched_url = original_url.replace("@db:", "@localhost:")
    
    # We must RE-CREATE engine/session because database.py already initialized with 'db'
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    # Re-init for this script only
    async_db_url = patched_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_db_url, echo=False)
    local_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print(f"Using URL: {async_db_url}")

    async with local_session_factory() as db:
        result = await db.execute(select(Webinar))
        webinars = result.scalars().all()
        
        data = [w.model_dump() for w in webinars]
        
        # Save to file
        output_file = "webinars_dump.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, cls=DateTimeEncoder, ensure_ascii=False)
            
        print(f"✅ Exported {len(data)} webinars to {output_file}")

if __name__ == "__main__":
    asyncio.run(dump_webinars())
