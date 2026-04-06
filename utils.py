import re

def normalize_name(name: str) -> str:
    if not name:
        return None
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)  # remove dots, commas
    name = re.sub(r"\s+", " ", name).strip()
    return name


def safe_int(val, default=0):
    try:
        return int(val)
    except:
        return default


def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default


def clean_name(name):
    return (
        name.replace("(c)", "")
            .replace("(wk)", "")
            .strip()
    )


def normalize_date(date_str, fallback_year=None):
    """
    Parses 'Saturday, December 28' + year into 'YYYY-MM-DD'.
    If parsing fails, returns None.
    """
    if not date_str:
        return None
        
    try:
        from datetime import datetime
        import re
        # Cricbuzz format is usually "Day, Month Date" e.g., "Saturday, December 28"
        # We need to append the year to make it parseable
        if not fallback_year:
            fallback_year = datetime.now().year
            
        clean_date = date_str.strip()
        # Some dates might already have a year (unlikely in Match Facts but possible)
        if re.search(r"\d{4}", clean_date):
            # Try to parse if it has 4 digits
            # Fallback to a simpler parse if %Y is present
            pass
            
        # Standard parsing
        parsed_dt = datetime.strptime(f"{clean_date}, {fallback_year}", "%A, %B %d, %Y")
        return parsed_dt.strftime("%Y-%m-%d")
    except Exception as e:
        # Try without the day name if it fails
        try:
            from datetime import datetime
            clean_date = date_str.split(",")[-1].strip()
            parsed_dt = datetime.strptime(f"{clean_date}, {fallback_year}", "%B %d, %Y")
            return parsed_dt.strftime("%Y-%m-%d")
        except:
            print(f"⚠️ Date normalization failed for '{date_str}': {e}")
            return None


def normalize_dob(dob_str):
    """
    Parses Cricbuzz 'Born' string e.g. 'December 01, 2000 (25 years)' 
    into 'YYYY-MM-DD'.
    """
    if not dob_str or "Unknown" in str(dob_str):
        return None
        
    try:
        from datetime import datetime
        import re
        
        # 1. Extract the main date part (before the parenthesis)
        # e.g., "December 01, 2000"
        match = re.search(r"([A-Za-z]+ \d{2}, \d{4})", dob_str)
        if match:
            clean_date = match.group(1)
            parsed_dt = datetime.strptime(clean_date, "%B %d, %Y")
            return parsed_dt.strftime("%Y-%m-%d")
            
        # 2. Fallback for formats like "Oct 11, 1996"
        match = re.search(r"([A-Za-z]{3} \d{1,2}, \d{4})", dob_str)
        if match:
            clean_date = match.group(1)
            parsed_dt = datetime.strptime(clean_date, "%b %d, %Y")
            return parsed_dt.strftime("%Y-%m-%d")
            
        return None
    except Exception as e:
        print(f"⚠️ DOB normalization failed for '{dob_str}': {e}")
        return None
