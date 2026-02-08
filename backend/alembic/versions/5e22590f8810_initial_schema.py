"""initial_schema

Revision ID: 5e22590f8810
Revises: 
Create Date: 2026-02-08 10:51:17.743611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel



# revision identifiers, used by Alembic.
revision: str = '5e22590f8810'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



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


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('agents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('avatar_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('system_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('greeting_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agents_slug'), 'agents', ['slug'], unique=True)
    op.create_table('chat_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_chat_model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('user_chat_temperature', sa.Float(), nullable=False),
    sa.Column('user_chat_max_tokens', sa.Integer(), nullable=True),
    sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
    sa.Column('compression_model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('compression_temperature', sa.Float(), nullable=False),
    sa.Column('compression_max_tokens', sa.Integer(), nullable=True),
    sa.Column('context_threshold', sa.Float(), nullable=False),
    sa.Column('context_compression_keep_last', sa.Integer(), nullable=False),
    sa.Column('context_soft_limit', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('llm_audit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('agent_slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=False),
    sa.Column('cached_tokens', sa.Integer(), nullable=False),
    sa.Column('output_tokens', sa.Integer(), nullable=False),
    sa.Column('total_tokens', sa.Integer(), nullable=False),
    sa.Column('cost_usd', sa.Float(), nullable=False),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('request_json', sa.Text(), nullable=True),
    sa.Column('response_json', sa.Text(), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('error_message', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_audit_agent_slug'), 'llm_audit', ['agent_slug'], unique=False)
    op.create_index(op.f('ix_llm_audit_created_at'), 'llm_audit', ['created_at'], unique=False)
    op.create_index(op.f('ix_llm_audit_user_id'), 'llm_audit', ['user_id'], unique=False)
    op.create_table('proactivity_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('memory_model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('memory_temperature', sa.Float(), nullable=False),
    sa.Column('memory_max_tokens', sa.Integer(), nullable=True),
    sa.Column('trigger_model', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('trigger_temperature', sa.Float(), nullable=False),
    sa.Column('trigger_max_tokens', sa.Integer(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('cron_expression', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('quiet_hours_start', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('quiet_hours_end', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('max_messages_per_day_agents', sa.Integer(), nullable=False),
    sa.Column('max_messages_per_day_assistant', sa.Integer(), nullable=False),
    sa.Column('summarizer_check_interval', sa.Integer(), nullable=False),
    sa.Column('summarizer_idle_threshold', sa.Integer(), nullable=False),
    sa.Column('memory_update_interval', sa.Float(), nullable=False),
    sa.Column('proactivity_timeout', sa.Float(), nullable=False),
    sa.Column('max_consecutive_messages', sa.Integer(), nullable=False),
    sa.Column('context_soft_limit', sa.Integer(), nullable=True),
    sa.Column('context_threshold', sa.Float(), nullable=True),
    sa.Column('context_compression_keep_last', sa.Integer(), nullable=True),
    sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
    sa.Column('agent_memory_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('assistant_memory_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('compression_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('proactivity_trigger_prompt', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('system_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('value', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_configs_key'), 'system_configs', ['key'], unique=True)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tg_id', sa.BigInteger(), nullable=True),
    sa.Column('tg_username', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('tg_first_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('tg_last_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('tg_photo_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('phone', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('utm_source', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('utm_medium', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('utm_campaign', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('utm_content', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('quiz_answers', sa.JSON(), nullable=True),
    sa.Column('role', sa.Enum('ADMIN', 'USER', name='userrole'), nullable=False),
    sa.Column('is_onboarded', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('timezone', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('last_activity_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_tg_id'), 'users', ['tg_id'], unique=True)
    op.create_table('webinar_libraries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('video_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('speaker_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('transcript_context', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('is_published', sa.Boolean(), nullable=False),
    sa.Column('conducted_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('webinar_schedules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('connection_link', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('thumbnail_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('speaker_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('is_published', sa.Boolean(), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(), nullable=False),
    sa.Column('duration_minutes', sa.Integer(), nullable=False),
    sa.Column('reminder_1h_sent', sa.Boolean(), nullable=False),
    sa.Column('reminder_15m_sent', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('chat_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('agent_slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('schedule_id', sa.Integer(), nullable=True),
    sa.Column('library_id', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('last_read_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('last_message_at', sa.DateTime(), nullable=True),
    sa.Column('summarized_at', sa.DateTime(), nullable=True),
    sa.Column('last_proactivity_check_at', sa.DateTime(), nullable=True),
    sa.Column('user_agent_profile', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.ForeignKeyConstraint(['agent_slug'], ['agents.slug'], ),
    sa.ForeignKeyConstraint(['library_id'], ['webinar_libraries.id'], ),
    sa.ForeignKeyConstraint(['schedule_id'], ['webinar_schedules.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_sessions_agent_slug'), 'chat_sessions', ['agent_slug'], unique=False)
    op.create_index(op.f('ix_chat_sessions_library_id'), 'chat_sessions', ['library_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_schedule_id'), 'chat_sessions', ['schedule_id'], unique=False)
    op.create_index(op.f('ix_chat_sessions_user_id'), 'chat_sessions', ['user_id'], unique=False)
    op.create_table('magic_link_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('is_used', sa.Boolean(), nullable=False),
    sa.Column('is_revoked', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_magic_link_tokens_token'), 'magic_link_tokens', ['token'], unique=True)
    op.create_index(op.f('ix_magic_link_tokens_user_id'), 'magic_link_tokens', ['user_id'], unique=False)
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('code', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('ip_address', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('is_used', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)
    op.create_table('pending_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('agent_slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('topic_context', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('sent_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['agent_slug'], ['agents.slug'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_actions_agent_slug'), 'pending_actions', ['agent_slug'], unique=False)
    op.create_index(op.f('ix_pending_actions_user_id'), 'pending_actions', ['user_id'], unique=False)
    op.create_table('user_actions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('action', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_actions_user_id'), 'user_actions', ['user_id'], unique=False)
    op.create_table('user_memories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('narrative_summary', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_memories_user_id'), 'user_memories', ['user_id'], unique=True)
    op.create_table('webinar_signups',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('schedule_id', sa.Integer(), nullable=False),
    sa.Column('reminder_1h_sent', sa.Boolean(), nullable=False),
    sa.Column('reminder_start_sent', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['schedule_id'], ['webinar_schedules.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webinar_signups_schedule_id'), 'webinar_signups', ['schedule_id'], unique=False)
    op.create_index(op.f('ix_webinar_signups_user_id'), 'webinar_signups', ['user_id'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='messagerole'), nullable=False),
    sa.Column('content', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('message_metadata', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'], unique=False)
    
    # === SEEDING DATA ===
    seed_agents(op)
    seed_proactivity(op)
    
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_messages_session_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_webinar_signups_user_id'), table_name='webinar_signups')
    op.drop_index(op.f('ix_webinar_signups_schedule_id'), table_name='webinar_signups')
    op.drop_table('webinar_signups')
    op.drop_index(op.f('ix_user_memories_user_id'), table_name='user_memories')
    op.drop_table('user_memories')
    op.drop_index(op.f('ix_user_actions_user_id'), table_name='user_actions')
    op.drop_table('user_actions')
    op.drop_index(op.f('ix_pending_actions_user_id'), table_name='pending_actions')
    op.drop_index(op.f('ix_pending_actions_agent_slug'), table_name='pending_actions')
    op.drop_table('pending_actions')
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    op.drop_index(op.f('ix_magic_link_tokens_user_id'), table_name='magic_link_tokens')
    op.drop_index(op.f('ix_magic_link_tokens_token'), table_name='magic_link_tokens')
    op.drop_table('magic_link_tokens')
    op.drop_index(op.f('ix_chat_sessions_user_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_schedule_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_library_id'), table_name='chat_sessions')
    op.drop_index(op.f('ix_chat_sessions_agent_slug'), table_name='chat_sessions')
    op.drop_table('chat_sessions')
    op.drop_table('webinar_schedules')
    op.drop_table('webinar_libraries')
    op.drop_index(op.f('ix_users_tg_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_system_configs_key'), table_name='system_configs')
    op.drop_table('system_configs')
    op.drop_table('proactivity_settings')
    op.drop_index(op.f('ix_llm_audit_user_id'), table_name='llm_audit')
    op.drop_index(op.f('ix_llm_audit_created_at'), table_name='llm_audit')
    op.drop_index(op.f('ix_llm_audit_agent_slug'), table_name='llm_audit')
    op.drop_table('llm_audit')
    op.drop_table('chat_settings')
    op.drop_index(op.f('ix_agents_slug'), table_name='agents')
    op.drop_table('agents')
    # ### end Alembic commands ###
