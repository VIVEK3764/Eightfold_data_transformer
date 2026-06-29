import re
from typing import Optional

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def normalize_email(email: str) -> Optional[str]:
    """
    Normalizes an email address by trimming whitespace and converting to lowercase.
    Returns None if the email is invalid.
    """
    if not email:
        return None
        
    cleaned = email.strip().lower()
    if not EMAIL_REGEX.match(cleaned):
        return None
        
    return cleaned
