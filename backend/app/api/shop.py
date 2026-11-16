from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.booking_service import BookingService
from app.models.shop import Shop

router = APIRouter()

class ShopUpdateRequest(BaseModel):
    name: Optional[str] = None
    industry_type: Optional[str] = None
    address: Optional[str] = None
    google_place_id: Optional[str] = None
    total_seats: Optional[int] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    persona_description: Optional[str] = None
    courses: Optional[List[Dict[str, Any]]] = None
    pre_order_items: Optional[List[Dict[str, Any]]] = None
    faqs: Optional[Dict[str, str]] = None
    additional_inquiry_prompt: Optional[str] = None

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
        "persona_description": shop.persona_description,
        "courses": shop.courses_json,
        "pre_order_items": shop.pre_order_items_json,
        "faqs": shop.faqs_json,
        "additional_inquiry_prompt": shop.additional_inquiry_prompt
    }

@router.put("/shop")
def update_shop_info(req: ShopUpdateRequest, db: Session = Depends(get_db)):
    """DB側の店舗・施設設定（名前、オプション、プランなど）を更新"""
    shop = BookingService.get_or_create_shop(db)
    if req.name is not None:
        shop.name = req.name
    if req.industry_type is not None:
        shop.industry_type = req.industry_type
    if req.address is not None:
        shop.address = req.address
    if req.google_place_id is not None:
        shop.google_place_id = req.google_place_id
    if req.total_seats is not None:
        shop.total_seats = req.total_seats
    if req.open_time is not None:
        shop.open_time = req.open_time
    if req.close_time is not None:
        shop.close_time = req.close_time
    if req.persona_description is not None:
        shop.persona_description = req.persona_description
    if req.courses is not None:
        shop.courses_json = req.courses
    if req.pre_order_items is not None:
        shop.pre_order_items_json = req.pre_order_items
    if req.faqs is not None:
        shop.faqs_json = req.faqs
    if req.additional_inquiry_prompt is not None:
        shop.additional_inquiry_prompt = req.additional_inquiry_prompt

    db.commit()
    db.refresh(shop)
    return {
        "id": shop.id,
        "name": shop.name,
        "industry_type": shop.industry_type,
        "address": shop.address,
        "courses": shop.courses_json,
        "pre_order_items": shop.pre_order_items_json
    }

