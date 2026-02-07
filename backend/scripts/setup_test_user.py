import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from database import async_engine, AsyncSession
from models import User, UserRole
from services.auth import get_password_hash


async def setup_test_user():
    """
    Creates or updates a test admin user with completed onboarding.
    
    User details:
    - Telegram ID: 1327165544
    - Email: admin@test.local
    - Password: test123
    - Role: ADMIN
    - Onboarding: Completed
    """
    
    TG_ID = 1327165544
    EMAIL = "admin@test.local"
    PASSWORD = "test123"
    
    async with AsyncSession(async_engine) as session:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.tg_id == TG_ID)
        )
        user = result.scalar_one_or_none()
        
        if user:
            print(f"✅ User with Telegram ID {TG_ID} already exists (ID: {user.id})")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role}")
            print(f"   Onboarding: {'✓' if user.is_onboarded else '✗'}")
            
            # Update user to ensure admin and onboarding status
            user.role = UserRole.ADMIN
            user.is_onboarded = True
            user.email = EMAIL
            user.hashed_password = get_password_hash(PASSWORD)
            
            await session.commit()
            print(f"\n🔄 Updated user settings:")
            print(f"   - Role: ADMIN")
            print(f"   - Onboarding completed: ✓")
            print(f"   - Email: {EMAIL}")
            print(f"   - Password: {PASSWORD}")
        else:
            # Create new user
            hashed_password = get_password_hash(PASSWORD)
            
            new_user = User(
                tg_id=TG_ID,
                email=EMAIL,
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                is_onboarded=True,
                created_at=datetime.utcnow()
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            print(f"✅ Created new test user (ID: {new_user.id})")
            print(f"   Telegram ID: {TG_ID}")
            print(f"   Email: {EMAIL}")
            print(f"   Password: {PASSWORD}")
            print(f"   Role: ADMIN")
            print(f"   Onboarding: ✓")
        
        print(f"\n🎯 You can now login with:")
        print(f"   Email: {EMAIL}")
        print(f"   Password: {PASSWORD}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(setup_test_user())
