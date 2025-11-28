# app/api/accounts.py
import io
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.core.dependencies import get_db
from app.models.domain import Account, AccountType, CategoryType
from app.schemas.account_schemas import AccountCreate, AccountRead

router = APIRouter()

# --- Helpers ---

async def get_or_create_account(
    db: AsyncSession, 
    name: str, 
    acc_type: str, 
    cat_type: str, 
    parent_id: int = None,
    cache: Dict = None
) -> Account:
    """
    Helper to find an account or create it if it doesn't exist.
    Uses a local cache to speed up bulk imports.
    """
    key = (name, acc_type, parent_id)
    
    # 1. Check Cache
    if cache and key in cache:
        return cache[key]

    # 2. Check Database
    stmt = select(Account).where(
        Account.name == name,
        Account.type == acc_type,
        Account.parent_id == parent_id
    )
    result = await db.execute(stmt)
    account = result.scalars().first()

    # 3. Create if missing
    if not account:
        account = Account(
            name=name,
            type=acc_type,
            category_type=cat_type,
            parent_id=parent_id
        )
        db.add(account)
        await db.flush() # Flush to generate ID without committing transaction
        await db.refresh(account)
    
    # 4. Update Cache
    if cache is not None:
        cache[key] = account
        
    return account

# --- Endpoints ---

@router.post("/bulk-upload")
async def bulk_upload_accounts(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk uploads Chart of Accounts from a CSV file.
    Expected Columns: 'Category', 'HEAD', 'Sub head'
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
        
        # Normalize headers
        df.columns = [c.strip() for c in df.columns]
        required_cols = {'Category', 'HEAD', 'Sub head'}
        if not required_cols.issubset(df.columns):
             raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required_cols}")

        # Cache to prevent duplicate DB lookups within this request
        # Key: (name, type, parent_id) -> Account Object
        account_cache = {}

        count = 0
        for _, row in df.iterrows():
            category_str = str(row['Category']).strip().upper() # e.g., "ASSET"
            head_name = str(row['HEAD']).strip()                # e.g., "Non Current Assets"
            sub_head_name = str(row['Sub head']).strip()        # e.g., "PPE"

            # 1. Ensure Root Node (Category) exists
            # We map "ASSET" -> Name "Assets" for cleaner display, or just use the raw value.
            # Let's map standard categories to pretty names if possible, else use raw.
            pretty_names = {
                "ASSET": "Assets",
                "LIABILITY": "Liabilities",
                "EQUITY": "Equity",
                "INCOME": "Income",
                "EXPENSE": "Expenses"
            }
            root_name = pretty_names.get(category_str, category_str.title())

            root_acc = await get_or_create_account(
                db, 
                name=root_name, 
                acc_type=AccountType.CATEGORY.value, 
                cat_type=category_str, 
                parent_id=None,
                cache=account_cache
            )

            # 2. Ensure Head Node exists
            head_acc = await get_or_create_account(
                db, 
                name=head_name, 
                acc_type=AccountType.HEAD.value, 
                cat_type=category_str, 
                parent_id=root_acc.id,
                cache=account_cache
            )

            # 3. Ensure Sub-Head Node exists
            if sub_head_name and sub_head_name.lower() != 'nan':
                await get_or_create_account(
                    db, 
                    name=sub_head_name, 
                    acc_type=AccountType.SUB_HEAD.value, 
                    cat_type=category_str, 
                    parent_id=head_acc.id,
                    cache=account_cache
                )
                count += 1

        await db.commit()
        return {"status": "success", "sub_heads_processed": count}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

@router.post("/", response_model=AccountRead)
async def create_account(payload: AccountCreate, db: AsyncSession = Depends(get_db)):
    # If parent_id is provided, ensure it exists
    if payload.parent_id:
        parent_result = await db.execute(select(Account).where(Account.id == payload.parent_id))
        if not parent_result.scalars().first():
             raise HTTPException(status_code=404, detail="Parent account not found")

    new_account = Account(
        name=payload.name,
        type=payload.type,
        category_type=payload.category_type,
        parent_id=payload.parent_id
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)
    return new_account

@router.get("/", response_model=List[AccountRead])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account))
    return result.scalars().all()