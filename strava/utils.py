
import re

def sanitize_filename(name: str) -> str:
    r"""
    Sanitize the string to be safe for filenames.
    Replaces special characters (Windows invalid characters) with underscores.
    Invalid characters: < > : " / \ | ? *
    """
    # Replace invalid characters with underscore
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Strip leading/trailing whitespace
    return sanitized.strip()
