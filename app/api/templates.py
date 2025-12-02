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
    # Serialize lists to JSON strings for SQLite/Text storage
    json_def = json.dumps(payload.template_definition)
    json_types = json.dumps(payload.applicable_client_types)
    
    new_template = ReportTemplate(
        name=payload.name,
        statement_type=payload.statement_type,
        applicable_client_types=json_types, # Store as JSON string
        template_definition=json_def
    )
    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)
    
    return ReportTemplateRead(
        id=new_template.id,
        name=new_template.name,
        statement_type=new_template.statement_type,
        applicable_client_types=payload.applicable_client_types,
        template_definition=payload.template_definition 
    )

@router.get("/", response_model=List[ReportTemplateRead])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReportTemplate))
    templates = result.scalars().all()
    
    output = []
    for t in templates:
        # Deserialize JSON strings back to Python objects
        t_def = json.loads(t.template_definition) if isinstance(t.template_definition, str) else t.template_definition
        
        # Handle applicable_client_types (Safe load)
        try:
            t_types = json.loads(t.applicable_client_types) if t.applicable_client_types else []
        except:
            t_types = []

        output.append(ReportTemplateRead(
            id=t.id, 
            name=t.name, 
            statement_type=t.statement_type,
            applicable_client_types=t_types,
            template_definition=t_def
        ))
    return output