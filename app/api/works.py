# app/api/works.py
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import Response  # <--- FIXED: Added this import
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel

from app.core.dependencies import get_db
from app.models.domain import FinancialWork, TrialBalanceEntry
from app.schemas.work_schemas import WorkCreate, WorkRead

# Import Services
from app.services.trial_balance_service import process_trial_balance_upload
from app.services.mapping_service import get_unmapped_entries, map_entry_to_account
from app.services.statement_generation_service import calculate_statement_data
from app.services.report_service import generate_report

router = APIRouter()

# --- Schema for Mapping Request (defined locally for now) ---
class MappingRequest(BaseModel):
    trial_balance_entry_id: int
    account_sub_head_id: int

# --- 1. Basic CRUD Operations ---

@router.post("/", response_model=WorkRead)
async def create_work(payload: WorkCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new Financial Work engagement.
    """
    new_work = FinancialWork(
        company_id=payload.company_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="PENDING"
    )
    db.add(new_work)
    await db.commit()
    await db.refresh(new_work)
    return new_work

@router.get("/{work_id}", response_model=WorkRead)
async def get_work(work_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get details of a specific work.
    """
    result = await db.execute(select(FinancialWork).where(FinancialWork.id == work_id))
    work = result.scalars().first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    return work

# --- 2. Phase 2: Trial Balance Upload ---

@router.post("/{work_id}/trial-balance")
async def upload_trial_balance(
    work_id: int, 
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads and parses the Trial Balance CSV.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
        
    contents = await file.read()
    
    result = await process_trial_balance_upload(
        session=db,
        work_id=work_id,
        file_contents=contents
    )
    
    return result

# --- 3. Phase 3: Mapping Endpoints ---

@router.get("/{work_id}/unmapped-entries")
async def list_unmapped_entries(
    work_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns a list of raw CSV rows that haven't been assigned an account yet.
    """
    entries = await get_unmapped_entries(db, work_id)
    return entries

@router.post("/{work_id}/map-entry")
async def map_entry(
    work_id: int,
    payload: MappingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Maps a raw entry to a standardized account head.
    """
    mapping = await map_entry_to_account(
        session=db,
        trial_balance_entry_id=payload.trial_balance_entry_id,
        account_sub_head_id=payload.account_sub_head_id
    )
    return {"status": "mapped", "mapping_id": mapping.id}

# --- 4. Phase 4: Calculation Endpoint ---

@router.get("/{work_id}/calculate")
async def generate_statement(
    work_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers the calculation engine to aggregate figures.
    """
    data = await calculate_statement_data(db, work_id)
    return {"work_id": work_id, "calculated_balances": data}

# --- 5. Phase 5: Reporting Endpoint ---

@router.get("/{work_id}/statements/{template_id}")
async def download_statement(
    work_id: int, 
    template_id: int, 
    format: str = "pdf",
    db: AsyncSession = Depends(get_db)
):
    """
    Generates and downloads the financial statement.
    Format: 'pdf' or 'xlsx'
    """
    file_bytes, filename = await generate_report(db, work_id, template_id, format)
    
    media_type = "application/pdf" if format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    
    
@router.get("/", response_model=List[WorkRead])
async def list_works(
    company_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all works, optionally filtered by company_id.
    """
    query = select(FinancialWork)
    if company_id:
        query = query.where(FinancialWork.company_id == company_id)
    
    result = await db.execute(query)
    return result.scalars().all()