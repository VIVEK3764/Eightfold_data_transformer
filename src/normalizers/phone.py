import re
from typing import Optional
import phonenumbers

def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalizes a phone number to E.164 format.
    Assumes default region = IN when country code is missing.
    Returns None for invalid numbers.
    Never throws exceptions.
    """
    if not phone:
        return None
        
    cleaned_input = phone.strip()
    
    # Quick pre-validation to reject obviously garbage strings like "123abc"
    # If the string contains letters (and is not an extension), phonenumbers can fail or parse weirdly.
    # So if it contains any alpha character, let's reject it unless it's a known format.
    # Specifically, check if there are letters
    if re.search(r"[a-zA-Z]", cleaned_input):
        return None
        
    try:
        # Parse using phonenumbers with default region IN
        parsed = phonenumbers.parse(cleaned_input, "IN")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
        
    # If standard parse failed, let's clean the number to digits and try parsing again
    digits_only = re.sub(r"[^\d+]", "", cleaned_input)
    if not digits_only:
        return None
        
    try:
        parsed = phonenumbers.parse(digits_only, "IN")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
        
    return None
