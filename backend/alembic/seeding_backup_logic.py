
# === SEEDING LOGIC BACKUP ===

def seed_agents(op):
    import yaml
    from pathlib import Path
    import sqlalchemy as sa
    
    # Locate the YAML file relative to this migration file
    yaml_path = Path(__file__).parent.parent.parent / "resources" / "default_prompts.yaml"
    
    if not yaml_path.exists():
        print(f"ERROR: Prompts file not found at {yaml_path}. Skipping agent seeding.")
        return

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            agents_config = data.get("agents", {})
    except Exception as e:
        print(f"ERROR: Failed to read prompts file: {e}")
        return

    print(f"SEEDING {len(agents_config)} AGENTS from {yaml_path}")
    
    for slug, data in agents_config.items():
        agent = {
            "slug": slug,
            "name": data["name"],
            "description": data["description"],
            "system_prompt": data["system_prompt"],
            "greeting_message": data.get("greeting"), # Note: YAML key is 'greeting', DB col is 'greeting_message'
            "avatar_url": data.get("avatar_url")
        }
        
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


def seed_proactivity(op):
    import sqlalchemy as sa
    import yaml
    from pathlib import Path
    
    print("SEEDING PROACTIVITY...")
    
    # 1. Ensure global settings exist
    op.execute("""
        INSERT INTO proactivity_settings (
            enabled,
            memory_update_interval,
            proactivity_timeout,
            check_interval,
            max_messages_per_day_agents,
            max_messages_per_day_assistant,
            summarizer_check_interval,
            summarizer_idle_threshold,
            context_soft_limit,
            context_threshold,
            context_compression_keep_last,
            rate_limit_per_minute,
            cron_expression,
            quiet_hours_start,
            quiet_hours_end,
            updated_at
        )
        SELECT 
            true,  -- enabled
            2.0,   -- memory_update_interval (hours)
            24.0,  -- proactivity_timeout (hours)
            2,     -- check_interval (minutes)
            3,     -- max_messages_per_day_agents
            3,     -- max_messages_per_day_assistant
            2,     -- summarizer_check_interval
            5,     -- summarizer_idle_threshold
            350000, -- context_soft_limit
            0.9,    -- context_threshold
            20,     -- context_compression_keep_last
            15,     -- rate_limit_per_minute
            '0 */2 * * *', -- cron_expression
            '22:00', -- quiet_hours_start
            '10:00', -- quiet_hours_end
            NOW()
        WHERE NOT EXISTS (SELECT 1 FROM proactivity_settings);
    """)
    
    # 2. Read Prompts from YAML
    yaml_path = Path(__file__).parent.parent.parent / "resources" / "default_prompts.yaml"
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"CRITICAL: Prompts file not found at {yaml_path}")

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            proactivity_prompts = data.get("proactivity_settings", {})
    except Exception as e:
        raise RuntimeError(f"CRITICAL: Failed to parse YAML: {e}")

    # Validate required prompts
    required_keys = ["agent_memory_prompt", "assistant_memory_prompt", "proactivity_trigger_prompt", "compression_prompt"]
    missing_keys = [key for key in required_keys if key not in proactivity_prompts]
    
    if missing_keys:
         # FALLBACK or ERROR? User asked for Error preferably or Fallback.
         # Let's error since this is initial migration and we expect file to be correct.
         raise ValueError(f"CRITICAL: Missing proactivity prompts in YAML: {missing_keys}")

    print("UPDATING PROACTIVITY PROMPTS from YAML...")
    
    # Update DB
    # We use parameters to avoid SQL injection even though it's trusted source
    sql = sa.text("""
        UPDATE proactivity_settings SET
            agent_memory_prompt = :agent_memory_prompt,
            assistant_memory_prompt = :assistant_memory_prompt,
            proactivity_trigger_prompt = :proactivity_trigger_prompt,
            compression_prompt = :compression_prompt
        WHERE (SELECT count(*) FROM proactivity_settings) > 0;
    """)
    
    op.get_bind().execute(sql, proactivity_prompts)
