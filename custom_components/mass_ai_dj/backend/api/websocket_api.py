"""Websocket API for AI DJ."""
from __future__ import annotations

from dataclasses import asdict
from typing import cast

import voluptuous as vol

from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from ..model import PartyUpdate, VibeSession

from ..const import DOMAIN
from ..store import PartyStore 
from . import dto
from . import api_schema


@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Set up the websocket API."""
    async_register_command(hass, ws_get_parties)
    async_register_command(hass, ws_create_party)
    async_register_command(hass, ws_update_party)
    async_register_command(hass, ws_delete_party)
    async_register_command(hass, ws_remove_history)
    async_register_command(hass, ws_clear_history)
    async_register_command(hass, websocket_get_players)


@websocket_command(api_schema.GET_PARTIES_SCHEMA)
@async_response
async def ws_get_parties(
    hass: HomeAssistant, connection: ActiveConnection, raw_msg: dict[str, vol.Any]
) -> None:
    """Handle get parties command."""
    msg  = cast(dto.GetPartiesMsg, raw_msg)
    store = cast(PartyStore | None, hass.data[DOMAIN].get("store"))
    if not store:
        connection.send_error(msg["id"], "not_ready", "Store not ready")
        return
        
    # Convert Dataclasses to Dicts for JSON serialization
    parties = [asdict(p) for p in store.get_parties()]
    connection.send_result(msg["id"], parties)


@websocket_command(api_schema.GET_PLAYERS_SCHEMA)
@async_response
async def websocket_get_players(
    hass: HomeAssistant, connection: ActiveConnection, raw_msg: dict[str, vol.Any]
) -> None:
    """Returns ONLY players created by the Music Assistant integration."""
        
    msg  = cast(dto.GetPlayersMsg, raw_msg)
    try:
        players : list[dict[str, str]]= []
        states = hass.states.async_all("media_player")
        registry = er.async_get(hass)
        
        for state in states:
            entity_id = state.entity_id
            entry = registry.async_get(entity_id)
            
            if entry and entry.platform == "music_assistant":
                attrs = dict(state.attributes) #type: ignore
                friendly_name = attrs.get("friendly_name", entity_id)
                
                players.append({
                    "entity_id": entity_id,
                    "name": friendly_name
                })
                
        connection.send_result(int(msg["id"]), players)
    except Exception as err:
        connection.send_error(int(msg["id"]), "get_players_failed", str(err))
        

@websocket_command(api_schema.CREATE_PARTY_SCHEMA)
@async_response
async def ws_create_party(
    hass: HomeAssistant, connection: ActiveConnection, raw_msg: dict[str, vol.Any]
) -> None:
    """Handle create party command."""
    
    msg  = cast(dto.CreatePartyMsg, raw_msg)
    store = cast(PartyStore, hass.data[DOMAIN].get("store"))
    try:
        party = await store.create_party(msg["name"])
        connection.send_result(int(msg["id"]), asdict(party))
    except Exception as err:
        connection.send_error(int(msg["id"]), "create_failed", str(err))


@websocket_command(api_schema.UPDATE_PARTY_SCHEMA)
@async_response
async def ws_update_party(
    hass: HomeAssistant, connection: ActiveConnection, raw_msg: dict[str, vol.Any]
) -> None:
    """Handle update party command."""
    
    msg  = cast(dto.UpdatePartyMsg, raw_msg)
    store = cast(PartyStore, hass.data[DOMAIN].get("store"))
    updates: PartyUpdate = PartyUpdate()
    if "sessions" in msg:
        updates.sessions = []
        for session in msg["sessions"]:
            updates.sessions.append(VibeSession(
                vibe=session["vibe"], 
                from_date= dt_util.parse_datetime(session["from_date"]), 
                to_date=dt_util.parse_datetime(session["to_date"])
            ))
    if "media_player_id" in msg:
        updates.media_player_id = msg["media_player_id"]
    if "active" in msg:
        updates.active = msg["active"]
        
            
    try:
        party = await store.update_party(msg["party_id"], updates)
        if updates.active is True:
            hass.bus.async_fire("mass_ai_dj_force_poll")
            
        connection.send_result(int(msg["id"]), asdict(party))
    except Exception as err:
        connection.send_error(int(msg["id"]), "update_failed", str(err))


@websocket_command(api_schema.DELETE_PARTY_SCHEMA)
@async_response
async def ws_delete_party(
    hass: HomeAssistant, connection: ActiveConnection, raw_msg: dict[str, vol.Any]
) -> None:
    """Handle delete party command."""
    
    msg  = cast(dto.DeletePartyMsg, raw_msg)
    store = cast(PartyStore, hass.data[DOMAIN].get("store"))
    try:
        await store.delete_party(msg["party_id"])
        connection.send_result(int(msg["id"]), {"success": True})
    except Exception as err:
        connection.send_error(int(msg["id"]), "delete_failed", str(err))
        

@websocket_command(api_schema.REMOVE_FROM_HISTORY_SCHEMA)
@async_response
async def ws_remove_history(
    hass: HomeAssistant, connection: ActiveConnection, raw_msg: dict[str, vol.Any]
) -> None:
    """Handle remove history item command."""
    
    msg  = cast(dto.RemoveFromHistoryMsg, raw_msg)
    store = cast(PartyStore, hass.data[DOMAIN].get("store"))
    try:
        await store.remove_from_history(msg["party_id"], msg["index"])
        party = store.parties.get(msg["party_id"])
        if party:
            connection.send_result(int(msg["id"]), asdict(party))
    except Exception as err:
        connection.send_error(int(msg["id"]), "delete_failed", str(err))
        

@websocket_command(api_schema.CLEAR_HISTORY_SCHEMA)
@async_response
async def ws_clear_history(
    hass: HomeAssistant, connection: ActiveConnection, dto: dict[str, vol.Any]
) -> None:
    """Handle clear party history command."""
    
    msg  = cast(dto.ClearHistoryMsg, dto)
    store = cast(PartyStore, hass.data[DOMAIN].get("store"))
    try:
        await store.clear_history(msg["party_id"])
        party = store.parties.get(msg["party_id"])
        if party:
            connection.send_result(int(msg["id"]), asdict(party))
    except Exception as err:
        connection.send_error(int(msg["id"]), "clear_failed", str(err))