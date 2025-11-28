# app/api/templates.py
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.dependencies import get_db
from app.models.domain import ReportTemplate
from app.schemas.report_schemas import ReportTemplateCreate, ReportTemplateRead

router = APIRouter()

@router.post("/", response_model=ReportTemplateRead)
async def create_template(payload: ReportTemplateCreate, db: AsyncSession = Depends(get_db)):
    # Dump the list of dicts to a JSON string for storage
    json_def = json.dumps(payload.template_definition)
    
    new_template = ReportTemplate(
        name=payload.name,
        statement_type=payload.statement_type,
        template_definition=json_def
    )
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    
    # We must manually attach the parsed JSON back for the response model to work
    # (Because the DB has a string, but the Pydantic model expects a List)
    response_obj = ReportTemplateRead(
        id=new_template.id,
        name=new_template.name,
        statement_type=new_template.statement_type,
        template_definition=payload.template_definition 
    )
    return response_obj

@router.get("/", response_model=List[ReportTemplateRead])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReportTemplate))
    templates = result.scalars().all()
    
    # Convert stored JSON strings back to lists
    output = []
    for t in templates:
        t_def = json.loads(t.template_definition) if isinstance(t.template_definition, str) else t.template_definition
        output.append(ReportTemplateRead(
            id=t.id, 
            name=t.name, 
            statement_type=t.statement_type, 
            template_definition=t_def
        ))
    return output