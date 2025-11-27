from pydantic import BaseModel
from typing import Optional

class CompanyCreate(BaseModel):
    legal_name: str
    cin: Optional[str] = None
    registered_address: Optional[str] = None

class CompanyRead(CompanyCreate):
    id: int
