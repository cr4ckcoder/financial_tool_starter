# app/api/report_config.py
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict

from app.core.dependencies import get_db
from app.models.domain import WorkReportConfiguration, FinancialWork

router = APIRouter()

class ReportConfigUpdate(BaseModel):
    custom_notes: Dict[str, str]

@router.get("/{work_id}/config")
async def get_report_config(work_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkReportConfiguration).where(WorkReportConfiguration.financial_work_id == work_id))
    config = result.scalars().first()
    
    if not config:
        return {"custom_notes": {}}
    
    return {"custom_notes": json.loads(config.custom_notes)}

@router.post("/{work_id}/config")
async def update_report_config(
    work_id: int, 
    payload: ReportConfigUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # Check if work exists
    work = await db.get(FinancialWork, work_id)
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")

    result = await db.execute(select(WorkReportConfiguration).where(WorkReportConfiguration.financial_work_id == work_id))
    config = result.scalars().first()
    
    if not config:
        config = WorkReportConfiguration(financial_work_id=work_id)
        db.add(config)
    
    config.custom_notes = json.dumps(payload.custom_notes)
    await db.commit()
    return {"status": "updated"}