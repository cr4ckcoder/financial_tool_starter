# app/utils/validators.py
import re

def validate_udin(udin: str) -> bool:
    """
    Validates UDIN format based on ICAI standards.
    Format: YY (2 digits) + MemberID (6 digits) + Random (10 alphanum)
    Total: 18 characters
    """
    if not udin:
        return False
        
    # Regex Pattern: 2 digits, 6 digits, 10 alphanumeric characters
    pattern = r"^\d{2}\d{6}[A-Z0-9]{10}$"
    
    return bool(re.match(pattern, udin))