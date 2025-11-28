# app/schemas/user_schemas.py
from pydantic import BaseModel
from typing import List, Optional

# Minimal company info for nesting
class CompanyLink(BaseModel):
    id: int
    legal_name: str
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role: str = "STAFF"

class UserRead(UserBase):
    id: int
    role: str
    # New field to show permissions
    assigned_companies: List[CompanyLink] = []
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    role: str

class AssignCompanyRequest(BaseModel):
    user_id: int
    company_id: int