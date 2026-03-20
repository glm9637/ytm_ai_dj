"""Websocket API for AI DJ."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN

@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Set up the websocket API."""
    websocket_api.async_register_command(hass, ws_get_parties)
    websocket_api.async_register_command(hass, ws_create_party)
    websocket_api.async_register_command(hass, ws_update_party)
    websocket_api.async_register_command(hass, ws_delete_party)
    websocket_api.async_register_command(hass, ws_remove_history)
    websocket_api.async_register_command(hass, ws_clear_history)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ytm_ai_dj/parties/get",
    }
)
@websocket_api.async_response
async def ws_get_parties(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle get parties command."""
    store = hass.data[DOMAIN].get("store")
    if not store:
        connection.send_error(msg["id"], "not_ready", "Store not ready")
        return
        
    parties = store.get_parties()
    connection.send_result(msg["id"], parties)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ytm_ai_dj/parties/create",
        vol.Required("name"): str,
    }
)
@websocket_api.async_response
async def ws_create_party(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle create party command."""
    store = hass.data[DOMAIN].get("store")
    try:
        party = await store.create_party(msg["name"])
        connection.send_result(msg["id"], party)
    except Exception as err:
        connection.send_error(msg["id"], "create_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ytm_ai_dj/parties/update",
        vol.Required("party_id"): str,
        vol.Optional("vibe"): str,
        vol.Optional("start_time"): vol.Any(str, None),
        vol.Optional("end_time"): vol.Any(str, None),
        vol.Optional("active"): bool,
    }
)
@websocket_api.async_response
async def ws_update_party(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle update party command."""
    store = hass.data[DOMAIN].get("store")
    updates = {}
    for key in ["vibe", "start_time", "end_time", "active"]:
        if key in msg:
            updates[key] = msg[key]
            
    try:
        party = await store.update_party(msg["party_id"], updates)
        connection.send_result(msg["id"], party)
    except Exception as err:
        connection.send_error(msg["id"], "update_failed", str(err))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "ytm_ai_dj/parties/delete",
        vol.Required("party_id"): str,
    }
)
@websocket_api.async_response
async def ws_delete_party(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle delete party command."""
    store = hass.data[DOMAIN].get("store")
    try:
        await store.delete_party(msg["party_id"])
        connection.send_result(msg["id"], {"success": True})
    except Exception as err:
        connection.send_error(msg["id"], "delete_failed", str(err))
        
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ytm_ai_dj/history/delete",
        vol.Required("party_id"): str,
        vol.Required("index"): int,
    }
)
@websocket_api.async_response
async def ws_remove_history(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle remove history item command."""
    store = hass.data[DOMAIN].get("store")
    try:
        await store.remove_from_history(msg["party_id"], msg["index"])
        # Return updated party
        party = store.parties.get(msg["party_id"])
        connection.send_result(msg["id"], party)
    except Exception as err:
        connection.send_error(msg["id"], "delete_failed", str(err))
        
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ytm_ai_dj/history/clear",
        vol.Required("party_id"): str,
    }
)
@websocket_api.async_response
async def ws_clear_history(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Handle clear party history command."""
    store = hass.data[DOMAIN].get("store")
    try:
        await store.clear_history(msg["party_id"])
        party = store.parties.get(msg["party_id"])
        connection.send_result(msg["id"], party)
    except Exception as err:
        connection.send_error(msg["id"], "clear_failed", str(err))
