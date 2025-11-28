# /mnt/data/file_processor.py
import io
import base64
import os
import subprocess
import tempfile
from typing import Dict, Any
import pandas as pd
from pathlib import Path
import httpx
import pdfplumber
from pydub import AudioSegment
import speech_recognition as sr
import math
import traceback
import cv2
import numpy as np

class FileProcessor:
    @staticmethod
    async def process_file_from_url(url: str) -> Dict[str, Any]:
        # Accept file:// local paths and http(s)
        if url.startswith("file://") or (not url.startswith("http") and Path(url).exists()):
            path = url.replace("file://", "")
            data = Path(path).read_bytes()
            ext = Path(path).suffix.lstrip(".").lower()
            return FileProcessor._process_bytes(data, ext, url)
        else:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.get(url, timeout=60.0)
                r.raise_for_status()
                data = r.content
                ext = url.split(".")[-1].lower().split("?")[0]
                return FileProcessor._process_bytes(data, ext, url)

    @staticmethod
    def _process_bytes(data: bytes, ext: str, url: str) -> Dict[str, Any]:
        info = {"url": url, "type": ext, "size": len(data)}
        try:
            if ext == "pdf":
                # simple PDF table extraction using pdfplumber
                tables = []
                try:
                    with pdfplumber.open(io.BytesIO(data)) as pdf:
                        for page in pdf.pages[:5]:
                            try:
                                t = page.extract_table()
                                if t:
                                    df = pd.DataFrame(t[1:], columns=t[0])
                                    tables.append({"page": page.page_number, "records": df.to_dict(orient="records")})
                            except Exception:
                                continue
                except Exception:
                    pass
                info["tables"] = tables
            elif ext in ("csv", "txt"):
                try:
                    df = pd.read_csv(io.BytesIO(data))
                    info["records"] = df.to_dict(orient="records")
                except Exception:
                    info["raw"] = data.decode(errors="ignore")
            elif ext in ("xls", "xlsx"):
                try:
                    df = pd.read_excel(io.BytesIO(data), sheet_name=0)
                    info["records"] = df.to_dict(orient="records")
                except Exception:
                    info["raw"] = "excel-read-failed"
            elif ext in ("mp3", "wav", "m4a", "ogg", "flac"):
                # Audio file bytes: transcribe and return transcript + duration
                try:
                    res = FileProcessor._process_audio_bytes(data, ext)
                    info.update(res)
                except Exception as e:
                    info["audio_error"] = str(e)
                    info["audio_traceback"] = traceback.format_exc()
            elif ext in ("mp4", "mov", "webm", "mkv", "avi"):
                try:
                    res = FileProcessor._process_video_bytes(data, ext)
                    info.update(res)
                except Exception as e:
                    info["video_error"] = str(e)
                    info["video_traceback"] = traceback.format_exc()
            else:
                # default: store base64 for unknown types
                info["raw_b64"] = base64.b64encode(data).decode("utf-8")
        except Exception as e:
            info["error"] = str(e)
            info["traceback"] = traceback.format_exc()
        return info

    @staticmethod
    def read_table_from_html(html: str):
        try:
            dfs = pd.read_html(html)
            out = []
            for df in dfs:
                out.append({"data": df.to_dict(orient="records")})
            return out
        except Exception:
            return []

    # --- Media helpers -------------------------------------------------
    @staticmethod
    def _process_audio_bytes(data: bytes, ext: str) -> Dict[str, Any]:
        """Save audio bytes to a temp file, convert to WAV if needed, and transcribe."""
        tmpdir = tempfile.mkdtemp(prefix="fp_audio_")
        try:
            src_path = os.path.join(tmpdir, f"input.{ext}")
            with open(src_path, "wb") as f:
                f.write(data)

            # Convert to PCM WAV using pydub (ffmpeg required)
            wav_path = os.path.join(tmpdir, "conv.wav")
            audio = AudioSegment.from_file(src_path)
            audio.export(wav_path, format="wav")

            duration_sec = len(audio) / 1000.0

            transcript = FileProcessor._transcribe_audio_file(wav_path)

            return {"transcript": transcript, "duration_seconds": duration_sec, "audio_path": src_path}
        finally:
            # keep files for debugging; caller may remove tmpdir if desired
            pass

    @staticmethod
    def _process_video_bytes(data: bytes, ext: str) -> Dict[str, Any]:
        """Save video, extract audio for transcription and a few frames as base64 PNGs."""
        tmpdir = tempfile.mkdtemp(prefix="fp_video_")
        try:
            src_path = os.path.join(tmpdir, f"input.{ext}")
            with open(src_path, "wb") as f:
                f.write(data)

            # Extract audio track to wav using ffmpeg subprocess call
            wav_path = os.path.join(tmpdir, "extracted_audio.wav")
            # -y overwrite, -vn no video -> audio only
            cmd = ["ffmpeg", "-i", src_path, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path, "-y"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

            transcript = None
            duration_seconds = None
            if os.path.exists(wav_path):
                try:
                    audio = AudioSegment.from_wav(wav_path)
                    duration_seconds = len(audio) / 1000.0
                    transcript = FileProcessor._transcribe_audio_file(wav_path)
                except Exception:
                    transcript = None

            # Extract a few frames using cv2
            frames_b64 = []
            try:
                cap = cv2.VideoCapture(src_path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS) or 1
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                    duration = frame_count / max(fps, 1.0)
                    duration_seconds = duration_seconds or duration

                    # sample up to 3 frames evenly spaced (avoid heavy processing)
                    n_frames = min(3, max(1, int(math.floor(duration)) if duration >= 1 else 1))
                    for i in range(n_frames):
                        ts = (i + 1) * (duration / (n_frames + 1))
                        frame_idx = int(ts * fps)
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                        ret, frame = cap.read()
                        if ret:
                            # convert to PNG bytes
                            _, buf = cv2.imencode(".png", frame)
                            b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
                            frames_b64.append(b64)
                cap.release()
            except Exception:
                pass

            return {
                "transcript": transcript,
                "duration_seconds": duration_seconds,
                "frames_b64": frames_b64,
                "video_path": src_path
            }
        finally:
            pass

    @staticmethod
    def _transcribe_audio_file(wav_path: str) -> str:
        """Transcribe a WAV file using speech_recognition (offline pocketsphinx if installed, or Google SR)."""
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)

        # Try local recognizer if possible (pocketsphinx), else fallback to Google Web Speech
        try:
            # This will run if pocketsphinx is installed
            text = recognizer.recognize_sphinx(audio_data)
            return text
        except Exception:
            try:
                # Fallback to Google Web Speech API (requires internet, no key for small audio)
                text = recognizer.recognize_google(audio_data)
                return text
            except Exception:
                # Last resort: return empty or placeholder
                return ""

