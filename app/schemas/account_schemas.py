from pydantic import BaseModel
from typing import Optional

class AccountCreate(BaseModel):
    name: str
    type: str
    category_type: str
    parent_id: Optional[int] = None

class AccountRead(AccountCreate):
    id: int
