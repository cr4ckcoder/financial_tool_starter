from pydantic import BaseModel
from typing import Optional
from datetime import date

class WorkCreate(BaseModel):
    company_id: int
    start_date: date
    end_date: date

class WorkRead(WorkCreate):
    id: int
    status: Optional[str] = "PENDING"
