from sqlmodel import Session, select
from database import sync_engine
from models import Agent
import sys

# Set output encoding to utf-8 just in case, catch errors silently
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

import yaml
from pathlib import Path

def load_prompts():
    path = Path(__file__).parent / "resources" / "default_prompts.yaml"
    if not path.exists():
        print(f"WARNING: Prompts file not found at {path}")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("agents", {})

def seed_agents():
    """
    Creates basic agents in DB if not exist.
    """
    print("Checking agents...")
    
    agents_config = load_prompts()
    agents_to_seed = []
    
    for slug, data in agents_config.items():
        agents_to_seed.append({
            "slug": slug,
            "name": data["name"],
            "description": data["description"],
            "system_prompt": data["system_prompt"],
            "avatar_url": data.get("avatar_url"),
            "greeting_message": data.get("greeting") # Also seed greeting
        })

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
                    print(f"Updating agent: {agent_data['slug']}...")
                    existing_agent.name = agent_data["name"]
                    existing_agent.description = agent_data["description"]
                    existing_agent.system_prompt = agent_data["system_prompt"]
                    existing_agent.avatar_url = agent_data.get("avatar_url")
                    existing_agent.greeting_message = agent_data.get("greeting")
                    session.add(existing_agent)
            
            session.commit()
        print("SEEDING DONE SUCCESS.")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    seed_agents()
