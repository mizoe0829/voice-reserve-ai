import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ReservationResponse(BaseModel):
    id: int
    booking_code: str
    date: Optional[str]
    time: Optional[str]
    guests: int
    seat_type: str
    course_name: str
    customer_name: Optional[str]
    phone_number: Optional[str]
    allergies: List[str]
    pre_orders: List[Dict[str, Any]]
    special_requests: Optional[str]
    status: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
