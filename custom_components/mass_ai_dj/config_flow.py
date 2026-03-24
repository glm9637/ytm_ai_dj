"""Config flow for AI DJ integration."""
from __future__ import annotations

import logging
from typing import Any, override

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, Mapping
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .backend.const import (
    DOMAIN,
    CONF_PROVIDER,
    CONF_GEMINI_API_KEY,
    CONF_OLLAMA_URL,
    CONF_OLLAMA_MODEL,
    PROVIDER_GEMINI,
    PROVIDER_OLLAMA,
)

_LOGGER = logging.getLogger(__name__)

async def validate_gemini(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the Gemini API key via REST API."""
    gemini_key = data[CONF_GEMINI_API_KEY]
    session = async_get_clientsession(hass)
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
    
    try:
        async with session.get(gemini_url) as response:
            if response.status != 200:
                error_data = await response.text()
                _LOGGER.error("Gemini API rejected key: %s", error_data)
                raise InvalidAuth
    except InvalidAuth:
        raise
    except Exception as err:
        _LOGGER.error("Gemini connection failed: %s", err)
        raise CannotConnect from err

    return {"title": "AI DJ (Gemini)"}

async def validate_ollama(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate the Ollama URL and verify the model is downloaded."""
    url = data[CONF_OLLAMA_URL].rstrip("/")
    model = data[CONF_OLLAMA_MODEL]
    session = async_get_clientsession(hass)
    tags_url = f"{url}/api/tags"
    
    try:
        async with session.get(tags_url) as response:
            if response.status != 200:
                raise CannotConnect
            
            result = await response.json()
            models = [m.get("name") for m in result.get("models", [])]
            
            # Ollama often appends ':latest' to model names if not specified
            if model not in models and f"{model}:latest" not in models:
                _LOGGER.error("Ollama model '%s' not found. Available: %s", model, models)
                raise InvalidModel
                
    except InvalidModel:
        raise
    except Exception as err:
        _LOGGER.error("Ollama connection failed: %s", err)
        raise CannotConnect from err

    return {"title": f"AI DJ ({model})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI DJ."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow state."""
        self.provider: str | None = None

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Ask the user to select their AI Provider."""
        if user_input is not None:
            self.provider = user_input[CONF_PROVIDER]
            if self.provider == PROVIDER_GEMINI:
                return await self.async_step_gemini()
            return await self.async_step_ollama()

        schema = vol.Schema({
            vol.Required(CONF_PROVIDER, default=PROVIDER_GEMINI): vol.In([PROVIDER_GEMINI, PROVIDER_OLLAMA])
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_gemini(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2A: Collect and validate Gemini credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_gemini(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                data: Mapping[str, str | None] = {CONF_PROVIDER: self.provider, **user_input}
                return self.async_create_entry(title=info["title"], data=data)

        schema = vol.Schema({vol.Required(CONF_GEMINI_API_KEY): str})
        return self.async_show_form(
            step_id="gemini", data_schema=schema, errors=errors
        )

    async def async_step_ollama(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2B: Collect and validate Ollama credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_ollama(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidModel:
                errors["base"] = "invalid_model"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                data: Mapping[str, str | None] = {CONF_PROVIDER: self.provider, **user_input}
                return self.async_create_entry(title=info["title"], data=data)

        schema = vol.Schema({
            vol.Required(CONF_OLLAMA_URL, default="http://localhost:11434"): str,
            vol.Required(CONF_OLLAMA_MODEL, default="llama3"): str
        })
        return self.async_show_form(
            step_id="ollama", data_schema=schema, errors=errors
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class InvalidModel(HomeAssistantError):
    """Error to indicate the requested Ollama model is not downloaded."""