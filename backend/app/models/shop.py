import os
from typing import Dict, Any
from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

SHOP_PRESETS: Dict[str, Dict[str, Any]] = {
    # 1. 飲食店モデル（炭火焼鳥・居酒屋）
    "yakitori": {
        "name": "炭火焼鳥 鳥神（とりじん） 渋谷本店",
        "industry_type": "restaurant",
        "address": "東京都渋谷区道玄坂1-2-3",
        "google_place_id": "ChIJ_wom9f2LGGAR79K1XqQ",
        "total_seats": 40,
        "table_seats": 24,
        "counter_seats": 8,
        "private_rooms": 8,
        "open_time": "17:00",
        "close_time": "23:30",
        "persona_description": "人気焼鳥店の親切で優秀なAI音声予約コンシェルジュ",
        "courses": [
            {"id": "course_nomi", "name": "2時間飲み放題付き 極み炭火焼鳥コース", "price": 5000, "description": "名物つくね、希少部位5種、飲み放題付き定番人気"},
            {"id": "course_zeitaku", "name": "料理長特選 贅沢地鶏フルコース", "price": 7000, "description": "特選地鶏鍋と炭火串焼きの豪華プラン"},
            {"id": "seat_only", "name": "お席のみのご予約（アラカルト注文）", "price": 0, "description": "当日お好きな料理・ドリンクをご注文ください"}
        ],
        "pre_orders": [
            {"id": "drink_beer", "name": "生ビール（プレミアムモルツ）", "category": "drink", "price": 600},
            {"id": "drink_highball", "name": "角ハイボール", "category": "drink", "price": 550},
            {"id": "drink_lemon", "name": "特製生搾りレモンサワー", "category": "drink", "price": 580},
            {"id": "drink_oolong", "name": "ウーロン茶（ソフトドリンク）", "category": "drink", "price": 400},
            {"id": "food_kushimori", "name": "職人おまかせ炭火串焼き5種盛り合わせ", "category": "food", "price": 1180, "description": "炭火で香ばしく焼き上げてお出しします"},
            {"id": "food_tsukune", "name": "名物・月見つくね串（本数指定）", "category": "food", "price": 380, "description": "秘伝タレと濃厚卵黄の看板串"},
            {"id": "food_karaage", "name": "秘伝醤油仕込み 若鶏のジューシー唐揚げ", "category": "food", "price": 780, "description": "外はカリッと中はジューシーな熱々唐揚げ"},
            {"id": "food_edamame", "name": "スピードおつまみ 茶豆の枝豆", "category": "food", "price": 450, "description": "着席と同時にすぐ乾杯できるスピード前菜"},
            {"id": "food_birthday_plate", "name": "特製バースデーデザートプレート（花火・メッセージ付き）", "category": "food", "price": 1500, "description": "記念日・誕生日サプライズ演出用プレート"}
        ],
        "faqs": {
            "parking": "店舗専用駐車場はございませんが、すぐ裏手に提携コインパーキングが2台分ございます（お会計時に1時間無料サービス券をお渡しします）。",
            "private_room_fee": "個室料・チャージ料は一切いただいておりません（無料です）。",
            "payment": "現金、各種クレジットカード、PayPay等に対応しております。",
            "smoking": "全席完全禁煙です（店舗の外に喫煙スペースがございます）。",
            "invoice": "適格請求書（インボイス）対応の領収書を発行可能です。"
        },
        "additional_inquiry_prompt": "ありがとうございます！続いて、ご同席の皆様でアレルギーや苦手な食材はございますか？また、乾杯のファーストドリンクや、すぐお出しできる串焼き盛り合わせ・名物つくね・唐揚げなどを事前にご用意しておくこともできますが、いかがなさいますか？"
    },

    # 2. 温泉旅館モデル（DB側で施設名・オプション・プランを自由設定可能）
    "ryokan": {
        "name": "",  # DB側で施設名を管理
        "industry_type": "ryokan",
        "address": "",
        "google_place_id": "",
        "total_seats": 20,  # 総客室数
        "table_seats": 12,  # 一般客室（和室・和洋室）
        "counter_seats": 0,
        "private_rooms": 8,   # 露天風呂付き特別客室・離れ
        "open_time": "15:00", # チェックイン開始
        "close_time": "10:00", # チェックアウト
        "persona_description": "温泉旅館の親切・丁寧なAI宿泊コンシェルジュ",
        "courses": [
            {"id": "ryokan_standard", "name": "料理長特選 季節の会席宿泊プラン（1泊2食付き）", "price": 25000, "description": "旬の食材を活かした特選会席と朝食付きの定番プラン"},
            {"id": "ryokan_zeitaku", "name": "贅沢極み懐石プラン（1泊2食付き）", "price": 35000, "description": "厳選食材の特別懐石をお楽しみいただける特別プラン"},
            {"id": "ryokan_morning_only", "name": "1泊朝食付きプラン", "price": 12000, "description": "遅めの到着にも安心な朝食付きプラン"}
        ],
        "pre_orders": [],  # DB側で別注料理（カキ、蟹、地酒など）や貸切風呂・送迎バス等のオプションを管理
        "faqs": {
            "hotspring": "天然温泉の大浴場および露天風呂を完備しております。",
            "dinner_time": "夕食の最終スタートは19:30となっております。",
            "parking": "敷地内に宿泊者様専用の無料駐車場を完備しております。"
        },
        "additional_inquiry_prompt": "ありがとうございます！続いて、ご同伴の皆様でアレルギーや苦手な食材はございますか？また、別注料理やお風呂の手配など、事前にご準備しておくご要望はございますでしょうか？"
    },

    # 3. 歯科・クリニックモデル（初診/再診・トリアージ）
    "clinic_dental": {
        "name": "さくら歯科・矯正クリニック",
        "industry_type": "clinic",
        "address": "東京都目黒区自由が丘1-5-8",
        "google_place_id": "ChIJ_sakura_dental",
        "total_seats": 6,  # 診察ユニット台数
        "table_seats": 5,  # 一般診療ユニット
        "counter_seats": 0,
        "private_rooms": 1,  # 特診室・個室ユニット
        "open_time": "09:30",
        "close_time": "19:00",
        "persona_description": "地域の皆様に寄り添う親切・丁寧な歯科クリニックのAI予約受付コンシェルジュ",
        "courses": [
            {"id": "clinic_checkup", "name": "定期検診・歯石クリーニング（保険適用）", "price": 3500, "description": "お口全体のチェックと専門機器による歯石除去"},
            {"id": "clinic_pain", "name": "痛み・しみる・詰め物が取れた（応急・一般診療）", "price": 3000, "description": "虫歯や歯のトラブルに対する診察と治療"},
            {"id": "clinic_whitening", "name": "オフィスホワイトニング（自由診療・約60分）", "price": 18000, "description": "高濃度ジェルと専用LEDで歯を自然な白さに"}
        ],
        "pre_orders": [
            {"id": "opt_first_visit", "name": "初診問診（問診票記入のため15分前到着案内済み）", "category": "service", "price": 0},
            {"id": "opt_anesthesia", "name": "痛みに配慮した極細針・表面麻酔希望", "category": "medical", "price": 0}
        ],
        "faqs": {
            "first_visit": "初診の方は問診票の記入がございますので、ご予約の15分前までに健康保険証をご持参のうえお越しください。",
            "parking": "提携駐車場が隣接ビルにございます。1時間分の駐車サービス券をお渡ししております。",
            "payment": "保険診療は現金またはPayPay、自費診療（ホワイトニング等）は各種クレジットカードをご利用いただけます。"
        },
        "additional_inquiry_prompt": "承知いたしました！当院は初めて（初診）でいらっしゃいますか？また、麻酔のアレルギーやお薬の服用歴、妊娠中など、事前に医師へ伝えておきたい配慮事項はございますでしょうか？"
    }
}

def get_active_preset_key() -> str:
    """環境変数 SHOP_PRESET で指定されたプリセット名を取得（デフォルト: yakitori）"""
    return os.getenv("SHOP_PRESET", "yakitori")

def get_preset_config(preset_key: str = "yakitori") -> Dict[str, Any]:
    """プリセット設定辞書を返す"""
    return SHOP_PRESETS.get(preset_key, SHOP_PRESETS["yakitori"])

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    preset_key = Column(String(50), default="yakitori")
    name = Column(String(100))
    industry_type = Column(String(50))
    address = Column(String(200))
    google_place_id = Column(String(100))
    
    # 席数在庫
    total_seats = Column(Integer, default=40)
    table_seats = Column(Integer, default=24)
    counter_seats = Column(Integer, default=8)
    private_rooms = Column(Integer, default=8)

    # 営業時間
    open_time = Column(String(10), default="17:00")
    close_time = Column(String(10), default="23:30")
    
    courses_json = Column(JSON)
    pre_order_items_json = Column(JSON)
    faqs_json = Column(JSON)
    persona_description = Column(String(200))
    additional_inquiry_prompt = Column(String(500))
