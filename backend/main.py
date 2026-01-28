from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import uvicorn
import requests
import os
import shutil

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.on_event("startup")
async def startup_event():
    # 1. تحديث المكتبة دائماً
    os.system("pip install --upgrade yt-dlp")
    
    # 2. نسخ الكوكيز من الخزنة السرية إلى مكان العمل
    # هذا يحل مشكلة Read-only ومشكلة المسارات
    secret_path = "/etc/secrets/cookies.txt"
    local_path = "cookies.txt"
    
    if os.path.exists(secret_path):
        print(f"Found secret cookies. Copying to {local_path}...")
        try:
            shutil.copy(secret_path, local_path)
            print("Cookies copied successfully!")
        except Exception as e:
            print(f"Error copying cookies: {e}")
    else:
        print("Warning: No cookies found in secrets! YouTube might block requests.")

@app.get("/")
def home():
    return {"message": "Qais Al-Jazi Server is Ready"}

# دالة إعدادات التحميل الموحدة
def get_ydl_opts():
    return {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        # نستخدم الملف المحلي اللي نسخناه
        'cookiefile': 'cookies.txt', 
        # تعطيل الكاش عشان ما يحاول يكتب على ملفات النظام
        'cache_dir': False, 
    }

@app.post("/api/info")
def get_video_info(request: VideoRequest):
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            formats_list = []
            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('acodec') != 'none':
                    server_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
                    proxy_link = f"{server_url}/api/stream?url={request.url}&format_id={f['format_id']}"
                    
                    formats_list.append({
                        'quality': f.get('format_note', 'HD'),
                        'ext': f['ext'],
                        'url': proxy_link
                    })
            
            formats_list.reverse()
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "formats": formats_list
            }
    except Exception as e:
        print(f"Info Error: {e}")
        # إذا الخطأ "Sign in" نرجع رسالة واضحة
        if "Sign in" in str(e):
             raise HTTPException(status_code=400, detail="Server Cookies Expired. Please update cookies.txt")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream")
def stream_video(url: str = Query(...), format_id: str = Query(None)):
    try:
        ydl_opts = get_ydl_opts()
        if format_id:
            ydl_opts['format'] = format_id
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url')
            title = info.get('title', 'video')

        def iterfile():
            with requests.get(direct_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    yield chunk

        headers = {
            "Content-Disposition": f'attachment; filename="{title}.mp4"'
        }
        return StreamingResponse(iterfile(), media_type="video/mp4", headers=headers)

    except Exception as e:
        print(f"Stream Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
