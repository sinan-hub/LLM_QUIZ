# /mnt/data/quiz_solver.py
"""
QuizSolver

Orchestrates:
 - scraping a quiz page (QuizScraper)
 - downloading / processing files and media (FileProcessor)
 - analyzing question(s) with LLM (LLMAnalyzer)
 - optional submission to the quiz 'submit' endpoint
 - following chained quizzes via solve_chained_quizzes

Notes:
 - Ensure `EXECUTION_TIMEOUT` in config/settings is compatible with long media tasks.
 - Media processing (audio/video) is intentionally conservative (samples/short transcripts)
   so it is less likely to exceed the default 3-minute limit.
"""
import time
import json
import math
from typing import Dict, Any, List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

import httpx

# Import project components (these are the files in your repo)
from quiz_scraper import QuizScraper
from file_processor import FileProcessor
from llm_analyzer import LLMAnalyzer
from visualization import QuizVisualizer

# NOTE: These files are from your repository and provide the scraper, file processor and LLM analyzer.
# See: FileProcessor, QuizScraper, LLMAnalyzer for implementation details. :contentReference[oaicite:3]{index=3} :contentReference[oaicite:4]{index=4} :contentReference[oaicite:5]{index=5}

class QuizSolver:
    def __init__(self, llm_analyzer: LLMAnalyzer, timeout: int = 180, max_workers: int = 4):
        """
        llm_analyzer: LLMAnalyzer instance (handles calls to your LLM API)
        timeout: total allowed seconds for a single top-level solve run
        """
        self.llm_analyzer = llm_analyzer
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.start_time = None
        self.errors: List[str] = []
        self.steps: List[Dict[str, Any]] = []

    # ----------------- Utilities -----------------
    def _now_elapsed(self) -> float:
        if not self.start_time:
            return 0.0
        return time.time() - self.start_time

    def _check_timeout(self):
        if self.start_time and (time.time() - self.start_time) > self.timeout:
            raise TimeoutError(f"Execution exceeded {self.timeout} seconds")

    def _add_step(self, name: str, details: Any = None):
        self.steps.append({"step": name, "elapsed": self._now_elapsed(), "details": details})

    # ----------------- Scraping (sync helper) -----------------
    def _scrape_sync(self, url: str, headless: bool = True) -> Dict[str, Any]:
        """Run the Playwright scraper synchronously in threadpool."""
        with QuizScraper(headless=headless) as scraper:
            return scraper.scrape_quiz(url)

    # ----------------- File & Media Processing -----------------
    async def _process_files_async(self, file_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process discovered file links (pdf/csv/xlsx/other)."""
        processed = []
        for link in file_links[:10]:  # limit to first 10 to control time
            href = link.get("href") or link.get("url") or link.get("src")
            if not href:
                continue
            try:
                info = await FileProcessor.process_file_from_url(href)
                info["meta_text"] = link.get("text") or link.get("meta") or ""
                processed.append(info)
            except Exception as e:
                self.errors.append(f"file_process_error: {str(e)}")
        return processed

    async def _process_media_async(self, media_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Download and process media (audio/video) into transcripts and frames.
        Returns a list of processed media dicts.
        """
        processed = []
        for m in (media_links or [])[:5]:  # process up to 5 media items to bound runtime
            url = m.get("url") or m.get("href") or m.get("src")
            kind = m.get("type") or ("video" if any(x in (url or "").lower() for x in [".mp4", ".mov", ".webm"]) else "audio")
            try:
                info = await FileProcessor.process_file_from_url(url)
                info["media_type"] = kind
                info["meta_text"] = m.get("text", "")
                processed.append(info)
            except Exception as e:
                self.errors.append(f"media_process_error: {str(e)}")
        return processed

    # ----------------- Core: solve a single quiz -----------------
    async def solve_quiz(self, url: str, secret: str, email: str,
                         auto_submit: bool = True) -> Dict[str, Any]:
        """
        Solve a single quiz: scrape -> process files/media -> call LLM -> (optionally) submit.
        Returns a result dict with status, answers, submission_response (if any), errors and steps.
        """
        self.start_time = time.time()
        self.steps = []
        self.errors = []

        result: Dict[str, Any] = {
            "status": "processing",
            "url": url,
            "answers": {},
            "analysis_raw": None,
            "submission_response": None,
            "media_processed": [],
            "files_processed": [],
            "errors": self.errors,
            "steps": self.steps,
        }

        try:
            # 1) Scrape (run the playwright scraper in a thread to avoid blocking event loop)
            self._add_step("scraping", {"url": url})
            loop = asyncio.get_event_loop()
            scraped = await loop.run_in_executor(self.executor, self._scrape_sync, url, True)
            self._check_timeout()

            if scraped.get("error"):
                self.errors.append(f"scrape_error: {scraped.get('error')}")
                result["status"] = "failed"
                return result

            # 2) Process files and media (async sequentially to keep memory bounded)
            files = scraped.get("file_links", []) or []
            media = scraped.get("media_links", []) or []

            self._add_step("processing_files", {"file_count": len(files)})
            files_processed = await self._process_files_async(files)
            result["files_processed"] = files_processed
            self._check_timeout()

            self._add_step("processing_media", {"media_count": len(media)})
            media_processed = await self._process_media_async(media)
            result["media_processed"] = media_processed
            self._check_timeout()

            # 3) Prepare LLM context
            context = {
                "page_url": url,
                "text_content": (scraped.get("text_content") or "")[:12000],
                "tables": scraped.get("tables", []),
                "files": files_processed,
                "media": media_processed,
                "scripts": scraped.get("scripts", [])[:10],
            }

            # 4) Determine question text (heuristic)
            question_text = self._extract_quiz_question_text(scraped)
            self._add_step("llm_analysis", {"question_preview": question_text[:400]})

            # 5) Ask LLM for the answer
            analysis = await self.llm_analyzer.analyze_quiz_question(question_text, context)
            result["analysis_raw"] = analysis
            self._check_timeout()

            # 6) Extract answer using heuristics
            answer = self._derive_answer_from_analysis(analysis)
            result["answers"] = {"answer": answer}

            # 7) Visualizations (if recommended)
            if self._should_visualize(analysis, scraped):
                self._add_step("visualization")
                try:
                    vis = await self._create_visualizations(files_processed, scraped.get("tables", []), analysis)
                    result["visualizations"] = vis
                except Exception as e:
                    self.errors.append(f"viz_error: {str(e)}")

            # 8) (Optional) Submit the answer
            submit_url = scraped.get("submit_url")
            if auto_submit and submit_url:
                self._add_step("submission", {"submit_url": submit_url})
                try:
                    payload = {"email": email, "secret": secret, "url": url, "answer": answer}
                    # Use httpx sync client in thread pool to avoid blocking
                    resp_obj = await loop.run_in_executor(self.executor, self._post_json_sync, submit_url, payload)
                    result["submission_response"] = resp_obj
                except Exception as e:
                    self.errors.append(f"submission_exception: {str(e)}")

            result["status"] = "done"
            return result

        except TimeoutError as te:
            self.errors.append(str(te))
            result["status"] = "timeout"
            return result
        except Exception as e:
            self.errors.append(str(e))
            result["status"] = "failed"
            return result

    # ----------------- Chained quizzes -----------------
    async def solve_chained_quizzes(self, initial_url: str, secret: str, email: str,
                                    max_chain_length: int = 10) -> List[Dict[str, Any]]:
        """
        Follow quiz chains: solve the initial_url, submit, inspect response for next URL, and repeat.
        Returns a list of per-quiz result dicts.
        """

        results: List[Dict[str, Any]] = []
        current_url = initial_url

        for step_idx in range(max_chain_length):
            self._check_timeout()
            self._add_step("chain_step", {"index": step_idx + 1, "url": current_url})

            single_result = await self.solve_quiz(current_url, secret, email, auto_submit=True)
            results.append(single_result)

            # Try to detect next URL in several likely places
            next_url = None

            # 1) Top-level convenience keys
            next_url = single_result.get("next_quiz_url") or single_result.get("next_url")

            # 2) Submission response (common key from sample servers)
            if not next_url:
                sub = single_result.get("submission_response") or single_result.get("submission_result") or {}
                if isinstance(sub, dict):
                    next_url = sub.get("next_url") or sub.get("url") or sub.get("next")

            # 3) Nested 'data' block
            if not next_url and isinstance(sub, dict):
                nested = sub.get("data")
                if isinstance(nested, dict):
                    next_url = nested.get("url") or nested.get("next_url")

            # 4) If still no next url, stop chain
            if not next_url:
                break

            # normalize and continue
            current_url = next_url

        return results

    # ----------------- Helpers -----------------
    def _post_json_sync(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous POST helper used inside threadpool to avoid blocking."""
        with httpx.Client(timeout=30.0) as client:
            r = client.post(url, json=payload, timeout=30.0)
            try:
                return r.json()
            except Exception:
                return {"status_code": r.status_code, "text": r.text}

    def _extract_quiz_question_text(self, scraped: Dict[str, Any]) -> str:
        """Heuristic extraction of the question text from scraped content."""
        # Prefer explicit field from scraper
        quiz_data = scraped.get("quiz_data") or {}
        if isinstance(quiz_data, dict):
            qtext = quiz_data.get("question_text")
            if qtext:
                return qtext
            questions = quiz_data.get("questions") or []
            if questions:
                # questions may be dict/list/strings; be tolerant
                if isinstance(questions, list):
                    return str(questions[0]) if questions else ""
                return str(questions)
        # fallback to trimmed page text
        text = scraped.get("text_content") or ""
        return text.strip()[:12000]

    def _derive_answer_from_analysis(self, analysis: Dict[str, Any]) -> Any:
        """
        Extract a sensible answer from LLM analysis output.
        - If LLM returns dict with 'answer' key, use it.
        - If a string with numbers, use the first parsed numeric.
        - Otherwise return raw result.
        """
        if not analysis:
            return None
        result = analysis.get("result") if isinstance(analysis, dict) else analysis
        # if analysis.result is dict with 'answer'
        if isinstance(result, dict):
            if "answer" in result:
                return result["answer"]
            if "result" in result:
                return result["result"]
            return result
        # if string, try parse JSON then numeric
        if isinstance(result, str):
            # try parse json
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict):
                    return parsed.get("answer", parsed.get("result", parsed))
                return parsed
            except Exception:
                # attempt numeric extraction
                import re
                nums = re.findall(r'-?\d+\.?\d*', result)
                if nums:
                    n = nums[0]
                    if '.' in n:
                        try:
                            return float(n)
                        except:
                            pass
                    else:
                        try:
                            return int(n)
                        except:
                            pass
                # fallback to raw string
                return result
        # otherwise return as-is
        return result

    def _should_visualize(self, analysis: Dict[str, Any], scraped: Dict[str, Any]) -> bool:
        """Decide whether to create visualizations (simple keyword heuristic)."""
        combined = json.dumps(analysis or {}) + json.dumps(scraped or {})
        kws = ["plot", "chart", "visualize", "graph", "histogram", "bar chart"]
        low = combined.lower()
        return any(k in low for k in kws)

    async def _create_visualizations(self, files_processed: List[Dict[str, Any]],
                                     tables: List[Dict[str, Any]],
                                     analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a few visualizations where applicable and return dict of base64 images.
        Uses QuizVisualizer to create charts/tables.
        """
        out = {}
        # prefer numeric data from processed files
        for idx, f in enumerate(files_processed):
            records = f.get("records") or []
            if records and isinstance(records, list) and len(records) > 0:
                try:
                    import pandas as pd
                    df = pd.DataFrame(records)
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    if numeric_cols:
                        # create a bar chart from first numeric col (top 10 rows)
                        data = {}
                        col = numeric_cols[0]
                        for i, row in df.head(10).iterrows():
                            label = str(row.index[0]) if len(row.index) > 0 else str(i)
                            try:
                                val = float(row[col])
                            except Exception:
                                continue
                            data[label] = val
                        if data:
                            img_b64 = QuizVisualizer.create_bar_chart(data=data, title=f"File {idx} - {col}", ylabel=col)
                            out[f"file_{idx}_chart"] = img_b64
                except Exception:
                    continue
        # small table images from scraped tables
        for i, t in enumerate(tables or []):
            try:
                img = QuizVisualizer.create_table_image(data=t.get("data", [])[:20], title=f"table_{i}")
                out[f"table_{i}"] = img
            except Exception:
                continue
        return out
