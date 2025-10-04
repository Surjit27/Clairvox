import shelve
import hashlib
import os
import re
from urllib.parse import urlparse

# --- Caching ---
CACHE_DIR = "data"
CACHE_FILE = os.path.join(CACHE_DIR, "cache.db")

# Ensure the cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_key(prefix: str, text: str) -> str:
    """Creates a consistent cache key."""
    return f"{prefix}_{hashlib.md5(text.encode()).hexdigest()}"

def cache_set(key: str, value):
    """Sets a value in the cache."""
    with shelve.open(CACHE_FILE) as db:
        db[key] = value

def cache_get(key: str):
    """Gets a value from the cache. Returns None if not found."""
    with shelve.open(CACHE_FILE) as db:
        return db.get(key)

# --- Text & URL Processing ---
def clean_text(text: str) -> str:
    """Basic text cleaning."""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespaces with a single space
    text = text.strip()
    return text

def get_domain(url: str) -> str:
    """Extracts the domain name from a URL."""
    try:
        parsed_url = urlparse(url)
        domain = '{uri.netloc}'.format(uri=parsed_url)
        # Remove 'www.' if it exists
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return "unknown"

# --- Constants ---
USER_AGENT = "Clairvox Research Assistant/1.0 (https://github.com/your-repo; your-email@example.com)"

LOGO_SVG = """
<svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12C4 7.59 7.59 4 12 4C16.41 4 20 7.59 20 12C20 16.41 16.41 20 12 20Z" fill="#4A90E2"/>
<path d="M12 6C9.24 6 7 8.24 7 11C7 12.76 7.85 14.31 9.25 15.26L9.2 15.3C9.15 15.33 9.1 15.38 9.07 15.43L12 18L14.93 15.43C14.9 15.38 14.85 15.33 14.8 15.3L14.75 15.26C16.15 14.31 17 12.76 17 11C17 8.24 14.76 6 12 6ZM12 13.5C11.17 13.5 10.5 12.83 10.5 12C10.5 11.17 11.17 10.5 12 10.5C12.83 10.5 13.5 11.17 13.5 12C13.5 12.83 12.83 13.5 12 13.5Z" fill="#4A90E2"/>
</svg>
"""
