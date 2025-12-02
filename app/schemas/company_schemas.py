# app/schemas/company_schemas.py
from pydantic import BaseModel
from typing import Optional, List

class CompanyCreate(BaseModel):
    legal_name: str
    client_type: str = "PVT_LTD" # Default
    cin: Optional[str] = None
    pan: Optional[str] = None
    tan: Optional[str] = None
    gstin: Optional[str] = None
    file_number: Optional[str] = None
    registered_address: Optional[str] = None

class CompanyRead(CompanyCreate):
    id: int
    
    class Config:
        from_attributes = True