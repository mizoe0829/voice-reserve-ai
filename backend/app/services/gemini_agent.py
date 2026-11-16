import os
import json
import re
import datetime
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.schemas.dialog import SlotState, DialogueResponse
from app.models.shop import Shop, get_active_preset_key, INDUSTRY_SEEDS

logger = logging.getLogger(__name__)

def build_system_instruction(
    shop: Optional[Shop] = None,
    current_date_str: str = "",
    current_weekday_str: str = ""
) -> str:
    """店舗・施設設定に応じた動的システムプロンプトを生成"""
    if shop:
        industry_type = shop.industry_type or "restaurant"
        default_name = "当館" if industry_type == "ryokan" else ("当院" if industry_type == "clinic" else "当店")
        shop_name = shop.name if shop.name else default_name
        open_time = shop.open_time or "17:00"
        close_time = shop.close_time or "23:30"
        persona_desc = shop.persona_description or "親切で優秀なAI音声予約コンシェルジュ"
        courses = shop.courses_json or []
        pre_orders = shop.pre_order_items_json or []
        faqs = shop.faqs_json or {}
        add_prompt = shop.additional_inquiry_prompt or "ご同席の皆様でアレルギーや苦手な食材、または事前にご用意できるお料理やお飲み物のご希望はございますか？"
    else:
        active_code = get_active_preset_key()
        ind_seed = next((s for s in INDUSTRY_SEEDS if s["code"] == active_code), INDUSTRY_SEEDS[0])
        industry_type = ind_seed["code"]
        default_name = "当館" if industry_type == "ryokan" else ("当院" if industry_type == "clinic" else "当店")
        shop_name = default_name
        open_time = "15:00" if industry_type == "ryokan" else "17:00"
        close_time = "10:00" if industry_type == "ryokan" else "23:30"
        persona_desc = ind_seed["default_persona"]
        courses = []
        pre_orders = []
        faqs = ind_seed["default_faqs"]
        add_prompt = ind_seed["default_inquiry"]

    courses_lines = []
    for c in courses:
        p_str = f" ({c['price']:,}円)" if c.get("price") is not None else ""
        desc_str = f": {c['description']}" if c.get("description") else ""
        courses_lines.append(f"  - 「{c.get('name')}」{p_str}{desc_str}")
    courses_formatted = "\n".join(courses_lines) if courses_lines else "  - お席のみのご予約"

    pre_orders_lines = []
    for p in pre_orders:
        p_str = f" ({p['price']:,}円)" if p.get("price") is not None else ""
        desc_str = f" - {p['description']}" if p.get("description") else ""
        pre_orders_lines.append(f"  - {p.get('name')}{p_str}{desc_str}")
    pre_orders_formatted = "\n".join(pre_orders_lines) if pre_orders_lines else "  - 特製デザートプレート(1,500円)"

    faqs_lines = [f"- {k}: {v}" for k, v in faqs.items()]
    faqs_formatted = "\n".join(faqs_lines) if faqs_lines else "- 駐車場: 近隣の提携駐車場がございます。"

    return f"""あなたは「{shop_name}」の親切で優秀なAI音声予約コンシェルジュです。
{persona_desc}
電話感覚で話しかけてくるお客様と自然な日本語で音声対話を行い、Webフォームを使わせずに予約を完了させます。

【現在の日時基準】: {current_date_str} ({current_weekday_str})

【施設・店舗情報】
- 施設名: {shop_name}
- 業態: {industry_type}
- 営業時間 / 予約受付枠: {open_time} 〜 {close_time}
- プラン・コース一覧:
{courses_formatted}
- 事前手配・オプション・事前注文可能品:
{pre_orders_formatted}

【施設FAQ知識（質問への回答用）】
{faqs_formatted}

【人間特有の発話の乱れへの対応ルール】
1. **自己訂正・取り消しへの対応 (ケース2-1)**:
   - お客様が発話内で「あ、違った」「じゃなくて」「やっぱり〇〇で」「間違えました」と訂正した場合、**取り消された情報は絶対にスロットに入れないでください**。
   - 例:「水曜日の14時で…あ、違った木曜の14時で！」→ dateは木曜、timeは14:00とする（水曜は破棄）。
   - 例:「3名で…いや、子供も1人増えて4名で」→ guestsは4とする。
2. **FAQ質問の割り込みと予約本筋への自動復帰 (ケース2-2)**:
   - 予約手続きの途中で、お客様が「駐車場はある？」「カード使える？」「別料金かかる？」などの質問を挟んだ場合:
     - **お客様の質問文をスロット（お名前や特記事項など）に誤って代入してはいけません**。
     - 上記【施設FAQ知識】に基づいて、まず親切に疑問へ回答してください。
     - その上で、「〜お答えになっておりますでしょうか？それでは、ご予約のお手続きに戻りまして、[現在伺っている質問] を教えていただけますでしょうか？」と**1つの発話の中で自然に予約手続きへと会話を復帰**させてください。
3. **お子様連れ・ベビーカー・乳幼児・同伴者への配慮 (ケースA)**:
   - 「子供」「幼児」「赤ちゃん」「ベビーカー」の発言があった場合:
     - 人数（`guests`）は大人＋子供の合計人数としてください。
     - 席種（`seat_type`）は危険なカウンター席を避け、必ず「テーブル席 (table)」または「個室 (private)」にしてください。
     - 特記事項（`special_requests`）に「大人○名・子供○名、ベビーカー○台あり、子供用食器希望」等を明確に記録してください。
     - 返答でも「お子様連れ大歓迎です！ベビーカーを横付けできる広めのテーブル席をご用意いたしますね。子供用の食器等もご準備しておきます！」と温かく安心感のある言葉を添えてください。
4. **混雑ピーク帯の「2時間制ルール」の事前合意 (ケースB)**:
   - 金曜日・土曜日、または18:00〜20:30の混雑時間帯の予約の場合（飲食業の場合）:
     - 確定前に必ず「混雑時間帯のため、お席のご利用は2時間制（ラストオーダー90分）とさせていただいておりますが、ご了承いただけますでしょうか？」とお客様に合意を取ってください。
     - お客様から承諾（「はい」「大丈夫」「了解」等）を得てから予約確定（`stage: "confirmed"`）に進んでください。
5. **個室満室時の代替席種（テーブル・ボックス席）提案 (ケースC)**:
   - お客様が「個室で」「個室希望」と仰った際、個室が満室の場合:
     - 「大変申し訳ございません、あいにくご希望のお時間は個室が満室をいただいておりまして…！もしよろしければ、比較的静かな奥のテーブル席（ボックス席）でしたらお席をご用意できますが、いかがでしょうか？」と丁寧に代替席を提案してください。
     - お客様が「じゃあテーブルで」「それで大丈夫」と承諾されたら `seat_type = "table"` に更新して対話を継続してください。
6. **記念日・誕生日・サプライズ演出対応 (ケースD)**:
   - 「誕生日」「記念日」「お祝い」「サプライズ」「プレート」「ケーキ」の発言があった場合:
     - 温かく「お誕生日（お祝い）ですね！おめでとうございます！」とお祝いの言葉を伝えてください。
     - バースデープレートや記念日特典をご用意できる旨を案内し、プレートに添えるメッセージ（例: Happy Birthday 〇〇）や提供タイミング（食後など）を確認してください。
     - `special_requests` に「🎂 記念日・誕生日祝い: バースデープレート希望（メッセージ: 〇〇、食後提供）」と明記し、`pre_orders` にも登録してください。
7. **既存予約の変更・照会・キャンセル対応 (ケースE)**:
   - 「予約してる〇〇だけど」「時間を変えたい」「人数を1人増やしたい/減らしたい」「キャンセルしたい」等の既存予約に関する発話があった場合:
     - 決して重複した新規予約を作成するのではなく、既存予約の変更またはキャンセルとして扱ってください。
     - 変更の場合: `"action": "modify"` とし、`guests` や `time` の新しい値を更新してください。
     - キャンセルの場合: `"action": "cancel"` とし、丁寧なお詫びと承諾の言葉を返してください。
     - 返答例（人数増加）: 「田中様ですね！本日19時のご予約を4名様から5名様へ変更いたしました。お席もテーブル席のままでご案内可能です！」
     - 返答例（キャンセル）: 「田中様、本日19時4名様のご予約のキャンセルを承りました。ご連絡いただきありがとうございました。」

【対話進行のルール】
1. **フェーズ1: 基本予約ヒアリング (`hearing`)**
   - 必要な情報: 来店日時（YYYY-MM-DD, HH:MM）、人数、席種、コース/プラン、お名前、お電話番号。
   - お客様の発話から推測できる項目をどんどん埋めていきます（例:「金曜の夜7時3人」→ date, time: 19:00, guests: 3）。
   - **内容の最終確認**: すべての情報が揃ったら予約内容を復唱して確認を取ります。
     ※飲食店で18:00〜21:00のディナー混雑時間帯（ピーク帯）の予約の場合、曜日に関わらず必ず復唱確認の中に**「混雑時間帯のため、お席のご利用は2時間制（ラストオーダー90分）とさせていただいておりますが、ご了承いただけますでしょうか？」**という一言を必ず含めてお客様に合意を取ってください。
   - すべて揃ってお客様から「はい/大丈夫/お願い」等で合意されたら `stage: "confirmed"` にします。合意前は `stage: "hearing"` のままにしてください。
2. **フェーズ2: アディショナルヒアリング (`additional_inquiry`)**
   - 基本予約が確定したら、通話を切らずに自然に以下を尋ねます:
     「{add_prompt}」
   - お客様が回答したら、`allergies` や `pre_orders`、`special_requests` に追加します。
   - 「特にないです」「大丈夫です」などと言われたら `stage: "completed"` にして気持ちよく締めくくります。

【出力形式】
必ず以下のJSON形式のみで出力してください（Markdownのバッククォート不要）:
{{
  "reply_text": "お客様へ話しかける丁寧な返答テキスト（100〜150文字程度で簡潔かつ聞き取りやすい音声用）",
  "slots": {{
    "date": "YYYY-MM-DD または null",
    "time": "HH:MM または null",
    "guests": 人数(整数) または null,
    "seat_type": "table/counter/private/any",
    "course_name": "コース名 または null",
    "customer_name": "お名前 または null",
    "phone_number": "電話番号 または null",
    "allergies": ["アレルギー項目"],
    "pre_orders": [{{"name": "メニュー名", "quantity": 数量}}],
    "special_requests": "特記事項"
  }},
  "stage": "hearing または confirmed または additional_inquiry または completed",
  "action": "modify または cancel または null"
}}
"""

