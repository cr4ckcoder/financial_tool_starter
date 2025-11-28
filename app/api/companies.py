# app/api/companies.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.domain import Company, User, UserRole
from app.schemas.company_schemas import CompanyCreate, CompanyRead

router = APIRouter()

@router.post("/", response_model=CompanyRead)
async def create_company(
    payload: CompanyCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only Admins can create companies")

    existing = await db.execute(select(Company).where(Company.legal_name == payload.legal_name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Company with this name already exists")

    new_company = Company(
        legal_name=payload.legal_name,
        cin=payload.cin,
        registered_address=payload.registered_address
    )
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)
    return new_company

@router.get("/", response_model=List[CompanyRead])
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.ADMIN.value:
        result = await db.execute(select(Company))
        return result.scalars().all()
    else:
        return current_user.assigned_companies

@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Fetch Company
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # 2. RBAC Check (If Staff, ensure they are assigned)
    if current_user.role == UserRole.STAFF.value:
        assigned_ids = [c.id for c in current_user.assigned_companies]
        if company.id not in assigned_ids:
            raise HTTPException(status_code=403, detail="Access denied to this company")

    return company