"""Tier 3: Google Gemini Client (Gemini 2.5 Flash Fallback & Voice Notes)
Lightweight REST client using httpx without heavy grpc dependencies.
"""

import logging
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx
from config import config

logger = logging.getLogger(__name__)


class GeminiBrain:
    def __init__(self):
        self.api_key = config.gemini_api_key
        self.model = config.gemini_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.timeout = 40.0

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("AIzaSyxxxx"))

    async def check_health(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {"online": False, "model": self.model, "configured": False, "error": "API key missing"}
        return {"online": True, "model": self.model, "configured": True}

    def _convert_openai_tools_to_gemini(self, openai_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert OpenAI tool schemas to Gemini functionDeclarations."""
        declarations = []
        for t in openai_tools:
            func = t.get("function", {})
            declarations.append({
                "name": func.get("name"),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {"type": "object", "properties": {}})
            })
        return [{"functionDeclarations": declarations}]

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute chat turn against Gemini 2.5 Flash REST API."""
        if not self.is_configured():
            raise ValueError("Gemini API key is not configured in .env")

        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            content = m.get("content", "")
            if content:
                contents.append({"role": role, "parts": [{"text": content}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            }
        }

        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        if tools:
            payload["tools"] = self._convert_openai_tools_to_gemini(tools)

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()

            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidate received from Gemini")

            parts = candidates[0].get("content", {}).get("parts", [])
            text_chunks = []
            tool_calls = []

            for p in parts:
                if "text" in p:
                    text_chunks.append(p["text"])
                if "functionCall" in p:
                    fc = p["functionCall"]
                    tool_calls.append({
                        "name": fc.get("name"),
                        "arguments": fc.get("args", {})
                    })

            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)

            return {
                "provider": "gemini",
                "model": self.model,
                "content": "".join(text_chunks),
                "tool_calls": tool_calls,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }

    async def transcribe_audio(self, audio_path: Path) -> str:
        """Transcribe an audio voice note using Gemini multimodal capability."""
        if not self.is_configured():
            raise ValueError("Gemini API key is required to transcribe audio")

        audio_bytes = audio_path.read_bytes()
        mime_type = "audio/ogg" if audio_path.suffix.lower() in (".oga", ".ogg") else "audio/mp3"
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "contents": [{
                "parts": [
                    {"text": "Transcribe this voice message accurately into plain text. Only return the transcription, nothing else."},
                    {"inlineData": {"mimeType": mime_type, "data": b64_audio}}
                ]
            }]
        }

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                return text.strip()
            return ""


gemini_brain = GeminiBrain()

