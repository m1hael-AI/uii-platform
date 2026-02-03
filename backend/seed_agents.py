from sqlmodel import Session, select
from database import sync_engine
from models import Agent
import sys

# Set output encoding to utf-8 just in case, catch errors silently
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def seed_agents():
    """
    Creates basic agents in DB if not exist.
    """
    print("Checking agents...")
    
    # List of agents
    agents_to_seed = [
        {
            "slug": "mentor",
            "name": "AI Ментор",
            "description": "Персональный куратор по всем вопросам обучения.",
            "system_prompt": "Ты опытный ментор и куратор курсов. Твоя цель - помогать студентам с вопросами по материалам, давать подсказки, но не решать задачи за них полностью. Будь вежлив, поддерживай и мотивируй.",
            "avatar_url": "https://ui-avatars.com/api/?name=AI+Mentor&background=0D8ABC&color=fff"
        },
        {
            "slug": "main_assistant",
            "name": "AI Помощник",
            "description": "Навигатор по платформе и помощник.",
            "system_prompt": "Ты - AI Помощник всей платформы. Ты помогаешь пользователю ориентироваться в интерфейсе, находить настройки, расписание и решать технические вопросы. Ты вежлив, краток и полезен. Не придумывай функции, которых нет.",
            "avatar_url": "https://ui-avatars.com/api/?name=AI+Helper&background=6366f1&color=fff"
        },
        {
            "slug": "analyst",
            "name": "Data Analyst",
            "description": "Эксперт по анализу данных и Pandas.",
            "system_prompt": "Ты - эксперт уровня Senior Data Analyst. Ты отлично знаешь Python, Pandas, SQL, статистику и ML. Твоя задача - объяснять сложные концепции простым языком, помогать с кодом и ревьюить решения. Если просят код - давай его. Если просят объяснение - объясняй.",
            "avatar_url": "https://ui-avatars.com/api/?name=Data+Analyst&background=10b981&color=fff"
        },
        {
            "slug": "python",
            "name": "Python Эксперт",
            "description": "Эксперт по Python разработке.",
            "system_prompt": "Ты - Senior Python Developer. Ты помогаешь с архитектурой, чистотой кода (PEP8), паттернами проектирования и алгоритмами.",
            "avatar_url": "https://ui-avatars.com/api/?name=Python+Expert&background=f59e0b&color=fff"
        },
        {
            "slug": "hr",
            "name": "HR Консультант",
            "description": "Помощник по карьере и резюме.",
            "system_prompt": "Ты - опытный IT HR. Ты помогаешь составлять резюме, готовиться к собеседованиям, прокачивать Soft Skills и строить карьерный трек.",
            "avatar_url": "https://ui-avatars.com/api/?name=HR+Consultant&background=ec4899&color=fff"
        }
    ]

    try:
        with Session(sync_engine) as session:
            for agent_data in agents_to_seed:
                # Check exist
                statement = select(Agent).where(Agent.slug == agent_data["slug"])
                existing_agent = session.exec(statement).first()
                
                if not existing_agent:
                    print(f"Creating agent: {agent_data['slug']}...")
                    agent = Agent(**agent_data)
                    session.add(agent)
                else:
                    print(f"Agent exists: {agent_data['slug']}")
            
            session.commit()
        print("SEEDING DONE SUCCESS.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    seed_agents()
