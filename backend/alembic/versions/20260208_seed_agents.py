"""seed_agents_sql

Revision ID: 20260208_seed_agents
Revises: 20260208_seed
Create Date: 2026-02-08 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260208_seed_agents'
down_revision: Union[str, None] = '20260208_seed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL to upsert agents
    # This migration dynamically reads the default_prompts.yaml file.
    
    import yaml
    from pathlib import Path
    
    # Locate the YAML file relative to this migration file
    # This migration is in: backend/alembic/versions/
    # YAML is in: backend/resources/default_prompts.yaml
    # So we go up 2 levels (../../) and then into resources/
    yaml_path = Path(__file__).parent.parent.parent / "resources" / "default_prompts.yaml"
    
    if not yaml_path.exists():
        print(f"WARNING: Prompts file not found at {yaml_path}. Skipping agent seeding.")
        return

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            agents_config = data.get("agents", {})
    except Exception as e:
        print(f"ERROR: Failed to read prompts file: {e}")
        return

    agents = []
    for slug, data in agents_config.items():
        agents.append({
            "slug": slug,
            "name": data["name"],
            "description": data["description"],
            "system_prompt": data["system_prompt"],
            "greeting_message": data.get("greeting"), # Note: YAML key is 'greeting', DB col is 'greeting_message'
            "avatar_url": data.get("avatar_url")
        })

    for agent in agents:
        sql = sa.text("""
            INSERT INTO agents (slug, name, description, system_prompt, greeting_message, avatar_url)
            VALUES (:slug, :name, :description, :system_prompt, :greeting_message, :avatar_url)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                system_prompt = EXCLUDED.system_prompt,
                greeting_message = EXCLUDED.greeting_message,
                avatar_url = EXCLUDED.avatar_url;
        """)
        
        op.get_bind().execute(sql, agent)


def downgrade() -> None:
    pass
