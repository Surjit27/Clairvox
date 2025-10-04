# FIXED: Wikipedia Query Handling Issue

## What Was Wrong

The original code passed full questions like "Does intermittent fasting improve weight loss?" directly to Wikipedia's API, which expects article titles like "Intermittent fasting".

## What Was Fixed

### File: `backend/retriever.py`

**Added:**
1. `extract_topic_from_query()` function that:
   - Removes question words (does, is, are, can, etc.)
   - Extracts the main 2-4 word topic
   - Examples:
     - "Does intermittent fasting improve weight loss?" → "intermittent fasting"
     - "Is solar energy cost effective?" → "solar energy"

2. Wikipedia search fallback:
   - If direct lookup fails (404), searches Wikipedia for the topic
   - Uses the first search result
   - Fetches summary for that article

### File: `app.py`

**Changed:**
- Wikipedia failure now shows a warning instead of stopping execution
- App continues with web search even if Wikipedia fails
- Uses the query itself as context if no Wikipedia article found

## Test It Now

Restart your app and try the same query:

```cmd
# Stop the current app (Ctrl+C)
# Restart it
streamlit run app.py
```

Now enter: "Does intermittent fasting improve weight loss?"

**Expected behavior:**
1. Extracts topic: "intermittent fasting"
2. Finds Wikipedia article successfully
3. Proceeds with claim extraction
4. No 404 error

## Alternative Test Queries

Try these to see different behaviors:

**Has Wikipedia article:**
- "Does coffee improve productivity?" → finds "coffee"
- "Is exercise good for mental health?" → finds "exercise"

**No direct Wikipedia match:**
- "What are best practices for remote work?" → warning, but continues with web search

---

**Status:** ✅ FIXED AND READY TO TEST
