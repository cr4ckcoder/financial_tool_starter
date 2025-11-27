from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.company_schemas import CompanyCreate, CompanyRead

router = APIRouter()

# In-memory store for starter
fake_db = {}

@router.post("/", response_model=CompanyRead)
async def create_company(payload: CompanyCreate):
    cid = len(fake_db) + 1
    data = payload.dict()
    data.update({"id": cid})
    fake_db[cid] = data
    return data

@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(company_id: int):
    c = fake_db.get(company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return c
