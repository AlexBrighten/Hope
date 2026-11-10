"""Brain Layer for Hope UltraLight:
Coordinates Local Ollama, Free OpenRouter (Inkling 2 Small), and Gemini 2.5 Flash fallback.
"""

from brain.router import router, RouteDecision
from brain.providers import provider_manager

__all__ = ["router", "RouteDecision", "provider_manager"]

