import pytest
import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.reservation import Reservation
from app.models.shop import Shop, Industry
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
        message="大人3人と、2歳の子供が1人いて、ベビーカーも1台持っていきたいんですけど予約できますか？",
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


def test_peak_hours_two_hour_rule_agreement():
    """
    飲食コーナーケース B: 週末・混雑ピーク帯の「2時間制ルール」事前合意
    - 金曜19:00の予約において、確定直前に「2時間制（L.O. 90分）」の合意を取り付ける
    - ユーザーが承諾（「大丈夫です」）するまで確定（confirmed）に進まない
    """
    agent = VoiceAgentService()

    # 1. 金曜19時・お名前までのヒアリング
    slots_before_confirm = SlotState(
        date="2026-11-20", # 金曜
        time="19:00",
        guests=4,
        seat_type="table",
        course_name="2時間飲み放題付き 極み炭火焼鳥コース"
    )

    res1 = agent.process_utterance(
        message="予約者は佐藤、電話番号は090-1234-5678です",
        current_slots=slots_before_confirm,
        stage="hearing"
    )

    # 2時間制の確認が入るため、まだ confirmed にならない
    reply1 = res1.reply_text
    assert "2時間" in reply1 or "時間制" in reply1 or "混雑" in reply1 or "90分" in reply1
    print(f"\n[Test B 2時間制ルール確認]:\nAI応答: {reply1}\nステージ: {res1.stage}")

    # 2. ユーザーが承諾したことで確定へ遷移
    res2 = agent.process_utterance(
        message="はい、2時間制で大丈夫です！よろしくお願いします。",
        current_slots=res1.updated_slots,
        stage=res1.stage
    )

    assert res2.is_confirmed is True or res2.stage in ["confirmed", "additional_inquiry"]
    print(f"[Test B 2時間制承諾後]:\nAI応答: {res2.reply_text}\nステージ: {res2.stage}")


def test_private_room_alternative_table_proposal():
    """
    飲食コーナーケース C: 「個室希望」と満室時の代替席種（テーブル・ボックス席）提案
    1. DB上で個室（8席分）を満室にする
    2. ユーザーが「個室で4名予約したい」と発話
    3. システムが個室満室を検知し、代替として「奥の落ち着いたテーブル席（ボックス席）」を提案
    4. ユーザーが「じゃあテーブル席でいいですよ」と承諾した場合、seat_type が table に切り替わる
    """
    db: Session = SessionLocal()
    shop = BookingService.get_or_create_shop(db)
    target_date = "2026-11-20"
    target_time = "19:00"

    # 個室を満室にする予約を登録
    full_priv = Reservation(
        booking_code="RSV-PRIV99",
        date=target_date,
        time=target_time,
        guests=shop.private_rooms,  # 8席満室
        seat_type="private",
        customer_name="VIP様",
        status="confirmed"
    )
    db.add(full_priv)
    db.commit()

    agent = VoiceAgentService()
    checker = lambda d, t, g, s="table": (
        BookingService.check_seat_type_availability(db, d, t, g, s) if s == "private"
        else BookingService.check_availability_and_find_alternatives(db, d, t, g)
    )

    current_slots = SlotState(
        date=target_date,
        time=target_time,
        guests=4,
        seat_type="private"
    )

    res1 = agent.process_utterance(
        message="大事な会食なので、できれば個室でお願いしたいのですが空いてますか？",
        current_slots=current_slots,
        stage="hearing",
        availability_checker=checker
    )

    reply1 = res1.reply_text
    assert "個室" in reply1
    assert "テーブル" in reply1 or "ボックス" in reply1 or "お席" in reply1
    print(f"\n[Test C 個室満室時の代替席種提案]:\nAI応答: {reply1}")

    # ユーザーがテーブル席を受け入れ
    res2 = agent.process_utterance(
        message="なるほど、個室は埋まってるんですね。では奥のテーブル席でお願いします！",
        current_slots=res1.updated_slots,
        stage=res1.stage,
        availability_checker=checker
    )

    assert res2.updated_slots.seat_type in ["table", "box"]
    print(f"[Test C 代替席受諾後]:\n席種: {res2.updated_slots.seat_type}\nAI応答: {res2.reply_text}")

    # クリーンアップ
    db.delete(full_priv)
    db.commit()
    db.close()


