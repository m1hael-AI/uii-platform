import json
import os
from datetime import datetime, timezone
import sys

def check_dump():
    # File is in secrets/webinars_dump.json
    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets", "webinars_dump.json")
    
    if not os.path.exists(file_path):
        print(f"File {file_path} not found.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    now = datetime.now(timezone.utc).replace(tzinfo=None) # Naive UTC for comparison
    
    print(f"Current UTC Time: {now}")
    print(f"Total items in dump: {len(data)}")
    
    suspicious_count = 0
    upcoming_count = 0
    library_count = 0
    
    for item in data:
        title = item.get('title')
        scheduled_str = item.get('scheduled_at')
        video_url = item.get('video_url', "")
        
        if not scheduled_str:
            print(f"⚠️ item '{title}' has no date.")
            continue
            
        dt = datetime.fromisoformat(scheduled_str)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            
        is_upcoming = dt > now
        has_video = bool(video_url and video_url.strip())
        
        if is_upcoming:
            upcoming_count += 1
        else:
            library_count += 1
            # Check for "Past but No Video" - likely the lost webinars
            if not has_video:
                print(f"🔴 Found Suspicious Item (In Past but No Video):")
                print(f"   Title: {title}")
                print(f"   Date:  {dt}")
                print(f"   Video: '{video_url}'")
                print("-" * 30)
                suspicious_count += 1

    print(f"\nSummary:")
    print(f"Projected Schedule (Future): {upcoming_count}")
    print(f"Projected Library (Past): {library_count}")
    print(f"Suspicious (Past + No Video): {suspicious_count}")

if __name__ == "__main__":
    check_dump()
