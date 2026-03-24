

import json
import logging
from typing import override

from custom_components.mass_ai_dj.backend.llm.llm_provider import LLMProvider
from custom_components.mass_ai_dj.backend.model import Song

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class GeminiProvider(LLMProvider):
    def __init__(self, hass: HomeAssistant, api_key: str):
        self.hass = hass
        self.api_key = api_key

    @override
    async def _query_llm(self, prompt: str) -> Song:
        
        session = async_get_clientsession(self.hass)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}} # type: ignore

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    _LOGGER.error("Gemini API error: %s", await response.text())
                    raise ValueError("Gemini API error")
                response_data = await response.json()
                response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                
            parsed_data = json.loads(response_text)
            artist = parsed_data.get("artist", "")
            title = parsed_data.get("title", "")
            _LOGGER.info("AI DJ Selected: %s by %s", title, artist)
            return Song(title=title, artist=artist)
        except Exception as err:
            _LOGGER.error("Failed to query Gemini: %s", err)
            raise err