def test_anniversary_birthday_plate_support():
    """
    飲食コーナーケース D: 記念日・誕生日プレート（サプライズ対応）
    - 発話: 「友人の誕生日祝いで行くのですが、サプライズでデザートプレートを用意してもらえますか？」
    - 期待値:
      1. AIがお祝いの言葉を述べ、特製バースデープレート（花火・メッセージ付き）を提案
      2. special_requests または pre_orders にバースデープレートが登録される
      3. メッセージ内容や提供タイミング（食後など）の確認が行われる
    """
    agent = VoiceAgentService()

    current_slots = SlotState(
        date="2026-11-20",
        time="19:00",
        guests=4,
        seat_type="table",
        course_name="2時間飲み放題付き 極み炭火焼鳥コース"
    )

    res = agent.process_utterance(
        message="実は友人の誕生日祝いで行くのですが、サプライズでデザートプレートを用意してもらえますか？",
        current_slots=current_slots,
        stage="hearing"
    )

    reply = res.reply_text
    assert "おめでとう" in reply or "お祝い" in reply or "プレート" in reply or "デザート" in reply or "誕生日" in reply
    assert res.updated_slots.special_requests is not None or len(res.updated_slots.pre_orders) > 0
    print(f"\n[Test D 記念日・誕生日プレート対応]:\nAI応答: {reply}\n特記事項: {res.updated_slots.special_requests}\nプレオーダー: {res.updated_slots.pre_orders}")


def test_existing_reservation_modification_and_cancellation():
    """
    飲食コーナーケース E: 「今日予約した田中だけど1人増やせる？」既存予約の変更・キャンセル対応
    1. DB上に「田中 太郎 4名 19:00」の既存予約を登録
    2. 人数変更の発話: 「今日19時で予約してる田中ですが、1人増えて5人になっても大丈夫ですか？」
       -> action='modify', guests=5, AIが4名→5名への変更を案内
    3. キャンセルの発話: 「今日19時で予約してる田中ですが、キャンセルでお願いします」
       -> action='cancel', AIがキャンセル受諾を案内
    """
    db: Session = SessionLocal()
    target_date = datetime.date.today().isoformat()

    # 1. 既存予約を作成
    existing_res = Reservation(
        booking_code="RSV-TANAKA01",
        date=target_date,
        time="19:00",
        guests=4,
        seat_type="table",
        customer_name="田中 太郎",
        phone_number="090-1111-2222",
        status="confirmed"
    )
    db.add(existing_res)
    db.commit()

    agent = VoiceAgentService()

    # 2. 人数変更
    res_mod = agent.process_utterance(
        message="今日19時で予約してる田中ですが、1人増えて5人になっても大丈夫ですか？",
        current_slots=None,
        stage="hearing"
    )

    assert res_mod.action == "modify" or res_mod.updated_slots.guests == 5
    reply_mod = res_mod.reply_text
    assert "田中" in reply_mod or "変更" in reply_mod or "5" in reply_mod or "承" in reply_mod
    print(f"\n[Test E 既存予約変更]:\nAI応答: {reply_mod}\nアクション: {res_mod.action}\n人数: {res_mod.updated_slots.guests}")

    # 3. キャンセル
    res_cancel = agent.process_utterance(
        message="今日19時で予約してる田中ですが、急に行けなくなったのでキャンセルでお願いします",
        current_slots=None,
        stage="hearing"
    )

    assert res_cancel.action == "cancel" or "キャンセル" in res_cancel.reply_text
    reply_cancel = res_cancel.reply_text
    assert "キャンセル" in reply_cancel
    print(f"\n[Test E 既存予約キャンセル]:\nAI応答: {reply_cancel}\nアクション: {res_cancel.action}")

    # クリーンアップ
    db.delete(existing_res)
    db.commit()
    db.close()

