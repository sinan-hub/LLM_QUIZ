FROM mcr.microsoft.com/playwright/python:latest

# Use a reliable Playwright base image which already includes browser binaries
WORKDIR /app

# Avoid caching issues by installing python dependencies first
COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt

# Ensure Playwright installs any missing platform deps and browsers
RUN python -m playwright install --with-deps

# Optional: install ffmpeg for media processing
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy app source
COPY . /app

# Use a non-root runtime user where possible (Playwright images create pwuser)
USER root

ENV PORT 7860
EXPOSE 7860

# Default process is the Gradio app created at app.py
CMD ["python", "app.py"]
