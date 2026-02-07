import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from database import async_engine, AsyncSession
from models import User
from services.auth import get_password_hash


async def setup_test_user():
    """
    Creates or updates a test admin user with completed onboarding.
    
    User details:
    - Telegram ID: 1327165544
    - Email: admin@test.local
    - Password: test123
    - Admin: Yes
    - Onboarding: Completed
    """
    
    TELEGRAM_ID = 1327165544
    EMAIL = "admin@test.local"
    PASSWORD = "test123"
    
    async with AsyncSession(async_engine) as session:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.telegram_id == TELEGRAM_ID)
        )
        user = result.scalar_one_or_none()
        
        if user:
            print(f"✅ User with Telegram ID {TELEGRAM_ID} already exists (ID: {user.id})")
            print(f"   Email: {user.email}")
            print(f"   Admin: {user.is_admin}")
            print(f"   Onboarding: {'✓' if user.onboarding_completed else '✗'}")
            
            # Update user to ensure admin and onboarding status
            user.is_admin = True
            user.onboarding_completed = True
            user.email = EMAIL
            user.password_hash = get_password_hash(PASSWORD)
            
            await session.commit()
            print(f"\n🔄 Updated user settings:")
            print(f"   - Admin rights: ✓")
            print(f"   - Onboarding completed: ✓")
            print(f"   - Email: {EMAIL}")
            print(f"   - Password: {PASSWORD}")
        else:
            # Create new user
            hashed_password = get_password_hash(PASSWORD)
            
            new_user = User(
                telegram_id=TELEGRAM_ID,
                email=EMAIL,
                password_hash=hashed_password,
                is_admin=True,
                onboarding_completed=True,
                created_at=datetime.utcnow()
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            print(f"✅ Created new test user (ID: {new_user.id})")
            print(f"   Telegram ID: {TELEGRAM_ID}")
            print(f"   Email: {EMAIL}")
            print(f"   Password: {PASSWORD}")
            print(f"   Admin: ✓")
            print(f"   Onboarding: ✓")
        
        print(f"\n🎯 You can now login with:")
        print(f"   Email: {EMAIL}")
        print(f"   Password: {PASSWORD}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(setup_test_user())
