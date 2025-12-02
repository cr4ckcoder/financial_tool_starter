# app/api/compliance.py
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional, Any

from app.core.dependencies import get_db
from app.models.domain import ComplianceTemplate
from app.services.compliance_service import generate_compliance_doc, html_to_pdf
from app.utils.default_compliance_templates import DEFAULT_TEMPLATES

router = APIRouter()

class TemplateCreate(BaseModel):
    name: str
    content_html: Optional[str] = ""
    template_definition: Optional[List[Any]] = None # New Field

class TemplateRead(TemplateCreate):
    id: int
    class Config:
        from_attributes = True

@router.get("/templates", response_model=List[TemplateRead])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ComplianceTemplate))
    templates = result.scalars().all()
    
    # Parse JSON for response
    output = []
    for t in templates:
        definition = json.loads(t.template_definition) if t.template_definition else None
        output.append(TemplateRead(
            id=t.id, name=t.name, content_html=t.content_html, template_definition=definition
        ))
    return output

@router.post("/templates")
async def create_template(payload: TemplateCreate, db: AsyncSession = Depends(get_db)):
    json_def = json.dumps(payload.template_definition) if payload.template_definition else None
    
    tmpl = ComplianceTemplate(
        name=payload.name, 
        content_html=payload.content_html,
        template_definition=json_def
    )
    db.add(tmpl)
    await db.commit()
    return tmpl

# --- UPDATED PREVIEW/DOWNLOAD ---

@router.get("/{work_id}/preview/{template_id}")
async def preview_document(
    work_id: int, 
    template_id: int, 
    signatory_ids: str = Query(None), # Accepts "1,2,3"
    db: AsyncSession = Depends(get_db)
):
    # Parse comma-separated IDs
    sig_ids_list = [int(x) for x in signatory_ids.split(',')] if signatory_ids else []
    
    try:
        html = await generate_compliance_doc(db, work_id, template_id, sig_ids_list)
        return {"html": html}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{work_id}/download/{template_id}")
async def download_document(
    work_id: int, 
    template_id: int, 
    signatory_ids: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    sig_ids_list = [int(x) for x in signatory_ids.split(',')] if signatory_ids else []
    
    try:
        html = await generate_compliance_doc(db, work_id, template_id, sig_ids_list)
        pdf_bytes = html_to_pdf(html)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=document.pdf"})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ... (seed endpoint remains same) ...
@router.post("/seed-defaults")
async def seed_default_templates(db: AsyncSession = Depends(get_db)):
    """
    Loads standard CA compliance templates (Engagement Letter, Consent, etc.)
    into the database.
    """
    count = 0
    # Iterate over the imported list
    for tmpl_data in DEFAULT_TEMPLATES:
        # Check if exists to avoid duplicates
        result = await db.execute(select(ComplianceTemplate).where(ComplianceTemplate.name == tmpl_data["name"]))
        existing = result.scalars().first()
        
        if not existing:
            new_tmpl = ComplianceTemplate(
                name=tmpl_data["name"],
                content_html=tmpl_data["content"]
            )
            db.add(new_tmpl)
            count += 1
            
    await db.commit()
    return {"status": "success", "templates_added": count}
