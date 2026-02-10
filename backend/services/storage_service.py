"""
Сервис для работы с файловым хранилищем.
Использует aioboto3 для асинхронной работы с S3-совместимыми хранилищами.
Vendor-agnostic: Supabase Storage, MinIO, AWS S3, Beget S3.
"""

from typing import Optional, BinaryIO
import aioboto3
from botocore.config import Config
from config import settings


# Конфигурация для S3 клиента
s3_config = Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path'},
)

# Константы для валидации
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "application/pdf",  # Разрешим PDF для документов
}


def get_s3_session():
    """Создаёт сессию aioboto3 для работы с S3"""
    return aioboto3.Session()


async def upload_file(
    file_data: BinaryIO,
    file_name: str,
    content_type: str = "application/octet-stream",
    folder: str = "uploads",
) -> Optional[str]:
    """
    Загружает файл в S3-совместимое хранилище.
    
    Args:
        file_data: Бинарные данные файла
        file_name: Имя файла
        content_type: MIME тип файла
        folder: Папка в bucket
    
    Returns:
        URL загруженного файла или None при ошибке
    """
    if not settings.s3_endpoint_url:
        return None

    # === Валидация ===
    if content_type not in ALLOWED_CONTENT_TYPES:
        # Для простоты вернем None, но в идеале нужно поднимать исключение
        print(f"Validation Error: Unsupported content type {content_type}")
        return None

    # Проверка размера (seek в конец -> tell -> seek в начало)
    try:
        file_data.seek(0, 2)
        size = file_data.tell()
        file_data.seek(0)
        
        if size > MAX_FILE_SIZE:
            print(f"Validation Error: File size {size} exceeds limit {MAX_FILE_SIZE}")
            return None
    except Exception as e:
        print(f"Validation Warning: Could not check file size: {e}")
        # Не блокируем, если не смогли проверить размер (например, потоковая передача)

    key = f"{folder}/{file_name}"
    session = get_s3_session()
    
    async with session.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=s3_config,
    ) as s3:
        await s3.upload_fileobj(
            file_data,
            settings.s3_bucket_name,
            key,
            ExtraArgs={
                'ContentType': content_type,
            },
        )
        
        # Формируем публичный URL
        url = f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{key}"
        return url


async def download_file(key: str) -> Optional[bytes]:
    """
    Скачивает файл из S3-совместимого хранилища.
    
    Args:
        key: Путь к файлу в bucket
    
    Returns:
        Бинарные данные файла или None при ошибке
    """
    if not settings.s3_endpoint_url:
        return None
    
    session = get_s3_session()
    
    async with session.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=s3_config,
    ) as s3:
        response = await s3.get_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
        )
        data = await response['Body'].read()
        return data


async def delete_file(key: str) -> bool:
    """
    Удаляет файл из S3-совместимого хранилища.
    
    Args:
        key: Путь к файлу в bucket
    
    Returns:
        True если успешно, False при ошибке
    """
    if not settings.s3_endpoint_url:
        return False
    
    session = get_s3_session()
    
    async with session.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=s3_config,
    ) as s3:
        await s3.delete_object(
            Bucket=settings.s3_bucket_name,
            Key=key,
        )
        return True


async def generate_presigned_url(
    key: str,
    expires_in: int = 3600,
) -> Optional[str]:
    """
    Генерирует временный URL для доступа к файлу.
    
    Args:
        key: Путь к файлу в bucket
        expires_in: Время жизни URL в секундах
    
    Returns:
        Подписанный URL или None при ошибке
    """
    if not settings.s3_endpoint_url:
        return None
    
    session = get_s3_session()
    
    async with session.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=s3_config,
    ) as s3:
        url = await s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.s3_bucket_name,
                'Key': key,
            },
            ExpiresIn=expires_in,
        )
        return url


async def file_exists(key: str) -> bool:
    """
    Проверяет, существует ли файл в S3-совместимом хранилище.
    
    Args:
        key: Путь к файлу в bucket
    
    Returns:
        True если файл существует, False если нет или при ошибке
    """
    if not settings.s3_endpoint_url:
        return False
    
    session = get_s3_session()
    
    try:
        async with session.client(
            's3',
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=s3_config,
        ) as s3:
            await s3.head_object(
                Bucket=settings.s3_bucket_name,
                Key=key,
            )
            return True
    except Exception:
        # Если файл не найден или ошибка доступа -> считаем, что его нет
        return False
