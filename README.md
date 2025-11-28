
Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
# LLM Analysis Quiz Solver

A complete automated system that solves IITM's LLM Analysis Quiz by scraping quiz pages, downloading files, processing data, analyzing tasks with an LLM, generating visualizations, and submitting answers within the required 3-minute limit.

## Features

### A. Web Scraping
- Full JavaScript rendering using Playwright
- Extracts text, HTML, tables, scripts, base64 content
- Detects and downloads files (PDF, CSV, Excel, JSON, TXT)
- Extracts and processes media (audio, video)
- Identifies the submit URL and instructions automatically

### B. File and Media Processing
- PDF table extraction (pdfplumber)
- CSV and Excel parsing (pandas)
- JSON and text extraction
- Audio processing:
  - Converts audio to WAV
  - Transcribes when possible
  - Base64 fallback for unsupported formats
- Video processing:
  - Extracts audio track
  - Captures representative frames
  - Produces transcripts or frame previews

### C. LLM Analysis 
- Sends scraped data + processed files + media transcripts to the LLM
- Extracts final answers without explanation
- Supports numeric, text, boolean, and JSON answers
- Can generate data visualizations when required
- Designed to stay within token and time limits

### D. Chained Quiz Solving
- Automatically follows next URLs returned by quiz server
- Solves each quiz in sequence
- Maintains full logs and error tracking per step

### E. FastAPI Endpoint
- Validates secret string (403 if incorrect)
- Accepts quiz URL, email, secret
- Runs solver pipeline
- Returns:
  - answer
  - intermediate steps
  - errors (if any)
  - visualizations (base64)
  - next URL (if chained)

### F. Prompt Challenge Module
- System prompt designed to prevent extraction of appended code words
- User prompt designed to jailbreak weak system prompts
- Supports pairwise prompt testing

### G. Docker Support
- Includes a production-ready Dockerfile
- Installs Playwright + Chromium + ffmpeg
- Runs FastAPI server with uvicorn
- Ready for Hugging Face or cloud deployment

### H. Hugging Face Hosting
- Can be pushed as a normal repo
- Or deployed as a Docker Space
- All dependencies & environment setup included

## Project Structure

- `main.py` – FastAPI application
- `quiz_solver.py` – Core quiz solving engine
- `quiz_scraper.py` – Playwright-based scraper
- `file_processor.py` – PDF/CSV/audio/video processor
- `llm_analyzer.py` – LLM orchestration module
- `visualization.py` – Chart/table generation
- `prompts.py` – Prompt challenge logic
- `llm_prompt_challenge.py` – Code word protection tester
- `requirements.txt` – Dependencies
- `Dockerfile` – Deployment container
- `.gitignore` – Ignored files
- `README.md` – Documentation

## Capabilities

- Scrape → Process → Analyze → Submit, all autonomously
- Handles text, numbers, files, tables, images, audio, video
- Supports chained quiz flows
- Produces clean, structured JSON output
- Fully compatible with IITM LLM Analysis Quiz requirements

---
