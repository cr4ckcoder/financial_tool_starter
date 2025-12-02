# app/services/compliance_service.py
import json
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from jinja2 import Template
from weasyprint import HTML

from app.models.domain import FinancialWork, OrganizationSettings, ComplianceTemplate, Signatory

async def generate_compliance_doc(
    session: AsyncSession, 
    work_id: int, 
    template_id: int, 
    signatory_ids: list[int] = None # <--- NEW ARGUMENT
):
    # 1. Fetch Work & Company
    work = await session.get(FinancialWork, work_id, options=[joinedload(FinancialWork.company)])
    if not work: raise ValueError("Work not found")
    
    # 2. Fetch Settings
    settings_res = await session.execute(select(OrganizationSettings).where(OrganizationSettings.id == 1))
    settings = settings_res.scalars().first() or OrganizationSettings(firm_name="My CA Firm")
    
    # 3. Fetch Template
    template = await session.get(ComplianceTemplate, template_id)
    if not template: raise ValueError("Template not found")

    # 4. Fetch Selected Signatories (if any)
    selected_signatories = []
    if signatory_ids:
        # Fetch only the IDs passed in the request
        sig_res = await session.execute(select(Signatory).where(Signatory.id.in_(signatory_ids)))
        selected_signatories = sig_res.scalars().all()

    # 5. Build Context
    context = {
        "cafirm": {
            "name": settings.firm_name,
            "frn": settings.firm_registration_number or "FRN_MISSING",
            "address": f"{settings.address or ''}, {settings.city or ''}",
            "email": settings.email,
            "pan": settings.pan or "PAN_MISSING"
        },
        "client": {
            "company": {
                "name": work.company.legal_name,
                "address": work.company.registered_address,
                "pan": work.company.pan,
                "cin": work.company.cin
            },
            # Helper for the first signatory if needed for single signatures
            "authorized_signatory": selected_signatories[0] if selected_signatories else None
        },
        "assignment": {
            "financialyear": f"{work.start_date.year}-{work.end_date.year}",
            "start_date": work.start_date.strftime("%d-%m-%Y"),
            "end_date": work.end_date.strftime("%d-%m-%Y"),
            "date": date.today().strftime("%d-%m-%Y")
        },
        # Pass the full list for looping
        "signatories": selected_signatories
    }

    # 6. Assemble Blocks
    final_html = ""
    
    # If using new Block system
    if template.template_definition:
        blocks = json.loads(template.template_definition)
        for block in blocks:
            if block['type'] == 'text':
                # Render text block with Jinja variables
                t = Template(block['content'])
                final_html += t.render(**context)
            
            elif block['type'] == 'signatories':
                # Render Dynamic Signatory Section
                sig_html = '<div style="margin-top: 30px;">'
                if block.get('title'):
                    sig_html += f"<p><strong>{block['title']}</strong></p>"
                
                # Loop through selected signatories
                for sig in selected_signatories:
                    sig_html += f"""
                    <div style="margin-bottom: 20px; page-break-inside: avoid;">
                        <p>__________________________</p>
                        <p><strong>{sig.name}</strong></p>
                        <p>{sig.designation}</p>
                        <p>DIN/PAN: {sig.din_number or sig.pan_number}</p>
                    </div>
                    """
                sig_html += "</div>"
                final_html += sig_html

    else:
        # Fallback for legacy templates (pure HTML)
        jinja_template = Template(template.content_html)
        final_html = jinja_template.render(**context)
    
    return final_html

def html_to_pdf(html_content: str):
    # Add basic styling for the document
    styled_html = f"""
    <html>
    <head>
        <style>
            @page {{ size: A4; margin: 2.5cm; }}
            body {{ font-family: "Times New Roman", serif; font-size: 12pt; line-height: 1.5; }}
            h3 {{ text-align: center; text-transform: uppercase; text-decoration: underline; }}
            p {{ margin-bottom: 10px; text-align: justify; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 10px; }}
            td, th {{ border: 1px solid black; padding: 5px; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    return HTML(string=styled_html).write_pdf()