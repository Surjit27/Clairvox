import re
import nltk
from .utils import clean_text

def split_into_sentences(text: str) -> list[str]:
    """Splits text into sentences using NLTK for better accuracy."""
    try:
        # Ensure 'punkt' is downloaded. Can be done once at app startup.
        return nltk.sent_tokenize(text)
    except Exception as e:
        # Fallback to a simpler regex-based splitter if NLTK fails
        print(f"NLTK sentence tokenization failed: {e}. Using regex fallback.")
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
        return [s.strip() for s in sentences if s.strip()]

# You already have clean_text in utils.py, but keeping it here as per spec
# if you want this module to be self-contained.
def clean_text_local(text: str) -> str:
    """A wrapper for the utility function for code clarity."""
    return clean_text(text)
