from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import uvicorn
import os

app = FastAPI()

# إعدادات السماح بالاتصال من أي مكان (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# تحديث المكتبة تلقائياً عند تشغيل السيرفر
@app.on_event("startup")
async def startup_event():
    print("Updating yt-dlp...")
    os.system("pip install --upgrade yt-dlp")

@app.get("/")
def home():
    return {"message": "Qais Al-Jazi Server is Running Live!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/info")
def get_video_info(request: VideoRequest):
    try:
        # إعدادات التحميل مع الكوكيز (الحل السحري)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt',  # <--- هذا السطر هو الذي سيقرأ الملف السري من Render
            'format': 'best',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج المعلومات بدون تحميل الفيديو فعلياً
            info = ydl.extract_info(request.url, download=False)
            
            # تنظيف وتجهيز الصيغ (Formats)
            formats_list = []
            for f in info.get('formats', []):
                # نختار فقط ملفات MP4 التي تحتوي على فيديو وصوت معاً، أو جودة عالية
                if f.get('ext') == 'mp4' and f.get('acodec') != 'none':
                    formats_list.append({
                        'format_id': f['format_id'],
                        'quality': f.get('format_note', 'Standard'),
                        'ext': f['ext'],
                        'url': f.get('url')
                    })
            
            # ترتيب الجودات من الأفضل للأسوأ
            formats_list.reverse()

            return {
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "formats": formats_list
            }

    except Exception as e:
        # طباعة الخطأ في السيرفر وإرجاعه للواجهة
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to fetch video: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
