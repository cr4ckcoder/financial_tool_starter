from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.core.dependencies import get_db
from app.models.domain import OrganizationSettings

router = APIRouter()

class SettingsSchema(BaseModel):
    firm_name: str
    firm_registration_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    email: Optional[str] = None

@router.get("/", response_model=SettingsSchema)
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrganizationSettings).where(OrganizationSettings.id == 1))
    settings = result.scalars().first()
    if not settings:
        # Return default defaults if not set
        return SettingsSchema(firm_name="My CA Firm")
    return settings

@router.post("/")
async def update_settings(payload: SettingsSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OrganizationSettings).where(OrganizationSettings.id == 1))
    settings = result.scalars().first()
    
    if not settings:
        settings = OrganizationSettings(id=1)
        db.add(settings)
    
    settings.firm_name = payload.firm_name
    settings.firm_registration_number = payload.firm_registration_number
    settings.address = payload.address
    settings.city = payload.city
    settings.pincode = payload.pincode
    settings.email = payload.email
    
    await db.commit()
    return {"status": "updated"}