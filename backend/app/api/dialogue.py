from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.dialog import DialogueRequest, DialogueResponse
from app.services.gemini_agent import VoiceAgentService
from app.services.booking_service import BookingService

router = APIRouter()
agent_service = VoiceAgentService()

@router.post("/dialogue", response_model=DialogueResponse)
def handle_dialogue(req: DialogueRequest, db: Session = Depends(get_db)):
    """
    音声対話エンドポイント:
    ユーザーの発話テキストを受け取り、Geminiでスロット抽出・返答生成を行い、
    リアルタイム予約カード情報と返答音声を返す。
    """
    resp = agent_service.process_utterance(
        message=req.message,
        current_slots=req.current_slots,
        stage=req.stage,
        availability_checker=lambda d, t, g: BookingService.check_availability_and_find_alternatives(db, d, t, g)
    )

    # 確定または追加ヒアリング完了時のDB登録
    if resp.is_confirmed:
        reservation = BookingService.save_or_update_reservation(
            db=db,
            slots=resp.updated_slots,
            booking_code=req.session_id,
            status=resp.stage
        )
        resp.booking_code = reservation.booking_code

    return resp
