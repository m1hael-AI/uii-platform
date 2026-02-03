"""
Сервис для работы с пользователями (аватарки, профиль).
"""
import os
import httpx
from io import BytesIO
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import User
from services.storage_service import upload_file
from config import settings

# Fallback path for local storage if S3 fails or is disabled
LOCAL_AVATAR_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/public/avatars'))

async def save_avatar_file(file_data: bytes, user_id: int, tg_id: int = 0) -> str:
    """
    Сохраняет файл аватарки (в S3 или локально) и возвращает публичный URL.
    """
    file_name = f"user_{user_id}_{tg_id}.jpg"
    file_obj = BytesIO(file_data)
    
    # 1. Пробуем загрузить в S3
    s3_url = await upload_file(
        file_data=file_obj,
        file_name=file_name,
        content_type="image/jpeg",
        folder="avatars/users"
    )
    
    if s3_url:
        return s3_url
    
    # 2. Если S3 не вернул URL (ошибка или не настроен) -> сохраняем локально
    # Это важно для dev-среды и fallback'а
    os.makedirs(LOCAL_AVATAR_DIR, exist_ok=True)
    local_path = os.path.join(LOCAL_AVATAR_DIR, file_name)
    
    with open(local_path, "wb") as f:
        f.write(file_data)
        
    # Возвращаем путь относительно корня сайта (для Next.js)
    return f"/avatars/{file_name}"


async def sync_user_avatar_from_telegram(user: User, session: AsyncSession) -> str:
    """
    Скачивает аватарку пользователя из Telegram и обновляет профиль.
    Возвращает URL аватарки или None.
    """
    if not user.tg_id:
        return None
        
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ BOT_TOKEN not found inside user_service")
        return None

    async with httpx.AsyncClient() as client:
        try:
            # 1. Получаем file_id
            url_photos = f"https://api.telegram.org/bot{bot_token}/getUserProfilePhotos"
            resp = await client.get(url_photos, params={"user_id": user.tg_id, "limit": 1})
            data = resp.json()
            
            if not data.get("ok") or data["result"]["total_count"] == 0:
                return None
                
            # Берем самое большое фото
            best_photo = data["result"]["photos"][0][-1]
            file_id = best_photo["file_id"]
            
            # 2. Получаем пусть к файлу
            url_file = f"https://api.telegram.org/bot{bot_token}/getFile"
            resp_file = await client.get(url_file, params={"file_id": file_id})
            file_path = resp_file.json()["result"]["file_path"]
            
            # 3. Скачиваем файл
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            resp_img = await client.get(download_url)
            
            if resp_img.status_code == 200:
                # 4. Сохраняем
                avatar_url = await save_avatar_file(resp_img.content, user.id, user.tg_id)
                
                # 5. Обновляем БД
                user.tg_photo_url = avatar_url
                session.add(user)
                await session.commit()
                await session.refresh(user)
                
                return avatar_url
                
        except Exception as e:
            print(f"❌ Error syncing avatar for user {user.id}: {e}")
            return None
            
    return None

async def upload_manual_avatar(user: User, file: UploadFile, session: AsyncSession) -> str:
    """
    Обработка ручной загрузки аватарки пользователем.
    """
    # Читаем файл
    content = await file.read()
    
    # Валидация размера (5MB limit for avatars)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    
    # Сохраняем (tg_id может быть 0 если нет привязки, используем просто 0 для имени файла)
    tg_id = user.tg_id or 0
    avatar_url = await save_avatar_file(content, user.id, tg_id)
    
    # Обновляем БД
    user.tg_photo_url = avatar_url
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return avatar_url
