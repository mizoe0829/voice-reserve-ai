from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.booking_service import BookingService

router = APIRouter()

@router.get("/shop")
def get_shop_info(db: Session = Depends(get_db)):
    """店舗マスタ情報・コース一覧・事前注文メニューを返す"""
    shop = BookingService.get_or_create_shop(db)
    return {
        "id": shop.id,
        "name": shop.name,
        "industry_type": shop.industry_type,
        "address": shop.address,
        "google_place_id": shop.google_place_id,
        "total_seats": shop.total_seats,
        "open_time": shop.open_time,
        "close_time": shop.close_time,
        "courses": shop.courses_json,
        "pre_order_items": shop.pre_order_items_json
    }
