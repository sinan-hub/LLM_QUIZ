# /mnt/data/llm_analyzer.py
# REPLACE YOUR ENTIRE llm_analyzer.py FILE WITH THIS

import httpx
import json
from typing import Dict, Any, Optional

class LLMAnalyzer:
    def __init__(self, api_url: str, api_key: str = None, model: str = "openai/gpt-4o-mini"):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    async def _call_llm(self, messages: list, max_tokens: int = 1000, temperature: float = 0.0) -> Dict[str, Any]:
        payload = {
            "model": self.model, 
            "messages": messages, 
            "max_tokens": max_tokens, 
            "temperature": temperature
        }
        async with httpx.AsyncClient(timeout=60.0) as client:  # Increased timeout
            resp = await client.post(f"{self.api_url}/chat/completions", headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    async def extract_data_from_content(self, content: str, extraction_type: str = "generic") -> Dict[str, Any]:
        system = f"You are an assistant that extracts {extraction_type} from the content. Return JSON."
        messages = [{"role":"system", "content": system}, {"role":"user", "content": content}]
        try:
            resp = await self._call_llm(messages)
            choices = resp.get("choices", [])
            if not choices:
                return {"success": False, "error": "No choices in LLM response", "raw": resp}
            assistant = choices[0].get("message", {}).get("content", "")
            try:
                parsed = json.loads(assistant)
                return {"success": True, "result": parsed, "raw": assistant}
            except Exception:
                return {"success": True, "result": assistant, "raw": assistant}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def analyze_quiz_question(self, question_text: str, context: dict, options: list = []) -> Dict[str, Any]:
        """
        Analyze a quiz question and return the answer.
        
        This method builds a comprehensive prompt that:
        1. Extracts the actual question from instructions
        2. Uses provided context (files, tables, data)
        3. Returns ONLY the final answer (number, string, etc.)
        """
        
        # Build a very clear, structured prompt
        system_prompt = """You are a data analysis expert solving quiz questions. 

CRITICAL INSTRUCTIONS:
1. Read the question carefully and identify what is being asked
2. If a file needs to be downloaded, use the file data provided in the context
3. Perform any necessary calculations, aggregations, or analysis
4. Return ONLY the final answer in your response
5. Do NOT return instructions, do NOT return explanations unless asked
6. If the question asks for a number, return ONLY the number
7. If the question asks for text, return ONLY that text
8. If the question asks for a chart, describe what chart to create

Examples:
- Question: "What is the sum of column X?" → Answer: "12345"
- Question: "What is the average?" → Answer: "45.67"
- Question: "Which city has the highest sales?" → Answer: "New York"
"""

        user_prompt = f"""Question to solve:
{question_text}

Context and Data:
{json.dumps(context, indent=2)[:12000]}

Analyze the above and provide ONLY the final answer. Do not include explanations, do not include the question, just the answer."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            resp = await self._call_llm(messages, max_tokens=1000, temperature=0.1)
            assistant = resp["choices"][0]["message"]["content"].strip()
            
            # Try to clean up the response
            # Remove markdown code blocks if present
            if assistant.startswith("```"):
                lines = assistant.split("\n")
                # Remove first and last lines if they're markdown
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                assistant = "\n".join(lines).strip()
            
            # Try to parse as JSON
            try:
                parsed = json.loads(assistant)
                if isinstance(parsed, dict) and "answer" in parsed:
                    # Extract just the answer
                    return {"success": True, "result": parsed["answer"], "raw": assistant, "full_response": parsed}
                return {"success": True, "result": parsed, "raw": assistant}
            except:
                # Not JSON, return as-is
                return {"success": True, "result": assistant, "raw": assistant}
                
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}