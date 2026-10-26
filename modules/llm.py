"""Thin LLM client for Gemini and Groq using plain REST (no SDK drift).

Provider "Demo" (or a missing key) switches the app to standalone demo mode.
"""
import requests

from .utils import extract_json, image_to_b64

GEMINI_DEFAULT_MODEL = "gemini-2.0-flash"
GROQ_DEFAULT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM_PROMPT = (
    "You are an expert food scientist, dietitian and food-safety auditor. "
    "Respond with ONLY a single valid JSON object that follows the requested schema. "
    "Be honest about uncertainty; all numbers are estimates."
)


class LLMError(Exception):
    """Raised when the provider call fails."""


class LLMClient:
    def __init__(self, provider: str = "Demo", api_key: str = "", model: str = ""):
        self.provider = provider
        self.api_key = (api_key or "").strip()
        if provider == "Gemini":
            self.model = model or GEMINI_DEFAULT_MODEL
        elif provider == "Groq":
            self.model = model or GROQ_DEFAULT_MODEL
        else:
            self.model = ""

    @property
    def is_demo(self) -> bool:
        return self.provider not in ("Gemini", "Groq") or not self.api_key

    def generate_json(self, prompt: str, images=None) -> dict:
        images = images or []
        try:
            if self.provider == "Gemini":
                text = self._gemini(prompt, images)
            elif self.provider == "Groq":
                text = self._groq(prompt, images)
            else:
                raise LLMError("No provider configured.")
        except requests.Timeout as exc:
            raise LLMError("The AI provider timed out. Please try again.") from exc
        except requests.RequestException as exc:
            raise LLMError(f"Network error talking to {self.provider}: {exc}") from exc
        try:
            return extract_json(text)
        except ValueError as exc:
            raise LLMError("The model returned an unreadable answer. Try again.") from exc

    # -- providers ---------------------------------------------------------
    def _gemini(self, prompt, images) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        parts = [{"text": SYSTEM_PROMPT + "\n\n" + prompt}]
        for img in images:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_to_b64(img)}})
        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"},
        }
        r = requests.post(url, params={"key": self.api_key}, json=body, timeout=90)
        if r.status_code != 200:
            raise LLMError(self._http_error(r))
        data = r.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Gemini returned no content (the request may have been blocked).") from exc

    def _groq(self, prompt, images) -> str:
        content = [{"type": "text", "text": prompt}]
        for img in images[:5]:
            content.append(
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + image_to_b64(img)}}
            )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content if images else prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
            timeout=90,
        )
        if r.status_code != 200:
            raise LLMError(self._http_error(r))
        try:
            return r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Groq returned no content.") from exc

    def _http_error(self, r) -> str:
        try:
            msg = r.json().get("error", {})
            msg = msg.get("message", "") if isinstance(msg, dict) else str(msg)
        except ValueError:
            msg = r.text[:200]
        hint = ""
        if r.status_code in (400, 401, 403):
            hint = " Check your API key and model name."
        elif r.status_code == 429:
            hint = " Rate limit reached; wait a moment."
        return f"{self.provider} error {r.status_code}: {msg}{hint}"
