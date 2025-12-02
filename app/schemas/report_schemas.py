# app/schemas/report_schemas.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ReportTemplateCreate(BaseModel):
    name: str
    statement_type: str
    # New Field: List of Client Types (e.g. ["PVT_LTD", "LLP"])
    applicable_client_types: List[str] = [] 
    template_definition: List[Dict[str, Any]]

class ReportTemplateRead(ReportTemplateCreate):
    id: int

    class Config:
        from_attributes = True