from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from loguru import logger

router = APIRouter(prefix="/logs", tags=["Logs"])

class LogEntry(BaseModel):
    level: str
    message: str
    meta: Optional[Dict[str, Any]] = None

@router.post("")
async def info_logs(entry: LogEntry):
    """
    Принимает логи с клиента (фронтенда) и пишет их в лог сервера.
    """
    # Форматируем сообщение для логов
    log_msg = f"[CLIENT] {entry.message}"
    if entry.meta:
        log_msg += f" | META: {entry.meta}"
    
    # Пишем в loguru с соответствующим уровнем
    level = entry.level.upper()
    if level == "INFO":
        logger.info(log_msg)
    elif level == "WARN" or level == "WARNING":
        logger.warning(log_msg)
    elif level == "ERROR":
        logger.error(log_msg)
    elif level == "DEBUG":
        logger.debug(log_msg)
    else:
        logger.info(f"[{level}] {log_msg}")

    return {"status": "ok"}
