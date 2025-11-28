# app/services/report_service.py
import io
import json
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from jinja2 import Template
from weasyprint import HTML
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

from app.models.domain import ReportTemplate, FinancialWork
from app.services.statement_generation_service import calculate_statement_data

# --- HTML Template (Unchanged) ---
PDF_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        @page { size: A4; margin: 1cm; }
        body { font-family: "Times New Roman", Times, serif; font-size: 11px; line-height: 1.3; }
        .company-header { text-align: center; margin-bottom: 10px; }
        .company-name { font-size: 16px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
        .report-name { font-size: 14px; font-weight: bold; margin-top: 5px; text-transform: uppercase; }
        .currency-note { font-size: 10px; font-style: italic; margin-top: 5px; margin-bottom: 15px; text-align: center;}
        table { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
        th { border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 8px 5px; font-weight: bold; vertical-align: middle; }
        td { padding: 5px 5px; vertical-align: top; }
        .col-particulars { width: 50%; text-align: left; }
        .col-note { width: 10%; text-align: center; }
        .col-amount { width: 20%; text-align: right; }
        .title-row td { font-weight: bold; padding-top: 15px; padding-bottom: 5px; }
        .subtotal-row td { border-top: 1px solid #000; border-bottom: 1px solid #000; font-weight: bold; padding-top: 8px; padding-bottom: 8px; }
        .value { font-family: monospace; font-size: 11px; }
        .page-break { page-break-before: always; }
        .note-block { margin-bottom: 20px; page-break-inside: avoid; }
        .note-header { font-weight: bold; font-size: 12px; margin-bottom: 5px; }
        .note-row { display: flex; justify-content: space-between; padding: 2px 0; }
        .note-row.total { border-top: 1px solid #ccc; font-weight: bold; margin-top: 5px; padding-top: 2px; }
        .dotted { border-bottom: 1px dotted #ccc; flex-grow: 1; margin: 0 5px; position: relative; top: -4px; }
    </style>
</head>
<body>
    {% for item in template_def %}
        {% if item.type == 'header_block' %}
            {% if not loop.first %}</tbody></table><div class="page-break"></div>{% endif %}
            <div class="company-header">
                <div class="company-name">{{ company_name }}</div>
                <div class="report-name">{{ item.text }}</div>
                <div class="currency-note">(All amounts are in Indian Rupees unless otherwise stated)</div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th class="col-particulars">Particulars</th>
                        <th class="col-note">Note No.</th>
                        <th class="col-amount">31st March 2024</th>
                        <th class="col-amount">31st March 2023</th>
                    </tr>
                </thead>
                <tbody>
        {% elif item.type == 'financial_line_item' %}
            {% set val = data.get(item.account_head_id, 0.0) %}
            {% if (val | abs > 0.01) or item.mandatory %}
            <tr>
                <td style="padding-left: 20px;">{{ item.label }}</td>
                <td class="col-note">{{ note_map.get(item.note_ref, '') }}</td>
                <td class="col-amount value">{{ "{:,.2f}".format(val | abs) }}</td>
                <td class="col-amount value">0.00</td> 
            </tr>
            {% endif %}
        {% elif item.type == 'subtotal' %}
            {% set val = data.get(item.id, 0.0) %}
            {% if (val | abs > 0.01) or item.mandatory %}
            <tr class="subtotal-row">
                <td>{{ item.label }}</td>
                <td></td>
                <td class="col-amount value">{{ "{:,.2f}".format(val | abs) }}</td>
                <td class="col-amount value">0.00</td>
            </tr>
            {% endif %}
        {% elif item.type == 'title' %}
            <tr class="title-row"><td colspan="4">{{ item.text }}</td></tr>
        {% endif %}
    {% endfor %}
    </tbody></table>

    {% if notes_data %}
        <div class="page-break"></div>
        <div class="company-header">
            <div class="company-name">{{ company_name }}</div>
            <div class="report-name">NOTES TO FINANCIAL STATEMENTS</div>
            <div class="currency-note">(All amounts are in Indian Rupees unless otherwise stated)</div>
        </div>
        {% for note in notes_data %}
            <div class="note-block">
                <div class="note-header">Note {{ note.ref }}: {{ note.title }}</div>
                {% for child in note.children %}
                <div class="note-row">
                    <span>{{ child.name }}</span>
                    <span class="dotted"></span>
                    <span class="value">{{ "{:,.2f}".format(child.amount | abs) }}</span>
                </div>
                {% endfor %}
                <div class="note-row total">
                    <span>Total</span>
                    <span></span>
                    <span class="value">{{ "{:,.2f}".format(note.total | abs) }}</span>
                </div>
            </div>
        {% endfor %}
    {% endif %}
</body>
</html>
"""

async def generate_report(
    session: AsyncSession, 
    work_id: int, 
    template_id: int, 
    format: str
) -> tuple[bytes, str]:
    
    stmt = select(FinancialWork).options(joinedload(FinancialWork.company)).where(FinancialWork.id == work_id)
    work_result = await session.execute(stmt)
    work = work_result.scalars().first()
    if not work: raise HTTPException(status_code=404, detail="Work not found")
        
    template_result = await session.execute(select(ReportTemplate).where(ReportTemplate.id == template_id))
    template = template_result.scalars().first()
    if not template: raise HTTPException(status_code=404, detail="Template not found")

    balances, account_map, children_map = await calculate_statement_data(session, work_id)
    _calculate_derived_balances(balances)

    if isinstance(template.template_definition, str):
        template_def = json.loads(template.template_definition)
    else:
        template_def = template.template_definition

    filename = f"{template.name.replace(' ', '_')}_{work.id}.{format}"

    # Notes Logic
    notes_data = []
    note_ref_map = {}
    note_counter = 3

    for item in template_def:
        if item.get('type') == 'financial_line_item' and item.get('note_ref'):
            head_id = item.get('account_head_id')
            val = balances.get(head_id, 0.0)
            if abs(val) < 0.01: continue

            children_ids = children_map.get(head_id, [])
            children_details = []
            
            for child_id in children_ids:
                child_acc = account_map.get(child_id)
                child_val = balances.get(child_id, 0.0)
                if abs(child_val) > 0.01: 
                    children_details.append({"name": child_acc.name, "amount": child_val})
            
            if children_details:
                original_ref = item.get('note_ref')
                if original_ref not in note_ref_map:
                    note_ref_map[original_ref] = str(note_counter)
                    note_counter += 1
                
                final_ref = note_ref_map[original_ref]
                notes_data.append({
                    "ref": final_ref,
                    "title": item.get('label').strip(), 
                    "children": children_details,
                    "total": val
                })

    if format == 'pdf':
        return _render_pdf(work, template_def, balances, notes_data, note_ref_map), filename
    elif format == 'xlsx':
        # Pass notes_data to Excel renderer now
        return _render_excel(work, template_def, balances, notes_data, note_ref_map), filename
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

def _calculate_derived_balances(balances: dict):
    # Same logic as before
    total_assets = balances.get(1, 0.0)
    total_liabilities = balances.get(61, 0.0)
    total_equity = balances.get(81, 0.0)
    total_income = balances.get(4, 0.0)
    total_expenses = balances.get(11, 0.0)
    
    balances[999] = total_equity + total_liabilities
    balances[1000] = total_assets
    balances[1001] = total_income
    balances[1002] = total_expenses
    pbt = total_income + total_expenses
    balances[1003] = pbt

    depreciation = balances.get(9991, 0.0)
    interest_exp = balances.get(38, 0.0)
    interest_inc = balances.get(6, 0.0)
    
    op_profit = pbt + depreciation + interest_exp - interest_inc
    balances[2001] = op_profit

    wc_changes = (
        balances.get(62, 0.0) + balances.get(52, 0.0) + 
        balances.get(57, 0.0) + balances.get(74, 0.0)
    )
    cash_gen = op_profit + wc_changes
    balances[2002] = cash_gen

    taxes = balances.get(9995, 0.0)
    balances[2003] = cash_gen - taxes

    purchase_fa = balances.get(55, 0.0)
    sale_fa = balances.get(9996, 0.0)
    balances[2004] = sale_fa + interest_inc - purchase_fa

    long_term_bor = balances.get(9902, 0.0)
    short_term_bor = balances.get(88, 0.0)
    balances[2005] = long_term_bor + short_term_bor - interest_exp

    balances[2006] = balances[2003] + balances[2004] + balances[2005]

def _render_pdf(work, template_def, data, notes_data, note_map):
    jinja_template = Template(PDF_HTML_TEMPLATE)
    html_string = jinja_template.render(
        company_name=work.company.legal_name,
        template_def=template_def,
        data=data,
        notes_data=notes_data,
        note_map=note_map
    )
    return HTML(string=html_string).write_pdf()

def _render_excel(work, template_def, data, notes_data, note_map):
    wb = Workbook()
    # Remove default sheet
    default_ws = wb.active
    wb.remove(default_ws)
    
    # Internal helper to set up a new sheet
    def create_sheet(title):
        # Excel sheet names max 31 chars, forbidden chars: : \ / ? * [ ]
        safe_title = title.replace("STATEMENT", "").strip()[:30]
        ws = wb.create_sheet(title=safe_title)
        
        # Company Header
        ws.merge_cells('A1:D1')
        ws['A1'] = work.company.legal_name
        ws['A1'].font = Font(size=14, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        # Report Title
        ws.merge_cells('A2:D2')
        ws['A2'] = title
        ws['A2'].font = Font(bold=True)
        ws['A2'].alignment = Alignment(horizontal='center')
        
        # Columns
        ws['A4'] = "Particulars"
        ws['B4'] = "Note No."
        ws['C4'] = "31st March 2024"
        ws['D4'] = "31st March 2023"
        for c in ['A', 'B', 'C', 'D']:
            ws[f'{c}4'].font = Font(bold=True)
            ws[f'{c}4'].alignment = Alignment(horizontal='center')
            ws.column_dimensions[c].width = 15 if c != 'A' else 50
            
        return ws, 5 # Return sheet and starting row index

    # --- Render Statements ---
    ws = None
    row_idx = 5
    
    # Check if we have header blocks (Full Set)
    has_header_blocks = any(i.get('type') == 'header_block' for i in template_def)
    if not has_header_blocks:
        ws, row_idx = create_sheet("Financial Statement")

    for item in template_def:
        # Create New Sheet on Header Block
        if item.get('type') == 'header_block':
            ws, row_idx = create_sheet(item.get('text'))
            continue

        # Zero check
        if item.get('type') in ['financial_line_item', 'subtotal']:
            val_check = data.get(item.get('account_head_id') or item.get('id'), 0.0)
            if abs(val_check) < 0.01 and not item.get('mandatory'): continue

        if not ws: # Fallback
            ws, row_idx = create_sheet("Report")

        if item.get('type') == 'title':
            ws[f'A{row_idx}'] = item.get('text')
            ws[f'A{row_idx}'].font = Font(bold=True, underline="single")
            row_idx += 1
            
        elif item.get('type') == 'financial_line_item':
            ws[f'A{row_idx}'] = item.get('label')
            static_ref = item.get('note_ref', '')
            ws[f'B{row_idx}'] = note_map.get(static_ref, '')
            ws[f'B{row_idx}'].alignment = Alignment(horizontal='center')
            
            val = data.get(item.get('account_head_id'), 0.0)
            ws[f'C{row_idx}'] = abs(val)
            ws[f'D{row_idx}'] = 0.00
            ws[f'C{row_idx}'].number_format = '#,##0.00'
            ws[f'D{row_idx}'].number_format = '#,##0.00'
            row_idx += 1
            
        elif item.get('type') == 'subtotal':
            ws[f'A{row_idx}'] = item.get('label')
            ws[f'A{row_idx}'].font = Font(bold=True)
            val = data.get(item.get('id'), 0.0)
            ws[f'C{row_idx}'] = abs(val)
            ws[f'D{row_idx}'] = 0.00
            ws[f'C{row_idx}'].font = Font(bold=True)
            ws[f'C{row_idx}'].number_format = '#,##0.00'
            ws[f'D{row_idx}'].number_format = '#,##0.00'
            row_idx += 1

    # --- Render Notes Sheet ---
    if notes_data:
        ws = wb.create_sheet(title="Notes")
        ws.column_dimensions['A'].width = 50
        ws.column_dimensions['B'].width = 20
        
        ws.merge_cells('A1:B1')
        ws['A1'] = "NOTES TO FINANCIAL STATEMENTS"
        ws['A1'].font = Font(size=14, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        row_idx = 3
        for note in notes_data:
            ws[f'A{row_idx}'] = f"Note {note['ref']}: {note['title']}"
            ws[f'A{row_idx}'].font = Font(bold=True)
            row_idx += 1
            
            for child in note['children']:
                ws[f'A{row_idx}'] = child['name']
                ws[f'B{row_idx}'] = abs(child['amount'])
                ws[f'B{row_idx}'].number_format = '#,##0.00'
                row_idx += 1
                
            ws[f'A{row_idx}'] = "Total"
            ws[f'A{row_idx}'].font = Font(bold=True)
            ws[f'A{row_idx}'].alignment = Alignment(horizontal='right')
            ws[f'B{row_idx}'] = abs(note['total'])
            ws[f'B{row_idx}'].font = Font(bold=True)
            ws[f'B{row_idx}'].number_format = '#,##0.00'
            row_idx += 2

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()