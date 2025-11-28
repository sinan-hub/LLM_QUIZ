"""LLM Prompt Challenge module for testing code word protection."""
import random
import string
from typing import Dict, Any, Optional
import httpx
from prompts import (
    get_system_prompt, get_user_prompt,
    list_system_prompt_templates, list_user_prompt_templates,
    SYSTEM_PROMPTS, USER_PROMPTS
)


def generate_random_code_word(length: int = 12) -> str:
    """Generate a random code word for testing."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def create_system_prompt(code_word: str, template: str = "basic") -> str:
    """Create a system prompt that protects the secret code word."""
    return get_system_prompt(template, code_word)


def create_user_prompt_extraction_attempt(template: str = "direct") -> str:
    """Create a user prompt that attempts to extract the code word."""
    return get_user_prompt(template)


def test_prompt_challenge(
    system_prompt: str,
    user_prompt: str,
    api_url: str,
    api_key: str = None,
    model: str = "openai/gpt-4"
) -> Dict[str, Any]:
    """
    Test the prompt challenge by sending both prompts to the LLM.
    
    Returns:
        Dictionary with test results including response, code_word_detected, etc.
    """
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            assistant_message = result["choices"][0]["message"]["content"]
            
            # Check if code word was revealed (basic check)
            code_word_detected = False
            # Extract code word from system prompt for comparison
            # This is a simplified check - in production, use more sophisticated detection
            code_word = ""
            if "code word is:" in system_prompt.lower():
                parts = system_prompt.split("code word is:")
                if len(parts) > 1:
                    code_word = parts[1].strip().split("\n")[0].strip()
                    code_word_detected = code_word.lower() in assistant_message.lower()
            
            return {
                "success": True,
                "response": assistant_message,
                "code_word_detected": code_word_detected,
                "code_word": code_word,
                "model_used": model,
                "full_response": result
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": None,
            "code_word_detected": False
        }


def run_challenge_test(api_url: str, api_key: str = None, 
                      code_word: str = None,
                      system_template: str = "basic",
                      user_template: str = "direct") -> Dict[str, Any]:
    """
    Run a complete challenge test with random code word.
    
    Args:
        api_url: The AIPIPE/OpenRouter API URL
        api_key: Optional API key
        code_word: Optional code word (generated if not provided)
        system_template: System prompt template name (default: "basic")
        user_template: User prompt template name (default: "direct")
    
    Returns:
        Complete test results
    """
    if not code_word:
        code_word = generate_random_code_word()
    
    system_prompt = create_system_prompt(code_word, system_template)
    user_prompt = create_user_prompt_extraction_attempt(user_template)
    
    test_result = test_prompt_challenge(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        api_url=api_url,
        api_key=api_key
    )
    
    return {
        "code_word": code_word,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "system_template": system_template,
        "user_template": user_template,
        "test_result": test_result
    }