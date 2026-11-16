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


def test_self_correction_speech():
    """
    コーナーケース 2-1: 発話内での自己訂正（取り消し・言い直し）
    - 「3名で…いや、子供も1人増えて4名でお願いします」
    - 「11月21日の18時で…あ、違った11月22日の19時で！」
    """
    agent = VoiceAgentService()

    # 1. 人数の自己訂正
    res1 = agent.process_utterance(
        message="3名で…あ、いや、子供が1人増えたので4名でお願いします！",
        current_slots=None,
        stage="hearing"
    )
    assert res1.updated_slots.guests == 4
    print(f"\n[Test 2-1 人数訂正] 抽出人数: {res1.updated_slots.guests}名 (期待値: 4名)")

    # 2. 日時・時間の自己訂正
    res2 = agent.process_utterance(
        message="11月21日の18時で…あ、違った、11月22日の19時でお願いできますか？",
        current_slots=res1.updated_slots,
        stage="hearing"
    )
    assert res2.updated_slots.date == f"{datetime.datetime.now().year}-11-22"
    assert res2.updated_slots.time == "19:00"
    print(f"[Test 2-1 日時訂正] 抽出日時: {res2.updated_slots.date} {res2.updated_slots.time} (期待値: 11-22 19:00)")


def test_faq_interruption_and_resumption():
    """
    コーナーケース 2-2: FAQ質問の割り込みと本筋への自動復帰
    - 名前ヒアリングの段階で「あ、その前に車で行くんですけど、駐車場ってありますか？」と割り込み
    - 期待値:
      1. customer_name に質問文が入らない
      2. 返答に「提携コインパーキング」「2台」等の回答が含まれる
      3. 返答の末尾で「お名前とお電話番号」のヒアリングへ自動復帰している
    """
    agent = VoiceAgentService()
    current_slots = SlotState(
        date="2026-11-22",
        time="19:00",
        guests=4,
        seat_type="table",
        customer_name=None,
        phone_number=None
    )

    res = agent.process_utterance(
        message="あ、その前に車で行く予定なんですけど、お店に駐車場ってありますか？",
        current_slots=current_slots,
        stage="hearing"
    )

    # 1. スロット汚染がないこと
    assert res.updated_slots.customer_name is None
    assert res.updated_slots.date == "2026-11-22"
    assert res.updated_slots.time == "19:00"

    # 2. FAQへの回答と予約本筋への復帰が両立していること
    reply = res.reply_text
    assert "駐車場" in reply or "パーキング" in reply
    assert "名前" in reply or "電話番号" in reply or "予約" in reply
    print(f"\n[Test 2-2 FAQ割り込み応答]:\n{reply}")


def test_children_and_stroller_handling():
    """
    飲食コーナーケース A: 子連れ・ベビーカー・乳幼児の席調整
    - 発話: 「大人3人と、子供が1人いて、ベビーカーも1台持っていきたいんですけど予約できますか？」
    - 期待値:
      1. 人数: 合計4名（大人3＋子供1）
      2. 席種: 危険なカウンターを避け「テーブル席（table）」
      3. 特記事項（special_requests）: 「大人3名、子供1名、ベビーカー」等の情報が記録される
      4. 返答: 歓迎の言葉と「広めのテーブル席」「子供用食器」等の配慮が案内される
    """
    agent = VoiceAgentService()

    res = agent.process_utterance(
        message="大人3人と、幼稚園の子供が1人いて、ベビーカーも1台持っていきたいんですけど予約できますか？",
        current_slots=None,
        stage="hearing"
    )

    # 1. 人数
    assert res.updated_slots.guests == 4
    # 2. 席種
    assert res.updated_slots.seat_type in ["table", "private"]
    # 3. 特記事項
    assert res.updated_slots.special_requests is not None
    # 4. 返答の温かみと配慮
    reply = res.reply_text
    assert "テーブル" in reply or "お席" in reply or "お子様" in reply
    print(f"\n[Test A 子連れ・ベビーカー対応]:\nスロット: guests={res.updated_slots.guests}, seat={res.updated_slots.seat_type}, special={res.updated_slots.special_requests}\nAI応答: {reply}")
