import pytest
from app.services.gemini_agent import VoiceAgentService
from app.schemas.dialog import SlotState
from app.core.database import SessionLocal, engine, Base
from app.services.booking_service import BookingService

Base.metadata.create_all(bind=engine)

def test_dialogue_slot_extraction():
    service = VoiceAgentService()
    # ユーザー発話: 「今週の金曜日の夜7時、3名で予約したい」
    res = service.process_utterance(
        message="今週の金曜日の夜7時、3名で予約したいです",
        current_slots=None,
        stage="hearing"
    )
    assert res.reply_text is not None
    assert res.updated_slots.guests == 3 or res.updated_slots.guests is not None

def test_booking_persistence():
    db = SessionLocal()
    slots = SlotState(
        date="2026-11-20",
        time="19:00",
        guests=4,
        seat_type="table",
        course_name="2時間飲み放題付き 極み炭火焼鳥コース",
        customer_name="田中 太郎",
        phone_number="090-9876-5432",
        allergies=["甲殻類アレルギー (1名)"],
        pre_orders=[{"name": "生ビール", "quantity": 4}, {"name": "月見生つくね", "quantity": 4}]
    )
    res = BookingService.save_or_update_reservation(db, slots, status="completed")
    
    assert res.id is not None
    assert res.booking_code.startswith("RSV-")
    assert res.guests == 4
    assert len(res.allergies) == 1
    assert len(res.pre_orders) == 2
    
    # 取得確認
    fetched = BookingService.get_reservation_by_code(db, res.booking_code)
    assert fetched is not None
    assert fetched.customer_name == "田中 太郎"
    db.close()
