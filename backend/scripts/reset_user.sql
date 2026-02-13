-- Script to clear chat history for a specific user (or all users if WHERE clause removed)
-- This allows testing the "Initial User State" without deleting Agents or Webinars.

-- OPTION 1: Clear for a specific user (replace 1 with your user_id)
-- DELETE FROM chat_messages 
-- WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id = 1);

-- DELETE FROM chat_sessions 
-- WHERE user_id = 1;


-- OPTION 2: Clear ALL chat history (for development)
TRUNCATE TABLE chat_messages CASCADE;
TRUNCATE TABLE chat_sessions CASCADE;

-- After running this, the next time the user loads the frontend:
-- 1. /chat/sessions will return empty.
-- 2. ensure_initial_sessions() will trigger.
-- 3. It will create new sessions for all active agents.
-- 4. It will insert greeting messages and mark them as UNREAD (last_read_at = 2000-01-01).
