import re
from typing import Optional
from dateutil import parser

def normalize_date(date_str: str) -> Optional[str]:
    """
    Normalizes various date formats into canonical YYYY-MM format.
    Uses python-dateutil for parsing.
    Returns None for invalid dates.
    """
    if not date_str:
        return None
        
    cleaned = date_str.strip()
    cleaned_lower = cleaned.lower()
    
    # Handle ongoing/present indicators
    if cleaned_lower in ["present", "current", "now", "ongoing", "to date", "active"]:
        return "Present"
        
    # Handle single 4-digit year (e.g. 2020)
    if re.match(r"^\d{4}$", cleaned):
        return f"{cleaned}-01"
        
    try:
        # We set fuzzy=False by default to avoid weird partial parses like "abcd" getting parsed as dates.
        # But we can allow a bit of flexibility. Fuzzy=True might match "Jan 2020 abcd", but we want to fail on "abcd".
        # dateutil.parser.parse("abcd") throws ValueError anyway.
        parsed = parser.parse(cleaned)
        return parsed.strftime("%Y-%m")
    except (ValueError, TypeError, OverflowError):
        return None
