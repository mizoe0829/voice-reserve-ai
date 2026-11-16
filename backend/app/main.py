from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api import dialogue, reservations, shop

# テーブル自動生成
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VoiceReserve AI",
    description="問い合わせ不要！電話感覚の音声対話型予約ボット ＆ リアルタイム予約同期システム",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dialogue.router, prefix="/api", tags=["Dialogue"])
app.include_router(reservations.router, prefix="/api", tags=["Reservations"])
app.include_router(shop.router, prefix="/api", tags=["Shop"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "VoiceReserve AI"}
