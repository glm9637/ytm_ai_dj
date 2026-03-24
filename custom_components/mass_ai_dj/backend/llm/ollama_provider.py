"""Ollama API integration for AI DJ."""
from __future__ import annotations

import json
import logging
from typing import Any, override

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.mass_ai_dj.backend.model import Song

from .llm_provider import LLMProvider

_LOGGER = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """LLM Provider implementation for local Ollama instances."""

    def __init__(self, hass: HomeAssistant, url: str, model: str) -> None:
        """Initialize the Ollama provider."""
        self.hass = hass
        self.url = url.rstrip("/")
        self.model = model

    @override
    async def _query_llm(self, prompt: str) -> Song:
        """Query the local Ollama instance and return a parsed Song."""
        session = async_get_clientsession(self.hass)
        endpoint = f"{self.url}/api/generate"
        
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json" 
        }

        response_text = ""
        try:
            async with session.post(endpoint, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Ollama API error (%s): %s", response.status, error_text)
                    raise ValueError(f"Ollama API returned status {response.status}")
                
                response_data: dict[str, Any] = await response.json()
                response_text: str = response_data.get("response", "")
                
            parsed_data: dict[str, Any] = json.loads(response_text)
            
            artist = str(parsed_data.get("artist", "Unknown Artist")).strip()
            title = str(parsed_data.get("title", "Unknown Title")).strip()
            
            if not artist or not title:
                raise ValueError("Ollama returned empty artist or title.")
            
            _LOGGER.info("[Ollama - %s] Selected: %s by %s", self.model, title, artist)
            return Song(title=title, artist=artist)

        except json.JSONDecodeError as err:
            _LOGGER.error("Ollama failed to return valid JSON: %s. Raw output: %s", err, response_text)
            raise ValueError("Invalid JSON from Ollama") from err
            
        except Exception as err:
            _LOGGER.error("Failed to query Ollama: %s", err)
            raise