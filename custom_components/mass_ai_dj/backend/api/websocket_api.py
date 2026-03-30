"""Websocket API for AI DJ."""
from __future__ import annotations

from dataclasses import asdict
from typing import cast

import voluptuous as vol

from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.decorators import async_response, websocket_command
from homeassistant.core import HomeAssistant, callback
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
    """Returns ONLY players from Music Assistant."""
        
    msg  = cast(dto.GetPlayersMsg, raw_msg)
    try:
        players : list[dict[str, str]]= []
        mass_data = hass.data.get("music_assistant")
        
        if not mass_data:
            connection.send_error(int(msg["id"]), "get_players_failed", "Music Assistant integration not loaded")
            return
            
        if isinstance(mass_data, dict):
            mass_client = next(iter(mass_data.values()), None) //#type: ignore
            if mass_client is not None and hasattr(mass_client, "client"): //#type: ignore
                mass_client = mass_client.client //#type: ignore
        else:
            mass_client = mass_data
            
        if not mass_client:
            connection.send_error(int(msg["id"]), "get_players_failed", "Music Assistant client not found")
            return
            
        # Request all players directly from the MA server
        ma_players = await mass_client.connection.send_command("players/all") //#type: ignore
        
        for player in ma_players: //#type: ignore
            players.append({ //#type: ignore
                "entity_id": player.get("player_id"),
                "name": player.get("name", "Unknown Player")
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