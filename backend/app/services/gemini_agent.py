import os
import json
import re
import datetime
import logging
from typing import Optional, Dict, Any
from app.core.config import settings
from app.schemas.dialog import SlotState, DialogueResponse

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """あなたは人気焼鳥店「炭火焼鳥 鳥神（とりじん）」の親切で優秀なAI音声予約コンシェルジュです。
電話感覚で話しかけてくるお客様と自然な日本語で音声対話を行い、Webフォームを使わせずに予約を完了させます。

【現在の日時基準】: {current_date} ({current_weekday})

【お店の情報】
- 営業時間: 17:00 〜 23:30 (ラストオーダー 22:30)
- 席種: テーブル席、カウンター席、個室（個室は4名様以上推奨）
- コース:
  1. 「2時間飲み放題付き 極み炭火焼鳥コース」(5,000円)
  2. 「鳥神特選 贅沢地鶏フルコース」(7,000円)
  3. 「お席のみのご予約（アラカルト）」(0円)
- 事前注文（プレオーダー）可能品:
  - 生ビール(600円)、角ハイボール(550円)、特製レモンサワー(580円)、ウーロン茶(400円)
  - 職人おまかせ炭火串焼き5種盛り合わせ(1,180円)
  - 名物・月見つくね串(1本380円)
  - 秘伝仕込み 若鶏のジューシー唐揚げ(780円)
  - 茶豆の枝豆(450円)

【対話進行のルール】
1. **フェーズ1: 基本予約ヒアリング (`hearing`)**
   - 必要な情報: 来店日時（YYYY-MM-DD, HH:MM）、人数、席種、コース、お名前、お電話番号。
   - お客様の発話から推測できる項目をどんどん埋めていきます（例:「金曜の夜7時3人」→ date, time: 19:00, guests: 3）。
   - すべて揃ったら、確認を取り、「はい/お願い」等で合意されたら `stage: "confirmed"` にします。
2. **フェーズ2: アディショナルヒアリング (`additional_inquiry`)**
   - 基本予約が確定したら、通話を切らずに自然に以下を尋ねます:
     「ありがとうございます！続いて、ご同席の皆様でアレルギーや苦手な食材はございますか？また、乾杯のファーストドリンクや、すぐお出しできる串焼き盛り合わせ・名物つくね・唐揚げなどを事前にご用意しておくこともできますが、いかがなさいますか？」
   - お客様が「甲殻類アレルギー」「生ビール3つとつくね3本」などと答えたら、`allergies` や `pre_orders` に追加します。
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
  "stage": "hearing または confirmed または additional_inquiry または completed"
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
        stage: str = "hearing"
    ) -> DialogueResponse:
        now = datetime.datetime.now()
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        current_date_str = now.strftime("%Y-%m-%d")
        current_weekday_str = weekdays[now.weekday()]

        sys_inst = SYSTEM_INSTRUCTION.format(
            current_date=current_date_str,
            current_weekday=current_weekday_str
        )

        slots_dict = current_slots.model_dump() if current_slots else {}

        user_prompt = f"""【現在のお客様の発話】: 「{message}」
【直前のスロット状態】: {json.dumps(slots_dict, ensure_ascii=False)}
【現在のステージ】: {stage}

上記の発話を踏まえてスロットを更新し、返答と新しいステージをJSONで出力してください。"""

        response_json = self._call_gemini(user_prompt, sys_inst)
        if not response_json:
            response_json = self._mock_processing(message, slots_dict, stage)

        reply_text = response_json.get("reply_text", "承知いたしました。")
        raw_slots = response_json.get("slots", {})
        new_stage = response_json.get("stage", stage)

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

        is_confirmed = (new_stage in ["confirmed", "additional_inquiry", "completed"])

        return DialogueResponse(
            reply_text=reply_text,
            updated_slots=merged_slots,
            stage=new_stage,
            is_confirmed=is_confirmed
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

    def _mock_processing(self, message: str, current_slots: dict, stage: str) -> Dict[str, Any]:
        """オフライン用モック"""
        slots = dict(current_slots)
        reply = "いらっしゃいませ！『炭火焼鳥 鳥神』のご予約ですね。ご希望の日時と人数を教えていただけますか？"
        new_stage = stage

        if "人" in message or "名" in message:
            import re
            m = re.search(r'(\d+)\s*(?:人|名)', message)
            if m: slots["guests"] = int(m.group(1))

        if "時" in message or ":" in message:
            slots["time"] = "19:00"

        if "コース" in message or "飲み放題" in message:
            slots["course_name"] = "2時間飲み放題付き 極み炭火焼鳥コース"

        if "佐藤" in message or "田中" in message:
            slots["customer_name"] = "佐藤"
            slots["phone_number"] = "090-1234-5678"
            reply = "佐藤様、ありがとうございます！ご予約内容を確認いたします。よろしければ予約を確定します。"
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
