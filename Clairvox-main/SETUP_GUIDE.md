# CLAIRVOX - Complete Setup & Execution Guide

## Project Overview

Clairvox is an Explainable AI Research Assistant that transforms opaque AI answers into verifiable research artifacts. It breaks down answers into discrete claims, shows supporting evidence with exact quotes and sources, and provides transparent confidence scores.

---

## Complete File Structure

```
clairvox/
├── app.py                      # Main Streamlit application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── docker-compose.yml          # Docker Compose setup
├── README.md                   # Project documentation
├── .gitignore                  # Git ignore rules
├── backend/
│   ├── __init__.py            # Package initializer
│   ├── utils.py               # Utility functions (caching, text processing)
│   ├── retriever.py           # Wikipedia & web search functions
│   ├── extractor.py           # Sentence splitting utilities
│   ├── synth.py               # Claim extraction (LLM + heuristic)
│   ├── verifier.py            # Evidence verification & confidence scoring
│   └── notebook_gen.py        # Jupyter notebook generation
├── tests/
│   └── test_scoring.py        # Unit tests for confidence algorithm
├── notebooks/
│   └── README.md              # Generated notebooks directory info
└── data/                       # Cache storage (created automatically)
```

---

## Setup Instructions

### Option 1: Local Setup (Recommended for Development)

#### Prerequisites
- Python 3.10 or higher
- pip package manager
- Internet connection (for initial model downloads)

#### Step-by-Step Commands

```bash
# Navigate to the project directory
cd C:\Users\Meges\Downloads\clairvox

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Download NLTK punkt data (required for sentence tokenization)
python -c "import nltk; nltk.download('punkt')"

# Run the application
streamlit run app.py
```

The application will start and open in your default browser at `http://localhost:8501`

---

### Option 2: Docker Setup (Recommended for Production/Demo)

#### Prerequisites
- Docker installed and running
- Docker Compose installed

#### Using Docker Compose (Easiest)

```bash
# Navigate to the project directory
cd C:\Users\Meges\Downloads\clairvox

# Build and start the container
docker-compose up --build

# The app will be available at http://localhost:8501

# To stop the container:
# Press Ctrl+C, then run:
docker-compose down
```

#### Using Docker Directly

```bash
# Navigate to the project directory
cd C:\Users\Meges\Downloads\clairvox

# Build the Docker image
docker build -t clairvox:latest .

# Run the container
docker run -p 8501:8501 -v ./data:/app/data clairvox:latest

# The app will be available at http://localhost:8501
```

---

## Running Tests

```bash
# Make sure you're in the project directory with venv activated
cd C:\Users\Meges\Downloads\clairvox

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_scoring.py
```

---

## Using the Application

### Basic Usage

1. **Start the application** using one of the methods above
2. **Enter a research query** in the text input (e.g., "Does intermittent fasting improve weight loss?")
3. **Click "Analyze Query"** to begin the analysis
4. **Review the results**:
   - View extracted claims
   - Check confidence scores (0-100)
   - Examine supporting evidence with sources
   - Review score breakdowns
5. **Download notebooks** for reproducible verification

### Understanding Confidence Scores

- **75-100**: High confidence (strong evidence from diverse sources)
- **50-74**: Moderate confidence (decent support but may have gaps)
- **0-49**: Low confidence (limited or contradictory evidence)

### Score Components

- **Support Count** (20 pts max): Number of supporting sources
- **Domain Diversity** (25 pts max): Variety of source domains
- **Recency** (30 pts max): How recent the sources are
- **Contradictions** (-30 pts max): Penalty for contradicting evidence

---

## Environment Variables

You can customize the application behavior with environment variables:

```bash
# Use heuristic method instead of LLM (reduces memory usage)
set CLAIM_EXTRACTION_METHOD=heuristic  # Windows
export CLAIM_EXTRACTION_METHOD=heuristic  # macOS/Linux

# Then run the app
streamlit run app.py
```

---

## Troubleshooting

### Model Download Issues

**Problem**: Hugging Face model download fails  
**Solution**: 
```bash
# Use heuristic mode (no LLM required)
set CLAIM_EXTRACTION_METHOD=heuristic
streamlit run app.py
```

### DuckDuckGo Rate Limiting

**Problem**: Getting rate limited during searches  
**Solution**: The app automatically caches results in `data/cache.db`. Wait a few minutes and try again. Cached queries will work immediately.

### Docker Memory Issues

**Problem**: Docker container crashes with OOM error  
**Solution**: 
1. Increase Docker Desktop memory limit (Settings → Resources → Memory: 4-6GB)
2. Or use heuristic mode by adding to `docker-compose.yml`:
   ```yaml
   environment:
     - CLAIM_EXTRACTION_METHOD=heuristic
   ```

### Port Already in Use

**Problem**: Port 8501 is already in use  
**Solution**:
```bash
# Use a different port
streamlit run app.py --server.port=8502

# Or for Docker:
docker run -p 8502:8501 clairvox:latest
```

### NLTK Data Missing

**Problem**: "punkt" tokenizer not found  
**Solution**:
```bash
python -c "import nltk; nltk.download('punkt')"
```

---

## Performance Tips

1. **First Run**: Model downloads may take 2-5 minutes
2. **Caching**: Subsequent identical queries are instant (served from cache)
3. **Memory**: LLM mode requires ~2-3GB RAM; heuristic mode uses <500MB
4. **Network**: Requires internet for Wikipedia and web searches

---

## Development Workflow

### Making Changes

```bash
# 1. Activate virtual environment
venv\Scripts\activate

# 2. Make your code changes

# 3. Run tests to verify
pytest

# 4. Test the app
streamlit run app.py

# 5. Commit your changes
git add .
git commit -m "Your commit message"
```

### Adding New Dependencies

```bash
# 1. Install the package
pip install new-package-name

# 2. Update requirements.txt
pip freeze > requirements.txt

# 3. Rebuild Docker image if using Docker
docker-compose up --build
```

---

## Project Features Summary

✅ **Implemented**:
- Wikipedia context retrieval
- Web search via DuckDuckGo
- LLM-based claim extraction with heuristic fallback
- Transparent confidence scoring
- Evidence verification with source tracking
- Contradiction detection
- Recency scoring
- Domain diversity analysis
- Reproducible Jupyter notebook generation
- Persistent caching
- Full Docker support
- Comprehensive unit tests

🚀 **Future Enhancements**:
- NLI-based contradiction detection
- Source quality analysis
- Interactive evidence highlighting
- API integration for external LLM services

---

## Quick Reference

### Common Commands

```bash
# Local run
streamlit run app.py

# Docker run
docker-compose up

# Run tests
pytest

# Clean cache
rm -rf data/cache.db  # Linux/Mac
del data\cache.db     # Windows

# Check installed packages
pip list

# Update all packages
pip install --upgrade -r requirements.txt
```

---

## Support & Documentation

- **Full README**: See `README.md` in project root
- **API Documentation**: Check inline comments in each module
- **Test Examples**: See `tests/test_scoring.py` for usage patterns

---

## License

MIT License - See project README for details

---

**Last Updated**: 2025-10-02  
**Version**: 1.0.0
