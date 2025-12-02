# app/services/statement_generation_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, List, Tuple
from app.models.domain import Account, MappedLedgerEntry, TrialBalanceEntry, WorkUnit

async def calculate_statement_data(
    session: AsyncSession, 
    work_id: int
) -> Tuple[Dict[int, float], Dict[int, Account], Dict[int, List[int]]]:
    
    # 1. Fetch Accounts & Hierarchy (Cached)
    all_accounts = (await session.execute(select(Account))).scalars().all()
    account_map = {acc.id: acc for acc in all_accounts}
    children_map: Dict[int, List[int]] = {}
    for acc in all_accounts:
        if acc.parent_id:
            children_map.setdefault(acc.parent_id, []).append(acc.id)
    
    balances: Dict[int, float] = {acc.id: 0.0 for acc in all_accounts}

    # 2. Identify Latest Versions for this Work
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

    # 3. Aggregate Data (Consolidated)
    stmt = (
        select(
            MappedLedgerEntry.account_sub_head_id, 
            func.sum(TrialBalanceEntry.closing_balance)
        )
        .join(TrialBalanceEntry, MappedLedgerEntry.trial_balance_entry_id == TrialBalanceEntry.id)
        .join(
            subq, 
            and_(
                TrialBalanceEntry.work_unit_id == subq.c.work_unit_id,
                TrialBalanceEntry.version_number == subq.c.max_ver
            )
        )
        .group_by(MappedLedgerEntry.account_sub_head_id)
    )
    
    results = await session.execute(stmt)
    
    for account_id, total in results.all():
        if account_id in balances:
            balances[account_id] = float(total)

    # 4. Roll up
    final_balances = {}
    def get_balance(acc_id: int) -> float:
        if acc_id in final_balances: return final_balances[acc_id]
        total = balances.get(acc_id, 0.0)
        if acc_id in children_map:
            for child_id in children_map[acc_id]:
                total += get_balance(child_id)
        final_balances[acc_id] = total
        return total

    root_accounts = [acc for acc in all_accounts if acc.parent_id is None]
    for root in root_accounts:
        get_balance(root.id)
        
    return final_balances, account_map, children_map