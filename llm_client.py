"""
llm_client.py
Thin wrapper around free-tier LLM APIs (Groq and Gemini).
API keys are passed in at call time from the Streamlit UI / sidebar —
nothing is hardcoded here. See .env.example for local dev key names.
"""

import requests


def call_groq(prompt: str, api_key: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Calls Groq's OpenAI-compatible chat completions endpoint.
    Get a free key at https://console.groq.com
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 4000,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def call_gemini(prompt: str, api_key: str, model: str = "gemini-2.0-flash") -> str:
    """
    Calls Google's Gemini generateContent endpoint.
    Get a free key at https://aistudio.google.com/apikey
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = requests.post(url, json=body, timeout=60)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def generate(provider: str, api_key: str, prompt: str) -> str:
    """Single entry point the app calls — routes to whichever provider is selected."""
    if not api_key:
        raise ValueError("No API key provided.")

    if provider == "groq":
        return call_groq(prompt, api_key)
    elif provider == "gemini":
        return call_gemini(prompt, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")
