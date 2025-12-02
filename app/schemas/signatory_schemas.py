# app/schemas/signatory_schemas.py
from pydantic import BaseModel
from typing import Optional

class SignatoryCreate(BaseModel):
    company_id: int
    name: str
    designation: str
    din_number: Optional[str] = None
    pan_number: Optional[str] = None
    is_active: bool = True

class SignatoryRead(SignatoryCreate):
    id: int
    
    class Config:
        from_attributes = True