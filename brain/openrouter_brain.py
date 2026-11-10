"""Tier 2: OpenRouter Client (Inkling 2 Small Free Cloud Workhorse)
Handles public web research, code generation, long documents, and multi-step tool execution.
"""

import logging
import json
from typing import List, Dict, Any, Optional
import httpx
from config import config

logger = logging.getLogger(__name__)


class OpenRouterBrain:
    def __init__(self):
        self.base_url = config.openrouter_base_url
        self.api_key = config.openrouter_api_key
        self.model = config.openrouter_model
        self.timeout = 45.0

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("sk-or-v1-xxxx"))

    async def check_health(self) -> Dict[str, Any]:
        if not self.is_configured():
            return {"online": False, "model": self.model, "configured": False, "error": "API key missing"}
        return {"online": True, "model": self.model, "configured": True}

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        effort: str = "low",
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute chat turn against OpenRouter OpenAI-compatible endpoint."""
        if not self.is_configured():
            raise ValueError("OpenRouter API key is not configured in .env")

        formatted_messages = list(messages)
        if system_prompt:
            formatted_messages.insert(0, {"role": "system", "content": system_prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.2,
        }

        # Reasoning effort for MoE model
        if effort in ("low", "medium", "high"):
            payload["reasoning"] = {"effort": effort}

        if tools:
            payload["tools"] = tools

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/hope-agent/hope",
            "X-Title": "Hope UltraLight Executive Agent",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()

            choices = data.get("choices", [])
            if not choices:
                raise ValueError("Empty response from OpenRouter")

            message = choices[0].get("message", {})
            content = message.get("content", "") or ""
            raw_tool_calls = message.get("tool_calls", [])

            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                args = func.get("arguments", "{}")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"raw_args": args}
                tool_calls.append({
                    "name": func.get("name"),
                    "arguments": args
                })

            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            return {
                "provider": "openrouter",
                "model": self.model,
                "content": content,
                "tool_calls": tool_calls,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }


openrouter_brain = OpenRouterBrain()

