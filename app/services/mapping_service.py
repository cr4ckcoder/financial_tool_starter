# app/services/mapping_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException
from app.models.domain import TrialBalanceEntry, MappedLedgerEntry, Account, AccountType

async def get_unmapped_entries(session: AsyncSession, work_id: int):
    # This query finds entries where the JOIN to MappedLedgerEntry is NULL
    query = (
        select(TrialBalanceEntry)
        .outerjoin(MappedLedgerEntry, TrialBalanceEntry.id == MappedLedgerEntry.trial_balance_entry_id)
        .where(
            and_(
                TrialBalanceEntry.financial_work_id == work_id,
                MappedLedgerEntry.id.is_(None)  # <--- This line is critical
            )
        )
    )
    result = await session.execute(query)
    return result.scalars().all()

async def map_entry_to_account(
    session: AsyncSession, 
    trial_balance_entry_id: int, 
    account_sub_head_id: int
):
    """
    Creates a link between a raw TB entry and a standardized Account Sub-Head.
    """
    # 1. Validate the Target Account
    account_query = select(Account).where(Account.id == account_sub_head_id)
    result = await session.execute(account_query)
    account = result.scalars().first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Target account not found")
    
    if account.type != AccountType.SUB_HEAD:
        raise HTTPException(status_code=400, detail="Entries can only be mapped to SUB_HEAD accounts")

    # 2. Validate the Source Entry
    entry_query = select(TrialBalanceEntry).where(TrialBalanceEntry.id == trial_balance_entry_id)
    result = await session.execute(entry_query)
    entry = result.scalars().first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Trial Balance entry not found")

    # 3. Create or Update Mapping
    existing_mapping_query = select(MappedLedgerEntry).where(
        MappedLedgerEntry.trial_balance_entry_id == trial_balance_entry_id
    )
    result = await session.execute(existing_mapping_query)
    existing_mapping = result.scalars().first()

    if existing_mapping:
        existing_mapping.account_sub_head_id = account_sub_head_id
        return existing_mapping
    else:
        new_mapping = MappedLedgerEntry(
            trial_balance_entry_id=trial_balance_entry_id,
            account_sub_head_id=account_sub_head_id
        )
        session.add(new_mapping)
        await session.commit()
        await session.refresh(new_mapping)
        return new_mapping