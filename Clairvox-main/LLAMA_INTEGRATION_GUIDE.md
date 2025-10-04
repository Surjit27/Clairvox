# Meta Llama Model Integration Guide

## Overview
Your Clairvox project has been successfully updated to use Meta's Llama-3-8B-Instruct model instead of the previous Google Flan-T5 model. This change provides better performance for claim extraction and text analysis tasks.

## What Changed

### 1. Model Configuration (`backend/synth.py`)
- **Model**: Changed from `google/flan-t5-base` to `meta-llama/Llama-3-8B-Instruct`
- **Task**: Updated from `text2text-generation` to `text-generation`
- **Prompt Format**: Updated to use Llama's chat template format
- **Generation Parameters**: Optimized for Llama models with temperature=0.1, top_p=0.9

### 2. Dependencies (`requirements.txt`)
- Added `accelerate>=0.20.0` for efficient model loading
- Updated `torch>=2.0.0` for better compatibility

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Accept Model License
Before using the Llama model, you need to accept Meta's license:
1. Visit: https://huggingface.co/meta-llama/Llama-3-8B-Instruct
2. Sign up/login to Hugging Face
3. Accept the license agreement
4. Generate an access token

### 3. Authenticate with Hugging Face
```bash
# Option 1: Using CLI
huggingface-cli login

# Option 2: Set environment variable
export HUGGINGFACE_HUB_TOKEN="your_token_here"
```

### 4. Test the Integration
```bash
python test_llama_integration.py
```

## Model Performance

### Advantages of Llama-3-8B-Instruct:
- **Better Text Understanding**: Superior performance on complex text analysis tasks
- **Improved Claim Extraction**: More accurate identification of key claims
- **Better JSON Output**: More reliable structured output generation
- **Open Source**: Fully open-source with permissive licensing

### Resource Requirements:
- **RAM**: ~16GB recommended (8GB minimum)
- **GPU**: Optional but recommended for faster inference
- **Storage**: ~16GB for model weights

## Configuration Options

### Environment Variables:
```bash
# Use LLM for claim extraction (default: heuristic)
export CLAIM_EXTRACTION_METHOD="llm"

# Use heuristic fallback method
export CLAIM_EXTRACTION_METHOD="heuristic"
```

### Alternative Models:
If you want to use a different Llama model, update `MODEL_NAME` in `backend/synth.py`:

```python
# For smaller model (faster, less accurate)
MODEL_NAME = "meta-llama/Llama-3-8B-Instruct"

# For larger model (slower, more accurate)
MODEL_NAME = "meta-llama/Llama-3-70B-Instruct"
```

## Troubleshooting

### Common Issues:

1. **Model Loading Errors**:
   - Ensure you've accepted the license and authenticated
   - Check internet connection for model download
   - Verify sufficient disk space (~16GB)

2. **Memory Issues**:
   - Use CPU inference if GPU memory is insufficient
   - Consider using the 8B model instead of 70B
   - Enable model quantization if available

3. **Performance Issues**:
   - The model will be slower on first run (downloading)
   - Subsequent runs will be faster (cached)
   - Consider using GPU acceleration

### Fallback Behavior:
The system automatically falls back to heuristic claim extraction if the LLM fails, ensuring your application continues to work even if there are model issues.

## Next Steps

1. **Test the Integration**: Run the test script to verify everything works
2. **Monitor Performance**: Check logs for any issues during claim extraction
3. **Optimize Settings**: Adjust generation parameters if needed
4. **Consider GPU**: For production use, consider GPU acceleration

## Support

If you encounter issues:
1. Check the logs for specific error messages
2. Verify all dependencies are installed correctly
3. Ensure you have sufficient system resources
4. Test with the heuristic method as a fallback

The integration maintains backward compatibility, so your existing functionality will continue to work while benefiting from improved claim extraction quality.


