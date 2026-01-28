import os
import sys
import subprocess
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# --- Configuration ---
# Allow all origins for simplicity
ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoURL(BaseModel):
    url: str

# --- Startup Tasks ---
@app.on_event("startup")
async def startup_event():
    """Auto-update yt-dlp on startup."""
    print("Checking for yt-dlp updates...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"])
        print("yt-dlp updated successfully.")
    except Exception as e:
        print(f"Failed to update yt-dlp: {e}")

# --- Endpoints ---

@app.get("/health")
async def health_check():
    """Keep-alive endpoint."""
    return {"status": "ok", "message": "Service is running"}

@app.post("/api/info")
async def get_video_info(video: VideoURL):
    """
    Extract video metadata using yt-dlp.
    Returns title, thumbnail, and simplified formats.
    """
    url = video.url
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            seen_formats = set()

            for f in info.get('formats', []):
                f_id = f.get('format_id')
                ext = f.get('ext')
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                height = f.get('height')

                label = ""
                type_ = "video"
                
                if vcodec == 'none' and acodec != 'none':
                    type_ = "audio"
                    label = f"Audio ({ext}) - {int(f.get('filesize', 0)/1024/1024) if f.get('filesize') else '?'}MB"
                elif vcodec != 'none':
                     if height:
                         label = f"{height}p ({ext})"
                     else:
                         continue
                else:
                    continue

                key = f"{type_}_{height or 'audio'}"
                if key not in seen_formats:
                     formats.append({
                        "format_id": f_id,
                        "label": label,
                        "ext": ext,
                        "type": type_,
                    })
                     seen_formats.add(key)
            
            formats.sort(key=lambda x: x['label'], reverse=True)

            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats
            }

    except Exception as e:
        print(f"Error extracting info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stream")
async def stream_video(url: str, format_id: str):
    ydl_opts = {
        'format': format_id,
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url')
            if not download_url:
                raise HTTPException(status_code=404, detail="Could not resolve download URL")
            
            return RedirectResponse(url=download_url)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
