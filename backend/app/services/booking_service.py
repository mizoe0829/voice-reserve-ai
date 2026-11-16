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
    def check_availability_and_find_alternatives(
        cls, db: Session, date: str, time: str, guests: int
    ) -> Dict[str, Any]:
        """
        指定枠の空席を判定し、満枠の場合は同日の近傍時間枠および翌日の同時間枠から
        案内可能な代替枠（候補リスト）を自動算出する
        """
        is_avail = cls.check_availability(db, date, time, guests)
        if is_avail:
            return {"is_available": True, "alternatives": []}

        # 満枠時の代替候補探索
        alternatives = []
        candidate_times = [
            "17:00", "17:30", "18:00", "18:30",
            "19:00", "19:30", "20:00", "20:30", "21:00", "21:30"
        ]

        # 同日の近傍時間枠を探索（希望時間に近い順）
        if time in candidate_times:
            idx = candidate_times.index(time)
            # 前後1枠〜3枠を順に探索
            offsets = [1, -1, 2, -2, 3, -3]
            for offset in offsets:
                cand_idx = idx + offset
                if 0 <= cand_idx < len(candidate_times):
                    cand_time = candidate_times[cand_idx]
                    if cls.check_availability(db, date, cand_time, guests):
                        alternatives.append(f"同日 {cand_time}")
                        if len(alternatives) >= 2:
                            break
        else:
            for cand_time in candidate_times:
                if cls.check_availability(db, date, cand_time, guests):
                    alternatives.append(f"同日 {cand_time}")
                    if len(alternatives) >= 2:
                        break

        # 翌日の同一時間枠を探索
        try:
            curr_d = datetime.date.fromisoformat(date)
            next_d = curr_d + datetime.timedelta(days=1)
            next_d_str = next_d.isoformat()
            if cls.check_availability(db, next_d_str, time, guests):
                alternatives.append(f"翌日 {time}")
        except Exception:
            pass

        return {
            "is_available": False,
            "alternatives": alternatives
        }

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
