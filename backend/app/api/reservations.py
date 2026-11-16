from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.reservation import ReservationResponse
from app.services.booking_service import BookingService

router = APIRouter()

@router.get("/reservations", response_model=List[ReservationResponse])
def get_reservations(db: Session = Depends(get_db)):
    """予約台帳一覧を返す（店舗管理画面カレンダー・厨房伝票用）"""
    return BookingService.get_all_reservations(db)

@router.get("/reservations/{booking_code}", response_model=ReservationResponse)
def get_reservation_detail(booking_code: str, db: Session = Depends(get_db)):
    """予約番号による詳細取得"""
    res = BookingService.get_reservation_by_code(db, booking_code)
    if not res:
        raise HTTPException(status_code=404, detail="予約が見つかりません。")
    return res
