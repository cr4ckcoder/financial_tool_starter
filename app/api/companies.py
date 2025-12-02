# app/api/companies.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.dependencies import get_db, get_current_user
from app.models.domain import Company, User, UserRole
from app.schemas.company_schemas import CompanyCreate, CompanyRead
from app.utils.default_compliance_templates import DEFAULT_TEMPLATES # <--- Import

router = APIRouter()

@router.post("/", response_model=CompanyRead)
async def create_company(
    payload: CompanyCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Only Admin can create companies
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=403, detail="Only Admins can create companies")

    # Check for duplicate name
    existing = await db.execute(select(Company).where(Company.legal_name == payload.legal_name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Company with this name already exists")

    new_company = Company(
        legal_name=payload.legal_name,
        client_type=payload.client_type,
        cin=payload.cin,
        pan=payload.pan,
        tan=payload.tan,
        gstin=payload.gstin,
        file_number=payload.file_number,
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
        # RBAC: Return only assigned companies
        return current_user.assigned_companies

@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # RBAC Check
    if current_user.role == UserRole.STAFF.value:
        assigned_ids = [c.id for c in current_user.assigned_companies]
        if company.id not in assigned_ids:
            raise HTTPException(status_code=403, detail="Access denied to this company")

    return company

# --- NEW SEED ENDPOINT ---
@router.post("/seed-defaults")
async def seed_default_templates(db: AsyncSession = Depends(get_db)):
    """
    Loads standard CA compliance templates (Engagement Letter, Consent, etc.)
    into the database.
    """
    count = 0
    for tmpl_data in DEFAULT_TEMPLATES:
        # Check if exists
        result = await db.execute(select(ComplianceTemplate).where(ComplianceTemplate.name == tmpl_data["name"]))
        existing = result.scalars().first()
        
        if not existing:
            new_tmpl = ComplianceTemplate(
                name=tmpl_data["name"],
                content_html=tmpl_data["content"]
            )
            db.add(new_tmpl)
            count += 1
            
    await db.commit()
    return {"status": "success", "templates_added": count}