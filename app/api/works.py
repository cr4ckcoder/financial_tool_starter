# app/api/works.py
import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.core.dependencies import get_db, get_current_user
from app.models.domain import FinancialWork, TrialBalanceEntry, WorkUnit, User, WorkStatus
from app.services.trial_balance_service import process_trial_balance_upload
from app.services.mapping_service import get_unmapped_entries, map_entry_to_account
from app.services.report_service import generate_report, get_report_data
from app.utils.validators import validate_udin

from app.services.trial_balance_service import process_trial_balance_upload, get_unit_versions, get_tb_totals # <--- Updated Import
from app.services.statement_generation_service import calculate_statement_data # <--- Need this for BS Validation


router = APIRouter()

# --- Schemas ---
class WorkCreate(BaseModel):
    company_id: int
    start_date: str 
    end_date: str

class UnitCreate(BaseModel):
    unit_name: str

class WorkRead(BaseModel):
    id: int
    company_id: int
    start_date: str
    end_date: str
    status: str
    udin_number: Optional[str] = None
    signing_date: Optional[str] = None
    units: List[dict] = []
    class Config:
        from_attributes = True

class MappingRequest(BaseModel):
    trial_balance_entry_id: int
    account_sub_head_id: int

# --- 1. Work Management ---

@router.post("/", response_model=WorkRead)
async def create_work(
    payload: WorkCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_work = FinancialWork(
        company_id=payload.company_id,
        start_date=datetime.strptime(payload.start_date, "%Y-%m-%d").date(),
        end_date=datetime.strptime(payload.end_date, "%Y-%m-%d").date(),
        status=WorkStatus.DRAFT.value
    )
    db.add(new_work)
    await db.flush() 

    default_unit = WorkUnit(financial_work_id=new_work.id, unit_name="Main")
    db.add(default_unit)
    
    await db.commit()
    await db.refresh(new_work)
    
    return WorkRead(
        id=new_work.id,
        company_id=new_work.company_id,
        start_date=str(new_work.start_date),
        end_date=str(new_work.end_date),
        status=new_work.status,
        units=[{"id": default_unit.id, "unit_name": default_unit.unit_name}]
    )

@router.get("/", response_model=List[WorkRead])
async def list_works(
    company_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(FinancialWork).options(selectinload(FinancialWork.units))
    if company_id:
        query = query.where(FinancialWork.company_id == company_id)
    
    result = await db.execute(query)
    works = result.scalars().all()
    
    return [
        WorkRead(
            id=w.id, company_id=w.company_id, 
            start_date=str(w.start_date), end_date=str(w.end_date), 
            status=w.status,
            udin_number=w.udin_number,
            signing_date=str(w.signing_date) if w.signing_date else None,
            units=[{"id": u.id, "unit_name": u.unit_name} for u in w.units]
        ) for w in works
    ]

@router.get("/{work_id}", response_model=WorkRead)
async def get_work(
    work_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(FinancialWork).options(selectinload(FinancialWork.units)).where(FinancialWork.id == work_id)
    result = await db.execute(query)
    work = result.scalars().first()
    
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
        
    return WorkRead(
        id=work.id,
        company_id=work.company_id,
        start_date=str(work.start_date),
        end_date=str(work.end_date),
        status=work.status,
        udin_number=work.udin_number,
        signing_date=str(work.signing_date) if work.signing_date else None,
        units=[{"id": u.id, "unit_name": u.unit_name} for u in work.units]
    )

@router.post("/{work_id}/units")
async def create_unit(
    work_id: int,
    payload: UnitCreate,
    db: AsyncSession = Depends(get_db)
):
    work = await db.get(FinancialWork, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
        
    new_unit = WorkUnit(financial_work_id=work_id, unit_name=payload.unit_name)
    db.add(new_unit)
    await db.commit()
    return {"status": "success", "unit_id": new_unit.id}

# --- 2. Versioned Upload ---

@router.post("/{work_id}/units/{unit_id}/trial-balance")
async def upload_trial_balance(
    work_id: int,
    unit_id: int,
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
        
    contents = await file.read()
    
    result = await process_trial_balance_upload(
        session=db,
        work_id=work_id,
        unit_id=unit_id,
        file_contents=contents
    )
    
    return result

# --- 3. Mapping & Reports ---

@router.get("/{work_id}/unmapped-entries")
async def list_unmapped_entries(
    work_id: int,
    db: AsyncSession = Depends(get_db)
):
    entries = await get_unmapped_entries(db, work_id)
    return entries

@router.post("/{work_id}/map-entry")
async def map_entry(
    work_id: int,
    payload: MappingRequest,
    db: AsyncSession = Depends(get_db)
):
    mapping = await map_entry_to_account(
        session=db,
        trial_balance_entry_id=payload.trial_balance_entry_id,
        account_sub_head_id=payload.account_sub_head_id
    )
    return {"status": "mapped", "mapping_id": mapping.id}

@router.get("/{work_id}/preview/{template_id}")
async def preview_statement(
    work_id: int, 
    template_id: int, 
    db: AsyncSession = Depends(get_db)
):
    data = await get_report_data(db, work_id, template_id)
    # Note: Pydantic serialization for complex objects skipped for brevity
    return {
        "company_name": data['company'].legal_name,
        "template_def": data['template_def'],
        "balances": data['balances'],
        "notes_data": data['notes_data'],
        "note_map": data['note_map']
    }

@router.get("/{work_id}/statements/{template_id}")
async def download_statement(
    work_id: int, 
    template_id: int, 
    format: str = "pdf",
    db: AsyncSession = Depends(get_db)
):
    file_bytes, filename = await generate_report(db, work_id, template_id, format)
    media_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- 4. Finalization & Compliance (NEW) ---

@router.post("/{work_id}/finalize")
async def finalize_work(
    work_id: int,
    udin: str = Form(...),
    signing_date: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Validate Work
    work = await db.get(FinancialWork, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    # 2. Validate UDIN Format
    if not validate_udin(udin):
        raise HTTPException(status_code=400, detail="Invalid UDIN format. Must be 18 characters.")
        
    # 3. Save Certificate
    upload_dir = "/app/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = f"{upload_dir}/{work_id}_{file.filename}"
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
        
    # 4. Update Work Status
    work.udin_number = udin
    work.signing_date = datetime.strptime(signing_date, "%Y-%m-%d").date()
    work.udin_certificate_url = file_location
    work.status = WorkStatus.FINALIZED.value
    
    await db.commit()
    return {"status": "success", "work_status": "FINALIZED"}


@router.get("/{work_id}/units/{unit_id}/versions")
async def list_versions(
    work_id: int,
    unit_id: int,
    db: AsyncSession = Depends(get_db)
):
    """List all upload versions for a specific unit"""
    return await get_unit_versions(db, unit_id)

@router.get("/{work_id}/validation-stats")
async def get_validation_stats(
    work_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns:
    1. TB Tally Status (Debit vs Credit)
    2. BS Tally Status (Assets vs Equity+Liab)
    """
    # 1. TB Validation
    tb_stats = await get_tb_totals(db, work_id)
    
    # 2. Balance Sheet Validation
    # We use the calculation engine to get the totals
    balances, _, _ = await calculate_statement_data(db, work_id)
    
    # Calculate derived totals manually here to check matching
    # Categories: 1=ASSET, 61=LIABILITY, 81=EQUITY
    total_assets = balances.get(1, 0.0)
    total_liabilities = balances.get(61, 0.0)
    total_equity = balances.get(81, 0.0)
    
    # In accounting: Assets = Liabilities + Equity
    # In our DB signs: Assets (+), Liab (-), Equity (-)
    # So: Assets + Liab + Equity should be 0
    bs_diff = total_assets + total_liabilities + total_equity
    
    return {
        "tb": tb_stats,
        "bs": {
            "total_assets": total_assets,
            "total_equity_liab": abs(total_liabilities + total_equity),
            "difference": bs_diff
        }
    }