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

# إعدادات CORS للسماح للواجهة بالاتصال بالسيرفر
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
    # 1. تحديث مكتبة yt-dlp لضمان مواكبة تحديثات يوتيوب
    os.system("pip install --upgrade yt-dlp")
    
    # 2. حل مشكلة الملفات للقراءة فقط (Read-only) في Render
    secret_path = "/etc/secrets/cookies.txt"
    local_path = "cookies.txt"
    
    if os.path.exists(secret_path):
        try:
            shutil.copy(secret_path, local_path)
            print("Successfully copied cookies to writable path.")
        except Exception as e:
            print(f"Error copying cookies: {e}")
    else:
        print("Warning: cookies.txt not found in /etc/secrets/")

def get_ydl_opts(format_id=None):
    """إعدادات yt-dlp مع التمويه والكوكيز"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'cache_dir': False,
        # سطر التمويه: يجعل الطلب يبدو كأنه من متصفح حقيقي لتجنب Bot Detection
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    if format_id:
        # يحاول طلب الجودة المختارة، وإذا لم يجدها يختار الأفضل تلقائياً
        opts['format'] = f"{format_id}/bestvideo+bestaudio/best"
    else:
        opts['format'] = 'best'
        
    return opts

@app.get("/")
def home():
    return {"message": "Server Qais Al-Jazi is Live!"}

@app.post("/api/info")
def get_video_info(request: VideoRequest):
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            formats_list = []
            for f in info.get('formats', []):
                # نختار فقط صيغ mp4 التي تدعم الفيديو والصوت معاً لسهولة التشغيل
                if f.get('ext') == 'mp4' and f.get('acodec') != 'none':
                    server_url = os.getenv("RENDER_EXTERNAL_URL", "https://you-lsq7.onrender.com")
                    proxy_link = f"{server_url}/api/stream?url={request.url}&format_id={f['format_id']}"
                    
                    formats_list.append({
                        'format_id': f['format_id'],
                        'quality': f.get('format_note') or f.get('resolution') or 'Standard',
                        'ext': f['ext'],
                        'url': proxy_link
                    })
            
            formats_list.reverse() # عرض الجودات الأعلى في البداية
            
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats_list
            }
    except Exception as e:
        print(f"Info Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream")
def stream_video(url: str = Query(...), format_id: str = Query(None)):
    try:
        ydl_opts = get_ydl_opts(format_id)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url')
            title = info.get('title', 'video')

        def iterfile():
            # سحب الفيديو من يوتيوب وتمريره للمستخدم مباشرة (Proxy) لتجاوز الحظر
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
