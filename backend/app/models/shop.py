import os
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

# 親業種（Industry）の定義マスター
INDUSTRY_SEEDS = [
    {
        "code": "restaurant",
        "name": "飲食・レストラン",
        "default_persona": "人気飲食店の親切で優秀なAI音声予約コンシェルジュ",
        "default_inquiry": "ありがとうございます！続いて、ご同席の皆様でアレルギーや苦手な食材はございますか？また、ファーストドリンクや事前にお出しできるお料理のご準備はいかがなさいますか？",
        "default_faqs": {
            "parking": "店舗専用駐車場はございませんが、近隣に提携コインパーキングがございます。",
            "private_room_fee": "個室料・チャージ料は一切いただいておりません（無料です）。",
            "payment": "現金、各種クレジットカード、PayPay等に対応しております。",
            "smoking": "全席完全禁煙となっております。"
        }
    },
    {
        "code": "ryokan",
        "name": "宿泊・温泉旅館",
        "default_persona": "老舗温泉旅館の親切・丁寧なAI宿泊コンシェルジュ",
        "default_inquiry": "ありがとうございます！続いて、ご同伴の皆様でアレルギーや苦手な食材はございますか？また、別注料理やお風呂の手配、駅からの送迎バスなど、事前にご準備しておくご要望はございますでしょうか？",
        "default_faqs": {
            "hotspring": "天然温泉の大浴場および露天風呂を完備しております。",
            "dinner_time": "夕食の最終スタートは19:30となっております。",
            "parking": "敷地内に宿泊者様専用の無料駐車場を完備しております。"
        }
    },
    {
        "code": "clinic",
        "name": "医療・クリニック",
        "default_persona": "地域の皆様に寄り添う親切・丁寧なクリニックのAI予約受付コンシェルジュ",
        "default_inquiry": "承知いたしました！当院は初めて（初診）でいらっしゃいますか？また、麻酔やお薬のアレルギー、服用歴、妊娠中など、事前に医師へ伝えておきたい配慮事項はございますでしょうか？",
        "default_faqs": {
            "first_visit": "初診の方は問診票の記入がございますので、ご予約の15分前までに健康保険証をご持参のうえお越しください。",
            "parking": "提携駐車場が隣接ビルにございます。",
            "payment": "保険診療は現金またはPayPay、自費診療は各種クレジットカードをご利用いただけます。"
        }
    }
]

def get_active_preset_key() -> str:
    """環境変数 SHOP_PRESET で指定された業種コードを取得（デフォルト: restaurant / yakitori互換）"""
    val = os.getenv("SHOP_PRESET", "restaurant")
    if val in ["yakitori", "restaurant"]:
        return "restaurant"
    if val in ["ryokan", "hotel"]:
        return "ryokan"
    if val in ["clinic", "clinic_dental", "dental"]:
        return "clinic"
    return "restaurant"

class Industry(Base):
    """業種（親テーブル）: 飲食、宿泊、クリニック等の共通ルール・ペルソナ雛形を保持"""
    __tablename__ = "industries"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)  # restaurant / ryokan / clinic
    name = Column(String(100))                         # 飲食・レストラン / 宿泊・温泉旅館 / 医療・クリニック
    default_persona_template = Column(String(500))
    default_inquiry_template = Column(String(500))
    default_faqs = Column(JSON)

    # 1対多のリレーション（親: 業種 -> 子: 個別店舗）
    shops = relationship("Shop", back_populates="industry", cascade="all, delete-orphan")

class Shop(Base):
    """個別店舗（子テーブル）: 初期は空設定のテンプレとして生成され、個別名・個別オプションをリレーションで管理"""
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    industry_id = Column(Integer, ForeignKey("industries.id"), nullable=True, index=True)
    industry_code = Column(String(50), default="restaurant", index=True)
    
    # 店舗名（初期は空設定のテンプレ）
    name = Column(String(100), default="")
    address = Column(String(200), default="")
    google_place_id = Column(String(100), default="")
    
    # 席数・客室数在庫
    total_seats = Column(Integer, default=40)
    table_seats = Column(Integer, default=24)
    counter_seats = Column(Integer, default=8)
    private_rooms = Column(Integer, default=8)

    # 営業時間 / チェックイン時間
    open_time = Column(String(10), default="17:00")
    close_time = Column(String(10), default="23:30")
    
    # 個別設定（初期は空配列/空辞書で、DB側で管理・登録）
    courses_json = Column(JSON, default=list)
    pre_order_items_json = Column(JSON, default=list)
    faqs_json = Column(JSON, default=dict)
    
    # 個別店舗で上書き可能なプロンプト（未設定なら親Industryの雛形を継承）
    custom_persona_description = Column(String(500), nullable=True)
    custom_additional_inquiry_prompt = Column(String(500), nullable=True)

    # 親業種へのリレーション
    industry = relationship("Industry", back_populates="shops")

    @property
    def industry_type(self) -> str:
        if self.industry:
            return self.industry.code
        return self.industry_code or "restaurant"

    @property
    def persona_description(self) -> str:
        if self.custom_persona_description:
            return self.custom_persona_description
        if self.industry and self.industry.default_persona_template:
            return self.industry.default_persona_template
        return "親切で優秀なAI音声予約コンシェルジュ"

    @property
    def additional_inquiry_prompt(self) -> str:
        if self.custom_additional_inquiry_prompt:
            return self.custom_additional_inquiry_prompt
        if self.industry and self.industry.default_inquiry_template:
            return self.industry.default_inquiry_template
        return "ありがとうございます！続いて、ご同伴の皆様でアレルギーや苦手な食材、または事前にご準備しておくご要望はございますでしょうか？"

