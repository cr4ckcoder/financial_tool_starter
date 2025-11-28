# app/services/trial_balance_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
from app.models.domain import TrialBalanceEntry, FinancialWork
from app.utils.csv_parser import parse_trial_balance

async def process_trial_balance_upload(
    session: AsyncSession, 
    work_id: int, 
    file_contents: bytes
):
    # 1. Verify Work exists
    result = await session.execute(select(FinancialWork).where(FinancialWork.id == work_id))
    work = result.scalars().first()
    if not work:
        raise HTTPException(status_code=404, detail="Financial Work not found")

    # 2. Parse CSV
    parsed_data = parse_trial_balance(file_contents)
    if not parsed_data:
        raise HTTPException(status_code=400, detail="Failed to parse CSV or empty file")

    # 3. Clear existing entries for this work (if re-uploading)
    existing_entries = await session.execute(
        select(TrialBalanceEntry).where(TrialBalanceEntry.financial_work_id == work_id)
    )
    for entry in existing_entries.scalars():
        await session.delete(entry)
    
    # 4. Bulk Create new entries
    new_entries = [
        TrialBalanceEntry(
            financial_work_id=work_id,
            account_name=row['account_name'],
            debit=row['debit'],
            credit=row['credit'],
            closing_balance=row['closing_balance']
        )
        for row in parsed_data
    ]
    
    session.add_all(new_entries)
    await session.commit()
    
    return {"status": "success", "entries_processed": len(new_entries)}