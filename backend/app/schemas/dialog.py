from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class SlotState(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    guests: Optional[int] = None
    seat_type: Optional[str] = None
    course_name: Optional[str] = None
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    allergies: List[str] = []
    pre_orders: List[Dict[str, Any]] = []
    special_requests: Optional[str] = None

class DialogueRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    current_slots: Optional[SlotState] = None
    stage: str = "hearing"  # hearing, confirming, additional_inquiry, completed

class DialogueResponse(BaseModel):
    reply_text: str
    updated_slots: SlotState
    stage: str
    is_confirmed: bool = False
    booking_code: Optional[str] = None
    is_slot_available: bool = True
    alternative_slots: List[str] = []
