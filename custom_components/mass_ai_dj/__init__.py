"""The AI DJ integration."""
from __future__ import annotations

import logging
_LOGGER = logging.getLogger(__name__)

import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import  HomeAssistant
from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig


from .backend.const import (
    DOMAIN,
    CONF_PROVIDER,
    CONF_GEMINI_API_KEY,
    CONF_OLLAMA_URL,
    CONF_OLLAMA_MODEL,
    PROVIDER_GEMINI,
    PROVIDER_OLLAMA,
)

from .backend.llm.llm_provider import LLMProvider
from .backend.store import PartyStore
from .backend.dj_engine import DJEngine
from .backend.llm.gemini_provider import GeminiProvider
from .backend.llm.ollama_provider import OllamaProvider
from .backend.api.websocket_api import async_setup_websocket_api

PLATFORMS: list[str] = []

def get_provider(hass: HomeAssistant, entry: ConfigEntry) -> LLMProvider:
    """Factory method to return the correct LLM Provider based on the config."""
    
    provider_name = entry.data.get(CONF_PROVIDER, PROVIDER_GEMINI)
    if provider_name == PROVIDER_GEMINI:
        return GeminiProvider(hass, entry.data[CONF_GEMINI_API_KEY])
    elif provider_name == PROVIDER_OLLAMA:
        return OllamaProvider(hass, entry.data[CONF_OLLAMA_URL], entry.data[CONF_OLLAMA_MODEL])
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    
async def setup_frontend(hass: HomeAssistant) -> None:
    """Set up the frontend resources and panel."""
    async_setup_websocket_api(hass)
        
    frontend_path = hass.config.path("custom_components/mass_ai_dj/frontend")
    os.makedirs(frontend_path, exist_ok=True)
            
    await hass.http.async_register_static_paths([
        StaticPathConfig("/mass_ai_dj_frontend", frontend_path, False)
    ])
        
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path="ai-dj",
        webcomponent_name="mass-ai-dj-panel",
        sidebar_title="AI DJ",
        sidebar_icon="mdi:music-box-multiple",
        module_url="/mass_ai_dj_frontend/mass-ai-dj-panel.js?v=2",
        trust_external=False,
    )
    
async def setup_store(hass: HomeAssistant) -> None:
    store = PartyStore(hass)
    await store.async_load()
    hass.data[DOMAIN]["store"] = store
    

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up AI DJ from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    try:
        llm_provider = get_provider(hass, entry)
    except ValueError as e:
        _LOGGER.error("Error setting up AI DJ: %s", e)
        return False

    if "store" not in hass.data[DOMAIN]:
        await setup_store(hass)
        await setup_frontend(hass)

    engine = DJEngine(hass, llm_provider)
    hass.data[DOMAIN][entry.entry_id] = engine
    engine.start()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if engine := hass.data[DOMAIN].get(entry.entry_id):
        engine.stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok