# app/api/signatories.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.dependencies import get_db
from app.models.domain import Signatory, Company
from app.schemas.signatory_schemas import SignatoryCreate, SignatoryRead

router = APIRouter()

@router.post("/", response_model=SignatoryRead)
async def add_signatory(payload: SignatoryCreate, db: AsyncSession = Depends(get_db)):
    # Validate Company exists
    company = await db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    new_signatory = Signatory(
        company_id=payload.company_id,
        name=payload.name,
        designation=payload.designation,
        din_number=payload.din_number,
        pan_number=payload.pan_number,
        is_active=payload.is_active
    )
    db.add(new_signatory)
    await db.commit()
    await db.refresh(new_signatory)
    return new_signatory

@router.get("/{company_id}", response_model=List[SignatoryRead])
async def list_signatories(company_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Signatory).where(Signatory.company_id == company_id))
    return result.scalars().all()