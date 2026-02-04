import asyncio
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, text
from database import async_engine, AsyncSession
from models import (
    User, UserAction, UserMemory, Agent, SystemConfig, 
    PendingAction, ProactivitySettings, WebinarSignup, 
    ChatSession, Message, MagicLinkToken, PasswordResetToken
)

async def reset_database():
    """
    Clears all data from the database EXCEPT for Webinars.
    """
    print("WARNING: This will delete ALL data (Users, Chats, etc) except Webinars.")
    print("Are you sure? (y/n)")
    # Skip confirmation if running in non-interactive mode or force flag is present
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        pass
    else:
        # Simple input check - might not work in all envs, but safer
        try:
            choice = input().lower()
            if choice != 'y':
                print("Aborted.")
                return
        except EOFError:
            print("Non-interactive mode detected. Use --force to proceed without confirmation.")
            return

    async with AsyncSession(async_engine) as session:
        print("Starting cleanup...")
        
        # Disable foreign key checks temporarily to allow truncation/deletion in any order
        # or just delete in correct order (Children -> Parents)
        
        # 1. Delete dependent data (Leaf nodes)
        print("Deleting Messages...")
        await session.execute(delete(Message))
        
        print("Deleting PasswordResetTokens...")
        await session.execute(delete(PasswordResetToken))
        
        print("Deleting MagicLinkTokens...")
        await session.execute(delete(MagicLinkToken))
        
        print("Deleting PendingActions...")
        await session.execute(delete(PendingAction))
        
        print("Deleting WebinarSignups...")
        await session.execute(delete(WebinarSignup))
        
        print("Deleting UserActions...")
        await session.execute(delete(UserAction))
        
        print("Deleting UserMemories...")
        await session.execute(delete(UserMemory))
        
        # 2. Delete ChatSessions (depends on Users, Agents, Webinars)
        print("Deleting ChatSessions...")
        await session.execute(delete(ChatSession))
        
        # 3. Delete Users (Parents for many)
        print("Deleting Users...")
        await session.execute(delete(User))
        
        # We generally keep Agents, SystemConfig, ProactivitySettings as they are configuration
        # But if the user said "Clean DB, keep ONLY webinars", maybe we should ask?
        # Usually Agents are part of the system core. I will KEEP Agents and Settings for now as they are "code/config" rather than "user data".
        # If the user wants to clear agents too, they can uncomment below.
        
        # print("Deleting Agents...")
        # await session.execute(delete(Agent))
        
        # print("Deleting SystemConfig...")
        # await session.execute(delete(SystemConfig))
        
        # print("Deleting ProactivitySettings...")
        # await session.execute(delete(ProactivitySettings))

        await session.commit()
        print("Database cleared successfully (Webinars, Agents, Configs preserved).")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_database())
