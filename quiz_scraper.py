# /mnt/data/quiz_scraper.py
import base64
import re
import time
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright

class QuizScraper:
    """Simplified Playwright-based scraper with audio/video extraction."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass

    def scrape_quiz(self, url: str, wait_time: int = 2) -> Dict[str, Any]:
        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
            time.sleep(wait_time)

            html = self.page.content()
            screenshot_bytes = self.page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            scripts = self.page.evaluate("""() => {
                return Array.from(document.querySelectorAll('script'))
                    .map(s => s.textContent || s.innerText)
                    .filter(s => s && s.trim().length > 0);
            }""")

            text_content = self.page.evaluate("""() => {
                return document.body.innerText || document.body.textContent || '';
            }""") or ""

            base64_content = self._extract_base64_content(html, scripts, text_content)
            file_links = self._extract_file_links()
            media_links = self._extract_media_links()
            submit_url = self._extract_submit_url(html, text_content, base64_content)
            quiz_data = self._extract_quiz_structure(text_content, base64_content)
            tables = self._extract_tables()

            return {
                "url": url,
                "html": html,
                "screenshot": screenshot_b64,
                "scripts": scripts,
                "base64_content": base64_content,
                "file_links": file_links,
                "media_links": media_links,           # NEW
                "submit_url": submit_url,
                "quiz_data": quiz_data,
                "text_content": text_content,
                "tables": tables
            }
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "html": "",
                "screenshot": "",
                "scripts": [],
                "base64_content": [],
                "file_links": [],
                "media_links": [],
                "submit_url": None,
                "quiz_data": {},
                "text_content": "",
                "tables": []
            }

    def _extract_base64_content(self, html: str, scripts: List[str], text: str) -> List[Dict[str, Any]]:
        base64_items = []
        patterns = [
            r'atob\(["\']([A-Za-z0-9+/=]+)["\']\)',
            r'data:([^;]+);base64,([A-Za-z0-9+/=]+)',
            r'["\']([A-Za-z0-9+/=]{40,})["\']',
        ]
        all_text = html + "\n".join(scripts) + text
        for pattern in patterns:
            for match in re.finditer(pattern, all_text):
                try:
                    if 'atob' in pattern:
                        b64_str = match.group(1)
                    elif 'data:' in pattern:
                        b64_str = match.group(2)
                    else:
                        b64_str = match.group(1)
                    decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                    if len(decoded) > 10:
                        base64_items.append({
                            "encoded": b64_str[:100] + (".." if len(b64_str) > 100 else ""),
                            "decoded": decoded,
                            "length": len(decoded)
                        })
                except Exception:
                    continue
        return base64_items

    def _extract_file_links(self) -> List[Dict[str, str]]:
        file_links = self.page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            const fileExtensions = ['.pdf', '.csv', '.xlsx', '.xls', '.json', '.txt', '.xml'];
            return links
                .map(a => ({ href: a.href, text: (a.textContent || '').trim() }))
                .filter(link => fileExtensions.some(ext => link.href.toLowerCase().includes(ext)));
        }""")
        return file_links or []

    def _extract_media_links(self) -> List[Dict[str, str]]:
        """
        Extract audio and video sources: <audio>, <video>, <source>, and plain links to media files.
        Returns list of {"url":..., "type":"audio"|"video", "text":...}
        """
        media = []
        # From <audio> and <video> tags
        try:
            media = self.page.evaluate("""() => {
                const out = [];
                const audios = Array.from(document.querySelectorAll('audio'));
                const videos = Array.from(document.querySelectorAll('video'));

                function collectMedia(el, kind) {
                    // direct src
                    if (el.src) out.push({url: el.src, type: kind, text: el.textContent || ''});
                    // <source> children
                    const sources = Array.from(el.querySelectorAll('source'));
                    for (const s of sources) {
                        if (s.src) out.push({url: s.src, type: kind, text: s.textContent || ''});
                    }
                }

                audios.forEach(a => collectMedia(a, 'audio'));
                videos.forEach(v => collectMedia(v, 'video'));

                // also inspect links for media file extensions
                const links = Array.from(document.querySelectorAll('a[href]'));
                const mediaExt = ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.mp4', '.mov', '.webm', '.mkv', '.avi'];
                links.map(a => ({href: a.href, text: (a.textContent||'').trim()})).forEach(l => {
                    const href = l.href.toLowerCase();
                    for (const ext of mediaExt) {
                        if (href.includes(ext)) {
                            const kind = ['.mp3','.wav','.m4a','.ogg','.flac'].includes(ext) ? 'audio' : 'video';
                            out.push({url: l.href, type: kind, text: l.text});
                            break;
                        }
                    }
                });

                return out;
            }""")
        except Exception:
            media = []
        return media or []

    def _extract_submit_url(self, html: str, text: str, base64_content: List[Dict]) -> Optional[str]:
        # existing implementation (keeps previous heuristics)...
        # look through decoded base64, text, html for a /submit or /submit endpoint
        current_url = self.page.url if self.page else ""
        for item in base64_content:
            decoded = item.get("decoded", "")
            submit_url = self._try_extract_url_from_text(decoded, current_url)
            if submit_url:
                return submit_url
        submit_url = self._try_extract_url_from_text(text, current_url)
        if submit_url:
            return submit_url
        submit_url = self._try_extract_url_from_text(html, current_url)
        if submit_url:
            return submit_url
        return None

    def _try_extract_url_from_text(self, text: str, base_url: str = "") -> Optional[str]:
        patterns = [
            r'https?://[^\s\'"<>]+/submit[^\s\'"<>]*',
            r'[Pp]ost\s+(?:your\s+)?(?:answer|response|solution)\s+(?:to|at)\s*:?\s*(https?://[^\s<>]+)',
            r'[Ss]ubmit\s+(?:your\s+)?(?:answer|response|solution)?\s+(?:to|at)\s*:?\s*(https?://[^\s<>]+)',
            r'POST\s+(?:to|at)\s*:?\s*(https?://[^\s<>]+)',
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                # if capture group present use it else full match
                url = m.group(1) if m.groups() else m.group(0)
                return url
        # try relative '/submit' on same host
        if "/submit" in text and base_url:
            from urllib.parse import urljoin
            return urljoin(base_url, "/submit")
        return None

    def _extract_quiz_structure(self, text_content: str, base64_content: List[Dict]) -> Dict[str, Any]:
        # Very small heuristic extractor (keeps your previous approach)
        return {
            "questions": [],
            "instructions": [],
            "question_text": text_content.strip()[:2000]
        }

    def _extract_tables(self) -> List[Dict[str, Any]]:
        # Basic table extraction via DOM -> text; more advanced handled elsewhere
        try:
            tables = self.page.evaluate("""() => {
                const out = [];
                const tables = Array.from(document.querySelectorAll('table'));
                for (const t of tables) {
                    const rows = Array.from(t.rows).map(r => Array.from(r.cells).map(c => c.innerText.trim()));
                    out.push({data: rows});
                }
                return out;
            }""")
            return tables or []
        except Exception:
            return []

