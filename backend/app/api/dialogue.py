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
        availability_checker=lambda d, t, g, s="table": (
            BookingService.check_seat_type_availability(db, d, t, g, s) if s == "private"
            else BookingService.check_availability_and_find_alternatives(db, d, t, g)
        )
    )

    # 既存予約の変更またはキャンセル時のDB反映
    if resp.action == "modify":
        existing_res = None
        if req.session_id:
            existing_res = BookingService.get_reservation_by_code(db, req.session_id)
        if not existing_res and resp.updated_slots.customer_name:
            existing_res = BookingService.find_reservation_by_name(db, resp.updated_slots.customer_name)
        if existing_res:
            if resp.updated_slots.guests:
                existing_res.guests = resp.updated_slots.guests
            if resp.updated_slots.time:
                existing_res.time = resp.updated_slots.time
            db.commit()
            db.refresh(existing_res)
            resp.booking_code = existing_res.booking_code
    elif resp.action == "cancel":
        existing_res = None
        if req.session_id:
            existing_res = BookingService.get_reservation_by_code(db, req.session_id)
        if not existing_res and resp.updated_slots.customer_name:
            existing_res = BookingService.find_reservation_by_name(db, resp.updated_slots.customer_name)
        if existing_res:
            BookingService.cancel_reservation(db, existing_res.id)
            resp.booking_code = existing_res.booking_code
    elif resp.is_confirmed:
        reservation = BookingService.save_or_update_reservation(
            db=db,
            slots=resp.updated_slots,
            booking_code=req.session_id,
            status=resp.stage
        )
        resp.booking_code = reservation.booking_code

    return resp
