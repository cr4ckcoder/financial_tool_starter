# app/services/statement_generation_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, List, Tuple
from app.models.domain import Account, MappedLedgerEntry, TrialBalanceEntry

async def calculate_statement_data(
    session: AsyncSession, 
    work_id: int
) -> Tuple[Dict[int, float], Dict[int, Account], Dict[int, List[int]]]:
    """
    Aggregates financial data.
    Returns:
      1. balances: {account_id: total_amount}
      2. account_map: {account_id: AccountObject} (for names/types)
      3. children_map: {parent_id: [child_id, child_id...]} (for hierarchy)
    """
    # 1. Fetch all accounts
    # We fetch objects to get names and hierarchy
    all_accounts = (await session.execute(select(Account))).scalars().all()
    account_map = {acc.id: acc for acc in all_accounts}
    
    # 2. Build children map
    children_map: Dict[int, List[int]] = {}
    for acc in all_accounts:
        if acc.parent_id:
            if acc.parent_id not in children_map:
                children_map[acc.parent_id] = []
            children_map[acc.parent_id].append(acc.id)
    
    # Initialize balances
    balances: Dict[int, float] = {acc.id: 0.0 for acc in all_accounts}

    # 3. Aggregate Mapped Data (The "Leaf" Nodes)
    stmt = (
        select(
            MappedLedgerEntry.account_sub_head_id, 
            func.sum(TrialBalanceEntry.closing_balance)
        )
        .join(TrialBalanceEntry, MappedLedgerEntry.trial_balance_entry_id == TrialBalanceEntry.id)
        .where(TrialBalanceEntry.financial_work_id == work_id)
        .group_by(MappedLedgerEntry.account_sub_head_id)
    )
    
    results = await session.execute(stmt)
    
    for account_id, total in results.all():
        if account_id in balances:
            balances[account_id] = float(total)

    # 4. Roll up values
    final_balances = {}
    
    def get_balance(acc_id: int) -> float:
        if acc_id in final_balances:
            return final_balances[acc_id]
        
        total = balances.get(acc_id, 0.0)
        
        if acc_id in children_map:
            for child_id in children_map[acc_id]:
                total += get_balance(child_id)
        
        final_balances[acc_id] = total
        return total

    # Calculate for all roots to ensure full coverage
    root_accounts = [acc for acc in all_accounts if acc.parent_id is None]
    for root in root_accounts:
        get_balance(root.id)
        
    return final_balances, account_map, children_map