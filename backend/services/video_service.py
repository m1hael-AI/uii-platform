import re
import httpx
import json
import io
from typing import Optional, Dict
import hashlib
from PIL import Image
from services.storage_service import upload_file, file_exists
from config import settings

# User-Agent to avoid bot blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}

async def fetch_vk_thumbnail(video_url: str) -> Optional[str]:
    """
    Scrapes VK/VKVideo page to find the thumbnail URL.
    Handles Embed (video_ext.php) and Direct links.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(video_url, headers=HEADERS)
            if resp.status_code != 200:
                return None
            
            # Decode using windows-1251 as most VK pages use it
            try:
                html = resp.content.decode("windows-1251")
            except:
                html = resp.content.decode("utf-8", errors="replace")
            
            # Pattern 1: Search for "image" array in config (most reliable for recent VK)
            image_match = re.search(r'"image":\s*(\[.*?\])', html)
            if image_match:
                images_json = image_match.group(1).replace(r'\/', '/')
                try:
                    images = json.loads(images_json)
                    if images:
                        # Prefer high-res (vid_w / vid_u / vid_x)
                        for tag in ['vid_w', 'vid_u', 'vid_x']:
                             found = next((img.get('url') for img in images if tag in img.get('url', '')), None)
                             if found: return found
                        return images[-1].get('url')
                except:
                    pass
            
            # Pattern 2: Global metadata (og:image)
            og_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
            if og_match:
                return og_match.group(1).replace(r'\/', '/')
            
            # Pattern 3: Global search for i.mycdn.me previews
            matches = re.findall(r'https:[\\/]+i\.mycdn\.me[\\/]+getVideoPreview\?[^"\'\s>]+', html)
            if matches:
                # Use the first match, clean up slashes
                return matches[0].replace('\\/', '/')
                
    except Exception as e:
        print(f"Error fetching VK thumbnail: {e}")
    return None

async def fetch_youtube_thumbnail(video_url: str) -> Optional[str]:
    """Extracts thumbnail for YouTube videos."""
    # Simple regex for YT ID
    yt_id_match = re.search(r'(?:v=|\/embed\/|\/watch\?v=|\/v\/|youtu\.be\/|\/vi\/|watch\?.*v=)([^#\&\?\/]+)', video_url)
    if yt_id_match:
        yt_id = yt_id_match.group(1)
        # Use hqdefault as it's almost always present and decent quality
        return f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg"
    return None

async def process_video_thumbnail(video_url: str) -> Optional[str]:
    """
    Detects platform, fetches external thumbnail, optimize it (WebP + Resize),
    and uploads to S3 storage if not exists. Returns public S3 URL.
    """
    ext_thumb_url = None
    
    if "vk.com" in video_url or "vkvideo.ru" in video_url:
        ext_thumb_url = await fetch_vk_thumbnail(video_url)
    elif "youtube.com" in video_url or "youtu.be" in video_url:
        ext_thumb_url = await fetch_youtube_thumbnail(video_url)
        
    if not ext_thumb_url:
        return None
        
    try:
        # 1. Generate unique filename based on hash ONLY (no timestamp)
        # This ensures dedup: same video URL -> same filename
        file_hash = hashlib.md5(video_url.encode()).hexdigest()
        file_name = f"thumb_{file_hash}.webp"
        folder = "thumbnails"
        file_key = f"{folder}/{file_name}"
        
        # 2. Check if file already exists in S3
        if await file_exists(file_key):
             # Return existing URL without downloading/uploading
             return f"{settings.s3_endpoint_url}/{settings.s3_bucket_name}/{file_key}"

        # 3. Download, Optimize, Upload
        async with httpx.AsyncClient(timeout=10.0) as client:
            img_resp = await client.get(ext_thumb_url, headers=HEADERS)
            if img_resp.status_code == 200:
                
                # Optimize Image using Pillow
                img = Image.open(io.BytesIO(img_resp.content))
                
                # Resize if too big (max width 800px)
                max_width = 800
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int(float(img.height) * float(ratio))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Save to in-memory buffer as WebP
                output_buffer = io.BytesIO()
                img.save(output_buffer, format="WEBP", quality=80, optimize=True)
                output_buffer.seek(0)
                
                # Upload optimized file
                s3_url = await upload_file(
                    file_data=output_buffer,
                    file_name=file_name,
                    content_type="image/webp",
                    folder=folder
                )
                return s3_url
                
    except Exception as e:
        print(f"Error processing/uploading thumbnail: {e}")
        
    return None
