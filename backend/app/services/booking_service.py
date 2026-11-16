import uuid
import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.reservation import Reservation
from app.models.shop import Shop, get_active_preset_key, get_preset_config
from app.schemas.dialog import SlotState

class BookingService:
    @classmethod
    def get_or_create_shop(cls, db: Session, preset_key: Optional[str] = None) -> Shop:
        target_preset = preset_key or get_active_preset_key()
        cfg = get_preset_config(target_preset)

        shop = db.query(Shop).first()
        if not shop:
            shop = Shop(
                preset_key=target_preset,
                name=cfg["name"],
                industry_type=cfg["industry_type"],
                address=cfg["address"],
                google_place_id=cfg["google_place_id"],
                total_seats=cfg["total_seats"],
                table_seats=cfg["table_seats"],
                counter_seats=cfg["counter_seats"],
                private_rooms=cfg["private_rooms"],
                open_time=cfg["open_time"],
                close_time=cfg["close_time"],
                persona_description=cfg["persona_description"],
                courses_json=cfg["courses"],
                pre_order_items_json=cfg["pre_orders"],
                faqs_json=cfg["faqs"],
                additional_inquiry_prompt=cfg["additional_inquiry_prompt"]
            )
            db.add(shop)
            db.commit()
            db.refresh(shop)
        elif shop.preset_key != target_preset or not shop.persona_description:
            # プリセット変更時の動的同期
            shop.preset_key = target_preset
            shop.name = cfg["name"]
            shop.industry_type = cfg["industry_type"]
            shop.address = cfg["address"]
            shop.google_place_id = cfg["google_place_id"]
            shop.total_seats = cfg["total_seats"]
            shop.table_seats = cfg["table_seats"]
            shop.counter_seats = cfg["counter_seats"]
            shop.private_rooms = cfg["private_rooms"]
            shop.open_time = cfg["open_time"]
            shop.close_time = cfg["close_time"]
            shop.persona_description = cfg["persona_description"]
            shop.courses_json = cfg["courses"]
            shop.pre_order_items_json = cfg["pre_orders"]
            shop.faqs_json = cfg["faqs"]
            shop.additional_inquiry_prompt = cfg["additional_inquiry_prompt"]
            db.commit()
            db.refresh(shop)
        return shop

    @classmethod
    def check_availability(cls, db: Session, date: str, time: str, guests: int, seat_type: str = "table") -> bool:
        shop = cls.get_or_create_shop(db)
        # 全体席数の確認
        existing_res = db.query(Reservation).filter(
            Reservation.date == date,
            Reservation.time == time,
            Reservation.status != "cancelled"
        ).all()
        current_guests = sum(r.guests for r in existing_res)
        if (current_guests + guests) > shop.total_seats:
            return False

        # 個室指定の場合の個室在庫チェック
        if seat_type == "private":
            private_res = [r for r in existing_res if r.seat_type == "private"]
            current_private_guests = sum(r.guests for r in private_res)
            if (current_private_guests + guests) > shop.private_rooms:
                return False

        return True

    @classmethod
    def check_seat_type_availability(
        cls, db: Session, date: str, time: str, guests: int, requested_seat_type: str
    ) -> Dict[str, Any]:
        """
        特定の席種（特に個室）の空きを判定し、満室だがテーブル席なら空いている場合に
        代替席種（ボックス席・テーブル席）を提案する
        """
        shop = cls.get_or_create_shop(db)
        is_requested_avail = cls.check_availability(db, date, time, guests, seat_type=requested_seat_type)
        if is_requested_avail:
            return {"is_available": True, "suggested_alternative_seat": None}

        # もし個室希望で満室の場合、テーブル席に空きがあるか探索
        if requested_seat_type == "private":
            is_table_avail = cls.check_availability(db, date, time, guests, seat_type="table")
            if is_table_avail:
                return {
                    "is_available": False,
                    "reason": "private_full",
                    "suggested_alternative_seat": "奥の落ち着いたテーブル席（ボックス席）"
                }

        return {"is_available": False, "reason": "full", "suggested_alternative_seat": None}

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

    @classmethod
    def find_reservation_by_name(cls, db: Session, name: str, date: Optional[str] = None) -> Optional[Reservation]:
        """名前（および日付）から既存予約を検索"""
        q = db.query(Reservation).filter(
            Reservation.status != "cancelled",
            Reservation.customer_name.contains(name)
        )
        if date:
            q = q.filter(Reservation.date == date)
        return q.order_by(Reservation.created_at.desc()).first()

    @classmethod
    def cancel_reservation(cls, db: Session, reservation_id: int) -> bool:
        """予約のキャンセル処理"""
        res = db.query(Reservation).filter(Reservation.id == reservation_id).first()
        if res:
            res.status = "cancelled"
            db.commit()
            return True
        return False
