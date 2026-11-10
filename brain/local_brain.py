"""Tier 1: Local Ollama Client (Qwen 2.5 3B Instruct)
Handles privacy-sensitive data, offline chat, and local tool calling with zero cloud tokens.
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
from config import config

logger = logging.getLogger(__name__)


class LocalBrain:
    def __init__(self):
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model
        self.deep_model = config.ollama_deep_model
        self.timeout = config.ollama_timeout
        self.keep_alive = config.ollama_keep_alive

    async def check_health(self) -> Dict[str, Any]:
        """Verify Ollama is reachable and list installed models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    is_model_present = any(self.model in m for m in models)
                    return {
                        "online": True,
                        "model": self.model,
                        "installed": is_model_present,
                        "available_models": models
                    }
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
        return {"online": False, "model": self.model, "installed": False, "available_models": []}

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        use_deep_model: bool = False,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute chat turn against local Ollama instance with optional tool calling."""
        selected_model = self.deep_model if use_deep_model else self.model
        formatted_messages = list(messages)
        if system_prompt:
            formatted_messages.insert(0, {"role": "system", "content": system_prompt})

        payload: Dict[str, Any] = {
            "model": selected_model,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "num_ctx": 4096,
                "temperature": 0.3
            },
            "keep_alive": self.keep_alive
        }

        if tools:
            # Ollama supports OpenAI-standard tools format
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()

            message = data.get("message", {})
            content = message.get("content", "")
            raw_tool_calls = message.get("tool_calls", [])

            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                tool_calls.append({
                    "name": func.get("name"),
                    "arguments": func.get("arguments", {})
                })

            prompt_eval_count = data.get("prompt_eval_count", 0)
            eval_count = data.get("eval_count", 0)

            return {
                "provider": "ollama",
                "model": selected_model,
                "content": content,
                "tool_calls": tool_calls,
                "prompt_tokens": prompt_eval_count,
                "completion_tokens": eval_count
            }


local_brain = LocalBrain()

