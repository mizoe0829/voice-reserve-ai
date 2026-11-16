import pytest
import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.reservation import Reservation
from app.models.shop import Shop
from app.schemas.dialog import SlotState
from app.services.booking_service import BookingService
from app.services.gemini_agent import VoiceAgentService

Base.metadata.create_all(bind=engine)

def test_full_slot_alternative_proposal():
    """
    コーナーケース 1-1: 満枠時の別日・別時間提案テスト
    1. 2026-11-20 19:00 の席（40席）を満席にする
    2. ユーザーが「11月20日の19時に4名で予約したい」と発話
    3. システムが満席を検知し、is_slot_available=False と代替候補（同日20:30や翌日19:00等）を提示
    4. ユーザーが「じゃあ20時半で」と受諾し、スロットが20:30に更新されて空席として進行可能になる
    """
    db: Session = SessionLocal()
    shop = BookingService.get_or_create_shop(db)
    target_date = "2026-11-20"
    target_time = "19:00"

    # 1. 19:00の席を満席にする
    existing = db.query(Reservation).filter(
        Reservation.date == target_date,
        Reservation.time == target_time
    ).all()
    for r in existing:
        db.delete(r)
    db.commit()

    full_res = Reservation(
        booking_code="RSV-FULL99",
        date=target_date,
        time=target_time,
        guests=shop.total_seats,  # 40席全埋まり
        seat_type="table",
        customer_name="団体様",
        status="confirmed"
    )
    db.add(full_res)
    db.commit()

    # 2. 空席チェック & 代替枠探索関数の動作確認
    avail_check = BookingService.check_availability_and_find_alternatives(
        db=db,
        date=target_date,
        time=target_time,
        guests=4
    )
    assert avail_check["is_available"] is False
    assert len(avail_check["alternatives"]) > 0
    print(f"\n[Test] 満枠検知時の代替候補: {avail_check['alternatives']}")

    # 3. VoiceAgentService への発話テスト（満席時）
    agent = VoiceAgentService()
    checker = lambda d, t, g: BookingService.check_availability_and_find_alternatives(db, d, t, g)

    res1 = agent.process_utterance(
        message="11月20日の19時に4名で予約をお願いできますか？",
        current_slots=None,
        stage="hearing",
        availability_checker=checker
    )

    assert res1.is_slot_available is False
    assert res1.is_confirmed is False
    assert len(res1.alternative_slots) > 0
    print(f"[Test] AIの満席時お詫び・提案テキスト: {res1.reply_text}")

    # 4. ユーザーが代替案（例: 20:30）を受け入れた場合の切り返し
    res2 = agent.process_utterance(
        message="あ、満席なんですね。じゃあ同じ日の20時半でお願いします！",
        current_slots=res1.updated_slots,
        stage=res1.stage,
        availability_checker=checker
    )

    assert res2.updated_slots.time == "20:30"
    assert res2.is_slot_available is True
    print(f"[Test] 代替枠受諾後のAI応答: {res2.reply_text}")

    # クリーンアップ
    db.delete(full_res)
    db.commit()
    db.close()
