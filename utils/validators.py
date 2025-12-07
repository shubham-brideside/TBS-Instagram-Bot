def is_valid_phone_number(phone_number):
    """Validate phone number for various formats"""
    if not phone_number or not isinstance(phone_number, str):
        return False
    
    # Remove all spaces, hyphens, and parentheses
    cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone_number.strip())
    
    # Pattern for Indian phone numbers
    patterns = [
        r'^\+91[6-9]\d{9}$',      # +91XXXXXXXXXX (starting with 6-9)
        r'^91[6-9]\d{9}$',        # 91XXXXXXXXXX (starting with 6-9)
        r'^[6-9]\d{9}$',          # XXXXXXXXXX (10 digits starting with 6-9)
    ]
    
    # Check against all patterns
    for pattern in patterns:
        if re.match(pattern, cleaned_phone):
            return True
    
    return False