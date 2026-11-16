from sqlalchemy import Column, Integer, String, JSON
from app.core.database import Base

DEFAULT_COURSES = [
    {"id": "course_nomi", "name": "2時間飲み放題付き 極み炭火焼鳥コース", "price": 5000, "description": "名物つくね、希少部位5種、飲み放題付き定番人気"},
    {"id": "course_zeitaku", "name": "鳥神特選 贅沢地鶏フルコース", "price": 7000, "description": "名古屋コーチン水炊き鍋と特選串の豪華プラン"},
    {"id": "seat_only", "name": "お席のみのご予約（アラカルト注文）", "price": 0, "description": "当日お好きな料理・ドリンクをご注文ください"}
]

# 安全＆安心の焼き鳥屋・王道メニュー
DEFAULT_PRE_ORDERS = [
    {"id": "drink_beer", "name": "生ビール（プレミアムモルツ）", "category": "drink", "price": 600},
    {"id": "drink_highball", "name": "角ハイボール", "category": "drink", "price": 550},
    {"id": "drink_lemon", "name": "特製生搾りレモンサワー", "category": "drink", "price": 580},
    {"id": "drink_oolong", "name": "ウーロン茶（ソフトドリンク）", "category": "drink", "price": 400},
    {"id": "food_kushimori", "name": "職人おまかせ炭火串焼き5種盛り合わせ", "category": "food", "price": 1180, "description": "炭火で香ばしく焼き上げてお出しします"},
    {"id": "food_tsukune", "name": "名物・月見つくね串（本数指定）", "category": "food", "price": 380, "description": "秘伝タレと濃厚卵黄の看板串"},
    {"id": "food_karaage", "name": "秘伝醤油仕込み 若鶏のジューシー唐揚げ", "category": "food", "price": 780, "description": "外はカリッと中はジューシーな熱々唐揚げ"},
    {"id": "food_edamame", "name": "スピードおつまみ 茶豆の枝豆", "category": "food", "price": 450, "description": "着席と同時にすぐ乾杯できるスピード前菜"},
    {"id": "food_birthday_plate", "name": "特製バースデーデザートプレート（花火・メッセージ付き）", "category": "food", "price": 1500, "description": "記念日・誕生日サプライズ演出用プレート"}
]

# 店舗FAQ知識
DEFAULT_FAQS = {
    "parking": "店舗裏手に提携コインパーキングが2台分ございます。ご利用のお客様にはお会計時に1時間無料サービス券をお渡ししております。",
    "private_room_fee": "個室料・チャージ料は一切いただいておりません。ご安心ください。",
    "payment": "現金、各種クレジットカード（VISA/Master/JCB/Amex等）、およびPayPayなどのQRコード決済に対応しております。",
    "smoking": "全席完全禁煙となっております（店舗の外に喫煙スペースを設けております）。",
    "invoice": "インボイス制度（適格請求書）に対応した領収書の発行が可能です。"
}

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="炭火焼鳥 鳥神（とりじん） 渋谷本店")
    industry_type = Column(String(50), default="restaurant")
    address = Column(String(200), default="東京都渋谷区道玄坂1-2-3")
    google_place_id = Column(String(100), default="ChIJ_wom9f2LGGAR79K1XqQ")
    
    # 席数在庫
    total_seats = Column(Integer, default=40)
    table_seats = Column(Integer, default=24)
    counter_seats = Column(Integer, default=8)
    private_rooms = Column(Integer, default=8)

    # 営業時間
    open_time = Column(String(10), default="17:00")
    close_time = Column(String(10), default="23:30")
    
    courses_json = Column(JSON, default=DEFAULT_COURSES)
    pre_order_items_json = Column(JSON, default=DEFAULT_PRE_ORDERS)
