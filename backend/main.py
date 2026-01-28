from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import uvicorn
import requests
import os

app = FastAPI()

# إعدادات CORS (السماح للواجهة بالاتصال)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# التحديث التلقائي للمكتبة عند التشغيل
@app.on_event("startup")
async def startup_event():
    os.system("pip install --upgrade yt-dlp")

@app.get("/")
def home():
    return {"message": "Qais Al-Jazi Server is Live & Ready!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

# 1. دالة جلب المعلومات (لزر التحليل)
@app.post("/api/info")
def get_video_info(request: VideoRequest):
    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt', # الملف السري
            'format': 'best',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
            
            formats_list = []
            for f in info.get('formats', []):
                # نختار صيغ MP4 التي تحتوي على صوت وصورة
                if f.get('ext') == 'mp4' and f.get('acodec') != 'none':
                    # نستخدم رابط السيرفر الخاص بنا للتحميل بدلاً من رابط جوجل المباشر
                    # هذا يحل مشكلة الحظر (403 Forbidden)
                    server_url = os.getenv("RENDER_EXTERNAL_URL", "http://localhost:8000")
                    # نقوم بترميز الرابط الأصلي لتمريره
                    proxy_link = f"{server_url}/api/stream?url={request.url}&format_id={f['format_id']}"
                    
                    formats_list.append({
                        'quality': f.get('format_note', 'HD'),
                        'ext': f['ext'],
                        'url': proxy_link # الرابط الجديد الموجه عبر سيرفرنا
                    })
            
            formats_list.reverse()
            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "formats": formats_list
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 2. دالة التحميل الجديدة (هذه هي الناقصة عندك!)
@app.get("/api/stream")
def stream_video(url: str = Query(...), format_id: str = Query(None)):
    try:
        ydl_opts = {
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'format': format_id if format_id else 'best',
        }
        
        # نحصل على الرابط المباشر الطازج من يوتيوب
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            direct_url = info.get('url') # رابط جوجل الحقيقي
            title = info.get('title', 'video')

        # نقوم بعمل "بث" (Stream) من جوجل للمستخدم عبر سيرفرنا
        def iterfile():
            with requests.get(direct_url, stream=True) as r:
                for chunk in r.iter_content(chunk_size=1024*1024): # 1MB chunks
                    yield chunk

        # إعداد الترويسة ليبدأ التحميل كملف
        headers = {
            "Content-Disposition": f'attachment; filename="{title}.mp4"'
        }
        return StreamingResponse(iterfile(), media_type="video/mp4", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
