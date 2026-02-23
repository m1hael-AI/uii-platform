import io
import re
import uuid
import httpx
from datetime import datetime
from typing import List, Optional
from loguru import logger
from PIL import Image

try:
    from goose3 import Goose
    from goose3.configuration import Configuration
except ImportError:
    Goose = None

from services.storage_service import upload_file

# ---- Fallback Regex filter ----
_BAD_IMG = re.compile(
    r"(logo|icon|favicon|avatar|pixel|spacer|1x1|badge|banner_small|placeholder|default[-_]img|\.gif)",
    re.IGNORECASE,
)
_OG_RE = [
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\'>\s]+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\'>\s]+)["\'][^>]+property=["\']og:image["\']', re.IGNORECASE),
]
_TW_RE = [
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\'>\s]+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\'>\s]+)["\'][^>]+name=["\']twitter:image["\']', re.IGNORECASE),
]

# Настройка Goose (убираем лишние таймауты)
_goose_config = None
if Goose:
    _goose_config = Configuration()
    _goose_config.browser_user_agent = "Mozilla/5.0 (compatible; UII-NewsBot/1.0)"
    _goose_config.http_timeout = 5.0
    _goose_config.strict_clean = False # Менее строгое удаление DOM-элементов


async def _process_and_upload_image(image_bytes: bytes, original_url: str) -> Optional[str]:
    """
    Конвертирует скачанные байты картинки в WebP через Pillow
    и асинхронно отправляет в S3 бакет.
    """
    try:
        # Открываем изображение через Pillow
        img = Image.open(io.BytesIO(image_bytes))
        
        # Конвертируем в RGB если нужно (например, прозрачный PNG -> RGB WebP)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Уменьшаем, если картинка слишком огромная (опционально, например макс 1920x1080)
        max_size = (1920, 1080)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Сохраняем в память как WebP
        out_bytes = io.BytesIO()
        img.save(out_bytes, format="WEBP", quality=80, method=4)
        out_bytes.seek(0)
        
        # Генерируем уникальное имя файла
        file_name = f"news_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.webp"
        
        # Загружаем в S3 (через storage_service)
        s3_url = await upload_file(
            file_data=out_bytes,
            file_name=file_name,
            content_type="image/webp",
            folder="news_images"
        )
        return s3_url
    except Exception as e:
        logger.error(f"Error processing/uploading image from {original_url[:60]}: {e}")
        return None

def _extract_fallback_image(html: str) -> Optional[str]:
    """Fallback-метод регулярками, если goose не справился"""
    candidates = []
    for patterns in (_OG_RE, _TW_RE):
        for p in patterns:
            m = p.search(html)
            if m:
                candidates.append(m.group(1).strip())
                break
    for img_url in candidates:
        if img_url.startswith("http") and not _BAD_IMG.search(img_url):
            return img_url
    return None

async def _download_bytes(url: str, client: httpx.AsyncClient) -> Optional[bytes]:
    try:
        r = await client.get(url, timeout=6.0, follow_redirects=True)
        if r.status_code == 200:
            return r.content
    except Exception as e:
        logger.debug(f"Failed to download image bytes from {url[:60]}: {e}")
    return None

async def extract_and_upload_best_image(source_urls: List[str]) -> Optional[str]:
    """
    Пытается найти лучшую картинку по списку URL.
    Сначала goose3 -> если пусто -> fallback regex.
    Затем скачивает картинку, конвертирует в WebP и грузит в S3.
    """
    if not source_urls:
        return None
        
    headers = {"User-Agent": "Mozilla/5.0 (compatible; UII-NewsBot/1.0)"}
    
    async with httpx.AsyncClient(headers=headers) as client:
        for article_url in source_urls:
            # Пропускаем мошеннический/неподходящий контент (например видео)
            if "youtube.com" in article_url or "youtu.be" in article_url:
                continue
                
            image_url_candidate = None
            html_content = None
            
            # --- 1. Скачиваем HTML ---
            try:
                r = await client.get(article_url, timeout=7.0, follow_redirects=True)
                if r.status_code != 200:
                    continue
                html_content = r.text
            except Exception as e:
                logger.debug(f"Failed to fetch HTML from {article_url[:60]}: {e}")
                continue
                
            # --- 2. Пытаемся распарсить через Goose3 ---
            if Goose and html_content:
                try:
                    g = Goose(_goose_config)
                    article = g.extract(raw_html=html_content)
                    if article.top_image and article.top_image.src:
                        goose_url = article.top_image.src
                        # Доп проверка, что это не гифка и не логотип
                        if goose_url.startswith("http") and not _BAD_IMG.search(goose_url):
                            image_url_candidate = goose_url
                except Exception as e:
                    logger.debug(f"Goose failed for {article_url[:60]}: {e}")
            
            # --- 3. Если Goose не справился, используем Regex-fallback ---
            if not image_url_candidate and html_content:
                image_url_candidate = _extract_fallback_image(html_content)
                
            # --- 4. Если картинка найдена, скачиваем и грузим в S3 ---
            if image_url_candidate:
                image_bytes = await _download_bytes(image_url_candidate, client)
                if image_bytes:
                    s3_url = await _process_and_upload_image(image_bytes, image_url_candidate)
                    if s3_url:
                        logger.info(f"✅ Image extracted and uploaded to S3: {s3_url} (source: {article_url})")
                        return s3_url
                        
            # Если дошли сюда, значит ни goose, ни fallback не нашли рабочих картинок
            # или не смогли их скачать. Идем на следующую ссылку.
            
    return None