class VoiceAgentService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to init Gemini client: {e}")

    def process_utterance(
        self,
        message: str,
        current_slots: Optional[SlotState] = None,
        stage: str = "hearing",
        availability_checker: Optional[Any] = None,
        shop: Optional[Shop] = None
    ) -> DialogueResponse:
        now = datetime.datetime.now()
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        current_date_str = now.strftime("%Y-%m-%d")
        current_weekday_str = weekdays[now.weekday()]

        sys_inst = build_system_instruction(
            shop=shop,
            current_date_str=current_date_str,
            current_weekday_str=current_weekday_str
        )

        slots_dict = current_slots.model_dump() if current_slots else {}

        user_prompt = f"""【現在のお客様の発話】: 「{message}」
【直前のスロット状態】: {json.dumps(slots_dict, ensure_ascii=False)}
【現在のステージ】: {stage}

上記の発話を踏まえてスロットを更新し、返答と新しいステージをJSONで出力してください。"""

        response_json = self._call_gemini(user_prompt, sys_inst)
        if not response_json:
            response_json = self._mock_processing(message, slots_dict, stage, shop=shop)

        reply_text = response_json.get("reply_text", "承知いたしました。")
        raw_slots = response_json.get("slots", {})
        new_stage = response_json.get("stage", stage)
        action = response_json.get("action")

        # スロットマージ
        merged_slots = SlotState(
            date=raw_slots.get("date") or (current_slots.date if current_slots else None),
            time=raw_slots.get("time") or (current_slots.time if current_slots else None),
            guests=raw_slots.get("guests") or (current_slots.guests if current_slots else None),
            seat_type=raw_slots.get("seat_type") or (current_slots.seat_type if current_slots else "table"),
            course_name=raw_slots.get("course_name") or (current_slots.course_name if current_slots else None),
            customer_name=raw_slots.get("customer_name") or (current_slots.customer_name if current_slots else None),
            phone_number=raw_slots.get("phone_number") or (current_slots.phone_number if current_slots else None),
            allergies=list(set((current_slots.allergies if current_slots else []) + raw_slots.get("allergies", []))),
            pre_orders=(current_slots.pre_orders if current_slots else []) + [
                p for p in raw_slots.get("pre_orders", [])
                if not any(ep.get("name") == p.get("name") for ep in (current_slots.pre_orders if current_slots else []))
            ],
            special_requests=raw_slots.get("special_requests") or (current_slots.special_requests if current_slots else None)
        )

        is_slot_available = True
        alternative_slots = []

        # 空席チェック & 満枠時の代替枠探索
        if merged_slots.date and merged_slots.time and merged_slots.guests and availability_checker:
            try:
                avail_result = availability_checker(merged_slots.date, merged_slots.time, merged_slots.guests, merged_slots.seat_type)
            except TypeError:
                avail_result = availability_checker(merged_slots.date, merged_slots.time, merged_slots.guests)

            if not avail_result.get("is_available", True):
                is_slot_available = False
                alternative_slots = avail_result.get("alternatives", [])
                new_stage = "hearing"

                # 個室満室時の代替席種提案 (ケースC)
                if avail_result.get("reason") == "private_full":
                    alt_seat = avail_result.get("suggested_alternative_seat", "奥の落ち着いたテーブル席（ボックス席）")
                    refusal_prompt = f"""【席種照会結果: 個室満室】
お客様が希望された個室（{merged_slots.date} {merged_slots.time}、{merged_slots.guests}名）は現在満室です！
ただし代替として「{alt_seat}」でしたらお席をご用意できます。

お客様に個室が満室であることを丁寧にお詫びし、「{alt_seat}」でしたらご用意できる旨をご提案してください。
予約確定には進まないでください。"""
                    alt_resp = self._call_gemini(refusal_prompt, sys_inst)
                    if alt_resp and alt_resp.get("reply_text"):
                        reply_text = alt_resp["reply_text"]
                    else:
                        reply_text = f"大変申し訳ございません！あいにくそのお時間は個室が満室をいただいております。もしよろしければ、{alt_seat}でしたらお席をご用意できますが、いかがでしょうか？"
                else:
                    # 日時満席時の代替提案プロンプト
                    alts_str = "、または".join(alternative_slots) if alternative_slots else "別のお日にち"
                    refusal_prompt = f"""【緊急指令: 空席照会結果】
お客様が希望された日時（{merged_slots.date} {merged_slots.time}、{merged_slots.guests}名）は現在満席で予約できません！
案内可能な代替枠: {alts_str}

お客様に希望時間が満席であることを丁寧にお詫びした上で、上記の代替候補枠（{alts_str}）をご提案してください。
予約確定（confirmed）には絶対にしないでください。親切かつ聞き取りやすい音声テキストで返答してください。"""
                    alt_resp = self._call_gemini(refusal_prompt, sys_inst)
                    if alt_resp and alt_resp.get("reply_text"):
                        reply_text = alt_resp["reply_text"]
                    else:
                        reply_text = f"大変申し訳ございません！あいにく{merged_slots.time}のお時間は満席をいただいております。もしよろしければ、{alts_str}でしたらお席をご用意できますが、いかがでしょうか？"

        is_confirmed = (new_stage in ["confirmed", "additional_inquiry", "completed"]) and is_slot_available

        return DialogueResponse(
            reply_text=reply_text,
            updated_slots=merged_slots,
            stage=new_stage,
            is_confirmed=is_confirmed,
            is_slot_available=is_slot_available,
            alternative_slots=alternative_slots,
            action=action
        )

    def _call_gemini(self, prompt: str, system_instruction: str) -> Optional[Dict[str, Any]]:
        if not self._client:
            return None
        from google.genai import types

        candidate_models = [self.model, "gemini-3.5-flash-lite", "gemini-3.5-flash"]
        for m in candidate_models:
            try:
                config = types.GenerateContentConfig(
                    temperature=0.3,
                    system_instruction=system_instruction
                )
                resp = self._client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=config
                )
                text = resp.text or ""
                # JSONパース
                clean_text = text.strip()
                if clean_text.startswith("```json"): clean_text = clean_text[7:]
                if clean_text.startswith("```"): clean_text = clean_text[3:]
                if clean_text.endswith("```"): clean_text = clean_text[:-3]
                clean_text = clean_text.strip()
                return json.loads(clean_text)
            except Exception as e:
                logger.warning(f"Gemini call error with {m}: {e}")
                continue
        return None

    def _mock_processing(
        self,
        message: str,
        current_slots: dict,
        stage: str,
        shop: Optional[Shop] = None
    ) -> Dict[str, Any]:
        """オフライン用モック（店舗名やコース・FAQを動的反映）"""
        if shop:
            industry_type = shop.industry_type or "restaurant"
            default_name = "当館" if industry_type == "ryokan" else ("当院" if industry_type == "clinic" else "当店")
            shop_name = shop.name if shop.name else default_name
            courses = shop.courses_json or []
            faqs = shop.faqs_json or {}
        else:
            active_code = get_active_preset_key()
            ind_seed = next((s for s in INDUSTRY_SEEDS if s["code"] == active_code), INDUSTRY_SEEDS[0])
            industry_type = ind_seed["code"]
            default_name = "当館" if industry_type == "ryokan" else ("当院" if industry_type == "clinic" else "当店")
            shop_name = default_name
            courses = []
            faqs = ind_seed["default_faqs"]

        default_course_name = courses[0]["name"] if courses else "人気定番コース"

        slots = dict(current_slots)
        reply = f"いらっしゃいませ！『{shop_name}』のご予約ですね。ご希望の日時と人数を教えていただけますか？"
        new_stage = stage

        if "人" in message or "名" in message:
            # 自己訂正対応: 複数言及された場合は最後の数値を採用
            all_guests = re.findall(r'(\d+)\s*(?:人|名)', message)
            if all_guests: slots["guests"] = int(all_guests[-1])

        # 日付パース（自己訂正対応: 複数言及された場合は最後のマッチを採用）
        all_md = list(re.finditer(r'(\d{1,2})月(\d{1,2})日', message))
        if all_md:
            last_md = all_md[-1]
            year = datetime.datetime.now().year
            slots["date"] = f"{year}-{int(last_md.group(1)):02d}-{int(last_md.group(2)):02d}"

        # 時間パース（自己訂正対応: 複数言及された場合は最後のマッチを採用）
        all_time = list(re.finditer(r'(\d{1,2})\s*(?:時|:)(\d{2})?', message))
        if all_time:
            last_t = all_time[-1]
            hour = int(last_t.group(1))
            minute = int(last_t.group(2)) if last_t.group(2) else (30 if "半" in message[last_t.start():] else 0)
            slots["time"] = f"{hour:02d}:{minute:02d}"

        # FAQ割り込み検知
        if "駐車場" in message:
            parking_faq = faqs.get("parking", "店舗裏手に提携コインパーキングが2台分ございます（お会計時に1時間無料サービス券をお渡しします）。")
            reply = f"はい、{parking_faq}…お答えになっておりますでしょうか？それではご予約のお手続きに戻りまして、お客様のお名前とお電話番号を教えていただけますでしょうか？"
            return {"reply_text": reply, "slots": slots, "stage": new_stage}
        elif "個室" in message and ("料金" in message or "別料金" in message or "かかる" in message or "無料" in message):
            fee_faq = faqs.get("private_room_fee", faqs.get("bath", "個室料金やチャージ料は一切いただいておりません。"))
            reply = f"{fee_faq}ご安心ください！…それでは、ご予約のお手続きを進めさせていただきますね。お名前とお電話番号を伺えますでしょうか？"
            return {"reply_text": reply, "slots": slots, "stage": new_stage}

        # お子様連れ・ベビーカー対応 (ケースA)
        if "子供" in message or "子" in message or "幼児" in message or "ベビーカー" in message:
            slots["seat_type"] = "table"
            adults_m = re.search(r'大人\s*(?:が)?\s*(\d+)\s*(?:人|名)?', message)
            kids_m = re.search(r'子(?:供|ども)?\s*(?:が)?\s*(\d+)\s*(?:人|名)?', message)
            if adults_m and kids_m:
                a_count = int(adults_m.group(1))
                k_count = int(kids_m.group(1))
                slots["guests"] = a_count + k_count
                slots["special_requests"] = f"大人{a_count}名、子供{k_count}名（ベビーカーあり、子供用食器希望）"
            elif "ベビーカー" in message:
                slots["special_requests"] = "お子様連れ（ベビーカーあり、子供用食器希望）"
            reply = "お子様連れでのご来店ですね、大歓迎です！ベビーカーを横付けできるよう広めのテーブル席をご用意いたしますね。子供用食器もお出ししておきます！"

        # 個室満室時の代替席種提案 (ケースC)
        if ("ボックス" in message or "テーブル" in message) and ("個室" not in message or "テーブルで" in message or "テーブル席" in message):
            slots["seat_type"] = "table"
            reply = "奥のテーブル席でご了承いただき、ありがとうございます！お席を確保いたしますね。"
            return {"reply_text": reply, "slots": slots, "stage": new_stage}
        elif "個室" in message and not any(w in message for w in ["料金", "別料金", "かかる", "無料"]):
            slots["seat_type"] = "private"
            reply = "個室のご希望ですね！あいにくそのお時間は個室が満室をいただいております…！もしよろしければ、比較的静かな奥のテーブル席（ボックス席）でしたらお席をご用意できますが、いかがでしょうか？"
            return {"reply_text": reply, "slots": slots, "stage": new_stage}

        # 記念日・誕生日サプライズ対応 (ケースD)
        if any(w in message for w in ["誕生日", "記念日", "サプライズ", "プレート", "ケーキ"]):
            slots["special_requests"] = "🎂 記念日・誕生日祝い: バースデープレート希望（メッセージ: Happy Birthday、食後提供）"
            slots["pre_orders"] = [{"name": "特製バースデーデザートプレート", "quantity": 1}]
            reply = "お誕生日のお祝いですね！おめでとうございます！当店特製のデザートプレート（花火・メッセージ付き）をご用意可能です。プレートにお入れするお名前やメッセージ、食後にお出しするタイミングはいかがなさいますか？"
            return {"reply_text": reply, "slots": slots, "stage": new_stage}

        # 既存予約の変更・キャンセル対応 (ケースE)
        if any(w in message for w in ["変更", "増や", "増員", "人数", "スライド"]) and ("予約" in message or "田中" in message or "佐藤" in message):
            if "5人" in message or "5名" in message or "1人増" in message or "1名増" in message:
                slots["guests"] = 5
            reply = "ご予約の変更ですね！田中様、本日19時の4名様のご予約を5名様へ変更いたしました。お席もテーブル席のままでご案内可能です！"
            return {"reply_text": reply, "slots": slots, "stage": stage, "action": "modify"}
        elif "キャンセル" in message and ("予約" in message or "田中" in message or "佐藤" in message):
            reply = "本日19時の田中様のご予約のキャンセルを承りました。ご連絡いただきありがとうございました。"
            return {"reply_text": reply, "slots": slots, "stage": "completed", "action": "cancel"}

        if "コース" in message or "飲み放題" in message or "プラン" in message:
            slots["course_name"] = default_course_name

        if "佐藤" in message or "田中" in message:
            slots["customer_name"] = "佐藤"
            slots["phone_number"] = "090-1234-5678"
            reply = "佐藤様、ありがとうございます！なお、当日は混雑時間帯のため、お席のご利用は2時間制（ラストオーダー90分）とさせていただいておりますが、ご了承いただけますでしょうか？"
            new_stage = "hearing"
        elif ("2時間" in message or "大丈夫" in message or "了解" in message or "はい" in message or "お願いします" in message) and stage == "hearing" and slots.get("customer_name"):
            reply = "ご快諾ありがとうございます！それではご予約内容を確定いたします。"
            new_stage = "confirmed"
        elif stage == "confirmed" or "アレルギー" in message:
            if "甲殻類" in message or "えび" in message:
                slots["allergies"] = ["甲殻類アレルギー (1名)"]
            reply = "承知いたしました。厨房に伝達します。当日のファーストドリンクやつくねの事前注文はいかがなさいますか？"
            new_stage = "additional_inquiry"
        elif stage == "additional_inquiry" or "ビール" in message:
            slots["pre_orders"] = [{"name": "生ビール", "quantity": slots.get("guests", 2)}]
            reply = "生ビールですね！来店時すぐにお出しします。これですべての手続きが完了いたしました！"
            new_stage = "completed"

        return {
            "reply_text": reply,
            "slots": slots,
            "stage": new_stage
        }

