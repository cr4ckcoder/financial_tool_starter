from fastapi import APIRouter
from typing import List
from app.schemas.account_schemas import AccountCreate, AccountRead

router = APIRouter()

fake_accounts = []
@router.post("/", response_model=AccountRead)
async def create_account(payload: AccountCreate):
    acc = payload.dict()
    acc.update({"id": len(fake_accounts) + 1})
    fake_accounts.append(acc)
    return acc

@router.get("/")
async def list_accounts():
    return fake_accounts
