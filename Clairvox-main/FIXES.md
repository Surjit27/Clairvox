# COMMON ERRORS AND FIXES

## Issue: Wikipedia 404 Error

**Error Message:**
```
ERROR:root:Error fetching Wikipedia summary for 'Does intermittent fasting improve weight loss?': 
404 Client Error: Not Found for url: https://en.wikipedia.org/api/rest_v1/page/summary/...
```

**Root Cause:** 
Wikipedia's API expects article titles (e.g., "Intermittent fasting"), not full questions.

**✅ FIXED:**
The code has been updated to:
1. Extract the main topic from questions automatically
2. Fall back to Wikipedia search if direct lookup fails
3. Gracefully handle failures and continue with web search only

**What Changed:**
- `backend/retriever.py`: Added `extract_topic_from_query()` function
- `app.py`: Added fallback when Wikipedia context is unavailable

---

## Other Common Errors

### 1. Model Download Timeout

**Error:**
```
ConnectionError: Couldn't reach https://huggingface.co/...
```

**Fix:**
```cmd
set CLAIM_EXTRACTION_METHOD=heuristic
streamlit run app.py
```

### 2. DuckDuckGo Rate Limit

**Error:**
```
RatelimitException: Ratelimit
```

**Fix:** 
- Wait 5 minutes
- Cached queries work immediately
- Consider running fewer concurrent searches

### 3. NLTK Data Missing

**Error:**
```
LookupError: Resource punkt not found
```

**Fix:**
```cmd
python -c "import nltk; nltk.download('punkt')"
```

### 4. Port Already in Use

**Error:**
```
OSError: [Errno 98] Address already in use
```

**Fix:**
```cmd
streamlit run app.py --server.port=8502
```

### 5. Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'streamlit'
```

**Fix:**
```cmd
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Testing After Fixes

Try these test queries:

1. **Good Query (has Wikipedia article):**
   - "Does intermittent fasting improve weight loss?"
   - Should now extract "intermittent fasting" and find Wikipedia page

2. **Query without direct Wikipedia match:**
   - "What are the best practices for remote work?"
   - Should gracefully fall back to web search only

3. **Technical Query:**
   - "How does blockchain technology work?"
   - Should find Wikipedia page for "blockchain technology"

---

## Verification Checklist

After applying fixes:
- [ ] App starts without errors
- [ ] Can submit a query
- [ ] Wikipedia warning appears if no article found (not error)
- [ ] Web search proceeds regardless
- [ ] Claims are extracted
- [ ] Confidence scores display
- [ ] Evidence shows with sources

---

**Last Updated:** 2025-10-02 (Fixed Wikipedia query handling)
