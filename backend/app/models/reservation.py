import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.core.database import Base

class Reservation(Base):
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    booking_code = Column(String(20), unique=True, index=True)
    
    # 基本予約スロット
    date = Column(String(20), nullable=True)         # 例: 2026-11-20
    time = Column(String(10), nullable=True)         # 例: 19:00
    guests = Column(Integer, default=2)             # 人数
    seat_type = Column(String(50), default="table")  # table, counter, private, any
    course_name = Column(String(100), default="お席のみのご予約（アラカルト注文）")
    
    # 連絡先
    customer_name = Column(String(100), nullable=True)
    phone_number = Column(String(50), nullable=True)

    # アディショナルスロット（要望・アレルギー・事前注文）
    allergies = Column(JSON, default=list)       # 例: ["甲殻類 (1名)", "そばアレルギー"]
    pre_orders = Column(JSON, default=list)      # 例: [{"name": "生ビール", "quantity": 3}, {"name": "月見つくね", "quantity": 3}]
    special_requests = Column(Text, nullable=True)

    # 進行ステータス
    # hearing (ヒアリング中) -> confirmed (基本確定) -> completed (アレルギー・事前注文含め完了)
    status = Column(String(30), default="hearing")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
