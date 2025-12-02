# app/services/mapping_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from fastapi import HTTPException
from app.models.domain import TrialBalanceEntry, MappedLedgerEntry, Account, AccountType, WorkUnit

async def get_unmapped_entries(session: AsyncSession, work_id: int):
    """
    Fetch unmapped entries for the LATEST version of ALL units in a work.
    """
    
    # 1. Subquery to find max version per unit
    # SELECT work_unit_id, MAX(version_number) FROM entries JOIN units WHERE work_id = X GROUP BY unit_id
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

    # 2. Main Query: Entries matching that Unit+Version, AND unmapped
    query = (
        select(TrialBalanceEntry)
        .join(
            subq, 
            and_(
                TrialBalanceEntry.work_unit_id == subq.c.work_unit_id,
                TrialBalanceEntry.version_number == subq.c.max_ver
            )
        )
        .outerjoin(MappedLedgerEntry, TrialBalanceEntry.id == MappedLedgerEntry.trial_balance_entry_id)
        .where(MappedLedgerEntry.id.is_(None))
    )
    
    result = await session.execute(query)
    return result.scalars().all()

async def map_entry_to_account(
    session: AsyncSession, 
    trial_balance_entry_id: int, 
    account_sub_head_id: int
):
    # Validate Accounts...
    account_query = select(Account).where(Account.id == account_sub_head_id)
    result = await session.execute(account_query)
    account = result.scalars().first()
    
    if not account or account.type != AccountType.SUB_HEAD:
        raise HTTPException(status_code=400, detail="Invalid Account")

    # Validate Entry
    entry = await session.get(TrialBalanceEntry, trial_balance_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Check existing
    existing = await session.execute(select(MappedLedgerEntry).where(MappedLedgerEntry.trial_balance_entry_id == trial_balance_entry_id))
    mapping = existing.scalars().first()

    if mapping:
        mapping.account_sub_head_id = account_sub_head_id
        return mapping
    else:
        new_mapping = MappedLedgerEntry(
            trial_balance_entry_id=trial_balance_entry_id,
            account_sub_head_id=account_sub_head_id
        )
        session.add(new_mapping)
        await session.commit()
        await session.refresh(new_mapping)
        return new_mapping