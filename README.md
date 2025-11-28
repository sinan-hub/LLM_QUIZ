---
title: "LLM Analysis Quiz Solver"
emoji: "🤖"
colorFrom: "blue"
colorTo: "purple"
sdk: "docker"
pinned: false
app_port : 7860
license: "mit"
---

# LLM Analysis Quiz Solver 🚀

This Space runs a **FastAPI + Playwright + ffmpeg** service that can automatically solve IITM’s LLM Analysis Quiz.

It performs:

- JavaScript-rendered scraping (Playwright + Chromium)
- File processing (PDF, CSV, Excel, JSON, TXT)
- Audio/video processing (OPUS, WAV, MP4 → transcript or frames)
- LLM-based reasoning & answer extraction
- Chained quiz solving (follows next URLs automatically)
- Optional visualizations (base64 PNG charts/tables)
- Strict 3-minute-per-quiz pipeline

This Space uses **Docker**, which means:
- Full control over Python environment
- System-level packages (Chromium, ffmpeg)
- Custom FastAPI server (uvicorn)
- Playwright browser installation inside the container

---

## 🚀 Endpoints

### `POST /solve-quiz`

**Body:**
```json
{
  "email": "your-email",
  "secret": "your-secret",
  "url": "https://quiz-url"
}
