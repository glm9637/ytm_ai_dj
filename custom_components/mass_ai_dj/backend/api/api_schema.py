
import voluptuous as vol

from homeassistant.helpers.typing import VolDictType

UPDATE_PARTY_SCHEMA: VolDictType = {
    vol.Required("type"): "mass_ai_dj/parties/update",
    vol.Required("party_id"): str,
    vol.Optional("sessions"): [
        {
            vol.Required("vibe"): str,
            vol.Required("from_date"): str,
            vol.Required("to_date"): str,
        }
    ],
    vol.Optional("media_player_id"): str,
    vol.Optional("active"): bool,
}

GET_PARTIES_SCHEMA: VolDictType = {
    vol.Required("type"): "mass_ai_dj/parties/get",
}

GET_PLAYERS_SCHEMA: VolDictType = { 
    vol.Required("type"): "mass_ai_dj/players/get",
}

CREATE_PARTY_SCHEMA: VolDictType = {
    vol.Required("type"): "mass_ai_dj/parties/create",
    vol.Required("name"): str,
}

DELETE_PARTY_SCHEMA: VolDictType = {
    vol.Required("type"): "mass_ai_dj/parties/delete",
    vol.Required("party_id"): str,
}

REMOVE_FROM_HISTORY_SCHEMA: VolDictType = { 
    vol.Required("type"): "mass_ai_dj/parties/history/remove",
    vol.Required("party_id"): str,
    vol.Required("index"): int,
}

CLEAR_HISTORY_SCHEMA: VolDictType = {
    vol.Required("type"): "mass_ai_dj/parties/history/clear",
    vol.Required("party_id"): str,
}