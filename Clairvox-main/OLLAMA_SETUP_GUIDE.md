# Ollama Integration Setup Guide

This guide explains how to set up and use Ollama with Llama 3.2 for Clairvox's claim extraction functionality.

## Prerequisites

1. **Install Ollama**: Download and install Ollama from [https://ollama.ai](https://ollama.ai)
2. **Python Dependencies**: Ensure all requirements are installed:
   ```bash
   pip install -r requirements.txt
   ```

## Setup Steps

### 1. Install and Start Ollama

**Windows:**
```bash
# Download Ollama from https://ollama.ai
# Install the downloaded executable
# Start Ollama (it will run in the background)
```

**Linux/macOS:**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve
```

### 2. Pull Llama 3.2 Model

```bash
# Pull the Llama 3.2 model (this may take several minutes)
ollama pull llama3.2

# Verify the model is installed
ollama list
```

### 3. Configure Environment

Set the environment variable to use Ollama:

```bash
# Windows (Command Prompt)
set CLAIM_EXTRACTION_METHOD=ollama

# Windows (PowerShell)
$env:CLAIM_EXTRACTION_METHOD="ollama"

# Linux/macOS
export CLAIM_EXTRACTION_METHOD=ollama
```

### 4. Test the Integration

Run the test script to verify everything works:

```bash
python test_ollama_integration.py
```

## Usage

### Running Clairvox with Ollama

1. **Start Ollama** (if not already running):
   ```bash
   ollama serve
   ```

2. **Set environment variable**:
   ```bash
   export CLAIM_EXTRACTION_METHOD=ollama
   ```

3. **Run Clairvox**:
   ```bash
   streamlit run app.py
   ```

### Fallback Behavior

If Ollama is not available or fails, Clairvox will automatically fall back to the heuristic method for claim extraction.

## Configuration Options

### Ollama API Settings

The following settings are configured in `backend/synth.py`:

- **API URL**: `http://localhost:11434/api/generate`
- **Model**: `llama3.2`
- **Temperature**: `0.1` (for consistent output)
- **Top-p**: `0.9`
- **Max tokens**: `1024`

### Alternative Models

You can use other Ollama models by modifying the `OLLAMA_MODEL` variable in `backend/synth.py`:

```python
OLLAMA_MODEL = "llama3.1"  # or "llama3.2:8b", "llama3.2:70b", etc.
```

## Troubleshooting

### Common Issues

1. **"Connection refused" error**:
   - Ensure Ollama is running: `ollama serve`
   - Check if Ollama is accessible: `curl http://localhost:11434/api/tags`

2. **"Model not found" error**:
   - Pull the model: `ollama pull llama3.2`
   - List available models: `ollama list`

3. **Slow performance**:
   - Use a smaller model: `llama3.2:8b` instead of `llama3.2:70b`
   - Ensure sufficient RAM (8GB+ recommended)

4. **Empty responses**:
   - Check Ollama logs for errors
   - Verify the model is properly installed
   - Try restarting Ollama: `ollama serve`

### Performance Tips

- **Memory Usage**: Llama 3.2 requires ~4-8GB RAM depending on model size
- **Speed**: First request may be slower due to model loading
- **Caching**: Clairvox caches results to improve performance

## API Reference

### Ollama API Endpoint

```
POST http://localhost:11434/api/generate
```

**Request Body:**
```json
{
  "model": "llama3.2",
  "prompt": "Your prompt here",
  "stream": false,
  "options": {
    "temperature": 0.1,
    "top_p": 0.9,
    "num_predict": 1024
  }
}
```

**Response:**
```json
{
  "response": "Generated text here",
  "done": true
}
```

## Security Notes

- Ollama runs locally on your machine
- No data is sent to external services
- API is accessible only from localhost by default
- For production use, consider securing the Ollama API endpoint

## Support

If you encounter issues:

1. Check the Ollama documentation: [https://ollama.ai/docs](https://ollama.ai/docs)
2. Verify Ollama is running: `ollama list`
3. Test with a simple prompt: `ollama run llama3.2 "Hello world"`
4. Check Clairvox logs for detailed error messages
