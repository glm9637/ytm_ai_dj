"""Config flow for AI DJ integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from ytmusicapi import YTMusic
import google.generativeai as genai

from .const import DOMAIN, CONF_GEMINI_API_KEY, CONF_YTM_HEADERS

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GEMINI_API_KEY): str,
        vol.Required(CONF_YTM_HEADERS): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    
    # 1. Validate Gemini
    gemini_key = data[CONF_GEMINI_API_KEY]
    try:
        def test_gemini():
            genai.configure(api_key=gemini_key)
            # Try doing a simple model list to validate the key
            models = list(genai.list_models())
            if not models:
                raise ValueError("No generative models found, key may be invalid")
        
        await hass.async_add_executor_job(test_gemini)
    except Exception as err:
        _LOGGER.error("Gemini API Key validation failed: %s", err)
        raise InvalidGeminiKey from err

    # 2. Validate YTM
    ytm_headers_str = data[CONF_YTM_HEADERS]
    try:
        def test_ytm():
            # YTMusic takes the raw headers string in setup
            ytm = YTMusic(auth=ytm_headers_str)
            # Try fetching the library or history to confirm it is valid
            # auth required endpoints will fail if auth is bad
            ytm.get_library_songs(limit=1)
        
        await hass.async_add_executor_job(test_ytm)
    except Exception as err:
        _LOGGER.error("YTMusic Auth Validation failed: %s", err)
        raise InvalidYTMHeaders from err

    # Return info that you want to store in the config entry.
    return {"title": "AI DJ"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for AI DJ."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id("ai_dj_integration")
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except InvalidGeminiKey:
                errors["base"] = "invalid_gemini_key"
            except InvalidYTMHeaders:
                errors["base"] = "invalid_ytm_headers"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class InvalidGeminiKey(HomeAssistantError):
    """Error to indicate there is an invalid Gemini API key."""


class InvalidYTMHeaders(HomeAssistantError):
    """Error to indicate there are invalid YouTube Music headers."""
