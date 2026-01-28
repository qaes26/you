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
    # 1. تحديث مكتبة yt-dlp لضمان عملها مع تحديثات يوتيوب
    os.system("pip install --upgrade yt-dlp")
    
    # 2. حل مشكلة الملفات للقراءة فقط (Read-only) في Render
    # نقوم بنسخ ملف الكوكيز من المجلد السري إلى مجلد التطبيق الحالي
    secret_path = "/etc/secrets/cookies.txt"
    local_path = "cookies.txt"
    
    if os.path.exists(secret_path):
        print(f"جاري نسخ الكوكيز من {secret_path} إلى {local_path}...")
        try:
            shutil.copy(secret_path, local_path)
            print("تم نسخ الكوكيز بنجاح!")
        except Exception as e:
            print(f"خطأ أثناء نسخ الكوكيز: {e}")
    else:
        print("تحذير: لم يتم العثور على ملف cookies.txt في المجلد السري.")

def get_ydl_opts(format_id=None):
    """إعدادات yt-dlp الموحدة"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        # استخدام ملف الكوكيز المحلي الذي تم نسخه
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'cache_dir': False,
    }
    
    if format_id:
        # إذا لم تتوفر الجودة المطلوبة، يختار أفضل جودة متاحة تلقائياً لتجنب Format Error
        opts['format'] = f"{format_id}/bestvideo+bestaudio/best"
    else:
        opts['format'] = 'best'
        
    return opts

@app.get("/")
def home():
    return {"message": "سيرفر قيس الجازي يعمل بنجاح!"}

@app.post("/api/info")
def get_video_info(request: VideoRequest):
    try:
        ydl_opts = get_ydl_opts()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            formats_list = []
            for f in info.get('formats', []):
                # تصفية الصيغ المتاحة (يفضل mp4)
                if f.get('ext') == 'mp4' and f.get('acodec') != 'none':
                    server_url = os.getenv("RENDER_EXTERNAL_URL", "https://you-lsq7.onrender.com")
                    # إنشاء رابط التحميل عبر سيرفرنا (Proxy)
                    proxy_link = f"{server_url}/api/stream?url={request.url}&format_id={f['format_id']}"
                    
                    formats_list.append({
                        'format_id': f['format_id'],
                        'quality': f.get('format_note') or f.get('resolution') or 'Standard',
                        'ext': f['ext'],
                        'url': proxy_link
                    })
            
            # عرض أحدث الجودات أولاً
            formats_list.reverse()
            
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats_list
            }
    except Exception as e:
        print(f"خطأ في جلب المعلومات: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/stream")
def stream_video(url: str = Query(...), format_id: str = Query(None)):
    try:
        ydl_opts = get_ydl_opts(format_id)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url')
            title = info.get('title', 'video')

        # دالة لإرسال الفيديو على أجزاء لتجنب استهلاك ذاكرة السيرفر
        def iterfile():
            with requests.get(direct_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    yield chunk

        headers = {
            "Content-Disposition": f'attachment; filename="{title}.mp4"'
        }
        return StreamingResponse(iterfile(), media_type="video/mp4", headers=headers)

    except Exception as e:
        print(f"خطأ أثناء التحميل: {e}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
