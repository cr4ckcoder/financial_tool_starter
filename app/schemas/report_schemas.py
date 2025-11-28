# app/schemas/report_schemas.py
from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any

# We use a flexible schema for the template definition 
# because it's a JSON list of various items (titles, lines, subtotals)
class ReportTemplateCreate(BaseModel):
    name: str
    statement_type: str  # BALANCE_SHEET, PROFIT_LOSS, etc.
    template_definition: List[Dict[str, Any]]

class ReportTemplateRead(ReportTemplateCreate):
    id: int

    class Config:
        from_attributes = True