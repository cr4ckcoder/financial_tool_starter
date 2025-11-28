# app/utils/csv_parser.py
import pandas as pd
from io import BytesIO
from typing import List, Dict, Any

def clean_currency(value: Any) -> float:
    """
    Cleans string formatted currency from the specific user format.
    Examples: 
      - " 13,110.00 "  -> 13110.0
      - " -   "        -> 0.0
      - "-1,37,890.49" -> -137890.49
      - nan            -> 0.0
    """
    if pd.isna(value):
        return 0.0
    
    s = str(value).strip()
    
    # Handle the specific dash used for zero in your file
    if s == '-' or s == ' - ':
        return 0.0
        
    # Remove common artifacts
    s = s.replace('"', '').replace(',', '').replace(' ', '')
    
    try:
        return float(s)
    except ValueError:
        return 0.0

def parse_trial_balance(file_contents: bytes) -> List[Dict[str, Any]]:
    """
    Parses the Trial Balance CSV, handling the specific 4-row header skip.
    """
    try:
        # 1. Read CSV, skipping the first 4 metadata rows
        # The 5th row (index 4) contains: Account Name, Debit , Credit ,Closing Balance
        df = pd.read_csv(BytesIO(file_contents), skiprows=4, dtype=str)
        
        # 2. Normalize headers (strip whitespace, lowercase)
        # This turns " Debit " into "debit" and "Account Name" into "account name"
        df.columns = [c.strip().lower() for c in df.columns]
        
        # 3. Validate Columns
        # We check for 'account name' instead of 'particulars' based on your file
        if 'account name' not in df.columns:
            # Fallback: maybe the file didn't have the top rows? 
            # In a real app, we might try reloading without skiprows, but for now let's be strict.
            print("Warning: 'account name' column not found. Columns are:", df.columns)
            return []

        results = []
        for _, row in df.iterrows():
            # 4. Clean and convert data
            name = str(row.get('account name', '')).strip()
            
            # Skip empty rows or total rows (your file has a 'TOTAL' row at the bottom)
            if not name or name.upper() == 'TOTAL': 
                continue
                
            debit = clean_currency(row.get('debit', 0))
            credit = clean_currency(row.get('credit', 0))
            
            # 5. Calculate closing balance
            # Ideally, we verify this against the 'closing balance' column in your CSV
            # But usually, it's safer to recalculate: Debit - Credit
            closing_balance = debit - credit
            
            results.append({
                "account_name": name,
                "debit": debit,
                "credit": credit,
                "closing_balance": closing_balance
            })
            
        return results
    except Exception as e:
        print(f"Parsing error: {e}")
        return []