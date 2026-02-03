import sys
from loguru import logger
from config import settings
import os

# Создаем папку для логов, если её нет
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger():
    """
    Настройка глобального логгера Loguru.
    - JSON формат для файлов
    - Ротация каждый день
    - Разделение уровней (INFO, ERROR)
    """
    # Удаляем стандартный обработчик, чтобы не дублировать
    logger.remove()

    # 1. Логи в консоль (для разработки удобнее цветной текст, а не JSON)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO" if not settings.debug else "DEBUG",
        colorize=True
    )

    # 2. Логи в файл (JSON, все уровни, ротация ежедневно)
    # Используем serialize=True для сохранения в JSON
    logger.add(
        os.path.join(LOG_DIR, "app_{time:YYYY-MM-DD}.json"),
        rotation="00:00",  # Новый файл каждый день в полночь
        retention="14 days",  # Хранить 14 дней
        compression="zip",  # Сжимать старые логи
        serialize=True,     # Писать в формате JSON
        level="INFO",
        encoding="utf-8"
    )

    # 3. Отдельный файл только для ошибок (чтобы быстро находить проблемы)
    logger.add(
        os.path.join(LOG_DIR, "errors.log"),
        rotation="10 MB",
        retention="30 days",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        encoding="utf-8" # Для ошибок JSON может быть избыточен, лучше читаемый текст, но можно и JSON
    )

    return logger

# Инициализируем при импорте, но функцию setup_logger можно вызвать повторно для реконфигурации
logger = setup_logger()
