# app/services/trial_balance_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models.domain import TrialBalanceEntry, FinancialWork, WorkUnit
from app.utils.csv_parser import parse_trial_balance

async def process_trial_balance_upload(
    session: AsyncSession, 
    work_id: int, 
    unit_id: int,
    file_contents: bytes
):
    # 1. Verify Unit belongs to Work
    unit = await session.get(WorkUnit, unit_id)
    if not unit or unit.financial_work_id != work_id:
        raise HTTPException(status_code=404, detail="Work Unit not found")

    # 2. Parse CSV
    parsed_data = parse_trial_balance(file_contents)
    if not parsed_data:
        raise HTTPException(status_code=400, detail="Failed to parse CSV or empty file")

    # 3. Determine New Version Number
    stmt = select(func.max(TrialBalanceEntry.version_number)).where(TrialBalanceEntry.work_unit_id == unit_id)
    result = await session.execute(stmt)
    current_max = result.scalar() or 0
    new_version = current_max + 1
    
    # 4. Bulk Create new entries
    new_entries = [
        TrialBalanceEntry(
            work_unit_id=unit_id,
            version_number=new_version,
            account_name=row['account_name'],
            debit=row['debit'],
            credit=row['credit'],
            closing_balance=row['closing_balance']
        )
        for row in parsed_data
    ]
    
    session.add_all(new_entries)
    await session.commit()
    
    return {
        "status": "success", 
        "entries_processed": len(new_entries), 
        "version": new_version,
        "unit": unit.unit_name
    }

async def get_unit_versions(session: AsyncSession, unit_id: int):
    """Returns a list of available versions for a unit."""
    stmt = (
        select(TrialBalanceEntry.version_number, func.count(TrialBalanceEntry.id))
        .where(TrialBalanceEntry.work_unit_id == unit_id)
        .group_by(TrialBalanceEntry.version_number)
        .order_by(TrialBalanceEntry.version_number.desc())
    )
    result = await session.execute(stmt)
    return [{"version": row[0], "count": row[1]} for row in result.all()]

async def get_tb_totals(session: AsyncSession, work_id: int):
    """Calculates the total Debit/Credit for the LATEST version of all units."""
    # Subquery for max version per unit
    subq = (
        select(
            TrialBalanceEntry.work_unit_id,
            func.max(TrialBalanceEntry.version_number).label("max_ver")
        )
        .join(WorkUnit, TrialBalanceEntry.work_unit_id == WorkUnit.id)
        .where(WorkUnit.financial_work_id == work_id)
        .group_by(TrialBalanceEntry.work_unit_id)
        .subquery()
    )
    
    stmt = (
        select(
            func.sum(TrialBalanceEntry.debit),
            func.sum(TrialBalanceEntry.credit)
        )
        .join(
            subq, 
            (TrialBalanceEntry.work_unit_id == subq.c.work_unit_id) & 
            (TrialBalanceEntry.version_number == subq.c.max_ver)
        )
    )
    
    result = await session.execute(stmt)
    row = result.first()
    
    total_debit = row[0] or 0.0
    total_credit = row[1] or 0.0
    
    return {
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "difference": float(total_debit - total_credit)
    }