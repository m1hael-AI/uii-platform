# Project Handover & Architecture Guide - Feb 2026

## 🧠 Memory & Proactivity Architecture

### 1. The "Snowball" Compression Strategy
**Logic:** instead of losing old context, we compress it into a snowball.
- **`{previous_summary}`**: The existing snowball (already compressed history).
- **`{text_to_compress}`**: Freshly archived messages that are being added to the snowball.
- **Process**: LLM reads `previous_summary` + `text_to_compress` -> Generates `new_summary`.
- **Code:** `backend/services/context_manager.py` -> `compress_context_task`.

> **⚠️ Gotcha:** If `{text_to_compress}` is empty or missing from the prompt, the LLM will hallucinate or return an empty summary, wiping out the user's history.

### 2. Proactivity Trigger
**Logic:** The agent doesn't just reply; it *decides* if it should reply when the user is silent.
- **Trigger**: Runs periodically (Cron/Celery).
- **Input**: User Profile + Recent History.
- **Output**: `{"should_respond": boolean, "suggested_message": string}`.
- **Code:** `backend/services/summarizer.py` -> `check_proactivity_trigger`.

### 3. LLM Audit Logs
**Logic:** Every request to OpenAI is logged for transparency and cost tracking.
- **Storage**: `LLMAudit` table in SQL.
- **Viewer**: Admin Panel (`/admin/llm-audit`).
- **Implementation**: `backend/services/audit_service.py` (fire-and-forget logic).

## 🛠️ Critical Configurations

### 1. `backend/models.py`
Contains the **default prompts**.
- `compression_prompt`: MUST contain `{previous_summary}` and `{text_to_compress}`.
- `proactivity_trigger_prompt`: MUST return JSON.

### 2. Frontend Tooltips
- Located in `frontend/src/app/system-control/proactivity/page.tsx`.
- Used to hint admins about available variables (`{user_profile}`, etc.).

## 📦 Dependency Management
- **Backend**: `requirements.txt`. Key libs: `openai`, `sqlalchemy`, `fastapi`, `apscheduler`.
- **Frontend**: `package.json` + `package-lock.json`.
    - `package-lock.json` **MUST** be committed. It ensures that everyone (devs + CI/CD) installs the *exact same* versions of dependencies. Without it, builds can break randomly.

## 🚀 Deployment Checklist
1. **Database**: Run migrations (`alembic upgrade head`).
2. **Env Vars**: Ensure `OPENAI_API_KEY`, `DATABASE_URL` are set.
3. **Cron**: Ensure the scheduler (APScheduler) is running for proactive tasks.

## 🐛 Known "Gotchas" (Self-Notes)
1. **Syntax Errors in Prompts**: Python f-strings can break if you have stray `{` or `}`. Always double-check JSON strings in prompts.
2. **Triple Quotes**: When defining multi-line prompts in Python, ensure triple quotes `"""` are closed correctly, otherwise fields get swallowed.
3. **Context Overflow**: If the context is full, the system relies on the `compress_context_task`. If this task fails, the agent will loop erroring on "Context Overflow".