def test_dynamic_industry_presets_ryokan_and_dental():
    """
    業態テンプレート・動的プリセット切り替え ＆ DB管理テスト:
    1. 旅館プリセット（ryokan）への切り替え:
       - テンプレ側では施設名（name）およびオプション（pre_orders）が空であること（DB管理設計）
       - DB側で施設名（例: 嬉野温泉 翠月楼）や別注オプション（竹崎カキ、竹崎蟹、貸切風呂）を登録・更新
       - エージェントがDBに登録された施設名とFAQを動的に使って案内できること
    2. 歯科クリニックプリセット（clinic_dental）への切り替え
       - 初診/再診、麻酔アレルギー、痛みトリアージなどのヒアリングプロンプトが反映されること
    """
    db: Session = SessionLocal()

    # 1. 旅館プリセットへ切り替え（親Industryにリレーションされ、初期状態は空テンプレ）
    ryokan_shop = BookingService.get_or_create_shop(db, preset_key="ryokan")
    assert ryokan_shop.name == ""  # 初期は空設定のテンプレ
    assert ryokan_shop.pre_order_items_json == []  # 初期は空設定のテンプレ
    assert ryokan_shop.industry_type == "ryokan"
    assert ryokan_shop.industry is not None
    assert ryokan_shop.industry.name == "宿泊・温泉旅館"
    assert "温泉旅館" in ryokan_shop.persona_description

    # DB側で施設固有の名前とオプションを登録・管理
    ryokan_shop.name = "嬉野温泉 翠月楼"
    ryokan_shop.pre_order_items_json = [
        {"id": "opt_oyster", "name": "炭火焼き竹崎カキ盛り合わせ", "price": 3500},
        {"id": "opt_crab", "name": "茹で上げ竹崎蟹", "price": 4800},
        {"id": "opt_bath", "name": "展望貸切露天風呂", "price": 2500}
    ]
    db.commit()
    db.refresh(ryokan_shop)

    assert ryokan_shop.name == "嬉野温泉 翠月楼"
    pre_order_names = [p["name"] for p in ryokan_shop.pre_order_items_json]
    assert any("竹崎カキ" in n for n in pre_order_names)
    assert any("竹崎蟹" in n for n in pre_order_names)
    assert any("貸切" in n for n in pre_order_names)

    # 旅館プリセットでのAI応答テスト（DBの施設名「翠月楼」で挨拶）
    agent = VoiceAgentService()
    res_greet = agent.process_utterance(
        message="予約をお願いしたいのですが",
        shop=ryokan_shop
    )
    assert "翠月楼" in res_greet.reply_text

    # 2. 歯科クリニックプリセットへ切り替え（親Industry: clinic にリレーションされた初期空テンプレ）
    dental_shop = BookingService.get_or_create_shop(db, preset_key="clinic_dental")
    assert dental_shop.industry_type == "clinic"
    assert dental_shop.industry.name == "医療・クリニック"
    assert dental_shop.name == ""  # 初期は空設定のテンプレ
    assert "初診" in dental_shop.additional_inquiry_prompt
    assert "麻酔" in dental_shop.additional_inquiry_prompt

    # DB側で個別店舗（医院）名を登録
    dental_shop.name = "さくら歯科・矯正クリニック"
    db.commit()
    db.refresh(dental_shop)

    res_dental = agent.process_utterance(
        message="予約を取りたいです",
        shop=dental_shop
    )
    assert "さくら歯科" in res_dental.reply_text

    # 最後にデフォルトの yakitori に戻しておく
    BookingService.get_or_create_shop(db, preset_key="yakitori")
    db.close()

