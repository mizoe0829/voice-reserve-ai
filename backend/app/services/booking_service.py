import uuid
import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.reservation import Reservation
from app.models.shop import Shop, DEFAULT_COURSES, DEFAULT_PRE_ORDERS
from app.schemas.dialog import SlotState

class BookingService:
    @classmethod
    def get_or_create_shop(cls, db: Session) -> Shop:
        shop = db.query(Shop).first()
        if not shop:
            shop = Shop(courses_json=DEFAULT_COURSES, pre_order_items_json=DEFAULT_PRE_ORDERS)
            db.add(shop)
            db.commit()
            db.refresh(shop)
        elif not shop.pre_order_items_json:
            shop.pre_order_items_json = DEFAULT_PRE_ORDERS
            db.commit()
            db.refresh(shop)
        return shop

    @classmethod
    def check_availability(cls, db: Session, date: str, time: str, guests: int) -> bool:
        shop = cls.get_or_create_shop(db)
        # 同日同時刻の合計予約人数
        existing_res = db.query(Reservation).filter(
            Reservation.date == date,
            Reservation.time == time,
            Reservation.status != "cancelled"
        ).all()
        current_guests = sum(r.guests for r in existing_res)
        return (current_guests + guests) <= shop.total_seats

    @classmethod
    def save_or_update_reservation(
        cls,
        db: Session,
        slots: SlotState,
        booking_code: Optional[str] = None,
        status: str = "confirmed"
    ) -> Reservation:
        if booking_code:
            res = db.query(Reservation).filter(Reservation.booking_code == booking_code).first()
        else:
            res = None

        if not res:
            new_code = f"RSV-{uuid.uuid4().hex[:6].upper()}"
            res = Reservation(booking_code=new_code)
            db.add(res)

        res.date = slots.date or datetime.date.today().isoformat()
        res.time = slots.time or "19:00"
        res.guests = slots.guests or 2
        res.seat_type = slots.seat_type or "table"
        res.course_name = slots.course_name or "お席のみのご予約（アラカルト注文）"
        res.customer_name = slots.customer_name or "お客様"
        res.phone_number = slots.phone_number or "未登録"
        res.allergies = slots.allergies or []
        res.pre_orders = slots.pre_orders or []
        res.special_requests = slots.special_requests
        res.status = status

        db.commit()
        db.refresh(res)
        return res

    @classmethod
    def get_all_reservations(cls, db: Session) -> List[Reservation]:
        return db.query(Reservation).order_by(Reservation.created_at.desc()).all()

    @classmethod
    def get_reservation_by_code(cls, db: Session, booking_code: str) -> Optional[Reservation]:
        return db.query(Reservation).filter(Reservation.booking_code == booking_code).first()
