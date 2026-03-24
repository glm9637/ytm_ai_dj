"""Storage for AI DJ parties."""
from __future__ import annotations

from typing import Any
import uuid

from attrs import asdict
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from custom_components.mass_ai_dj.backend.model import Party, PartyUpdate, Song, VibeSession

from .const import DOMAIN

STORAGE_KEY = f"{DOMAIN}.parties"
STORAGE_VERSION = 1


class PartyStore:
    """Class to hold Party data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self.hass = hass
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY)
        self.parties: dict[str, Party] = {}
        self._load_task = None

    async def async_load(self) -> None:
        """Load data from storage."""
        raw_data = await self._store.async_load()
        if not raw_data:
            self.parties = {}
            return

        # Home Assistant gives us raw dicts, we turn them back into objects
        parties: dict[str, Party] = {}
        for party_id, p in raw_data.get("parties", {}).items():
            parties[party_id] = Party(
                id=p["id"],
                name=p["name"],
                active=p.get("active", False),
                media_player_id=p.get("media_player_id"),
                # Rehydrate nested history
                history=[Song(**s) for s in p.get("history", [])],
                # Rehydrate nested sessions + parse ISO date strings
                sessions=[
                    VibeSession(
                        vibe=s["vibe"],
                        from_date=dt_util.parse_datetime(s["from_date"]) or dt_util.utcnow(),
                        to_date=dt_util.parse_datetime(s["to_date"]) or dt_util.utcnow()
                    )
                    for s in p.get("sessions", [])
                ]
            )
        self.parties = parties

    async def async_save(self) -> None:
        """Save data to storage."""
        data_to_save = {
            "parties": {pid: asdict(p) for pid, p in self.parties.items()}
        }
        await self._store.async_save(data_to_save)

    def get_parties(self) -> list[Party]:
        """Return all parties."""
        return list(self.parties.values())

    async def create_party(self, name: str) -> Party:
        """Create a new party."""
        party_id = str(uuid.uuid4())
        party = Party(
            id=party_id,
            name=name,
            sessions=[],
            history=[],
            active=False,
            media_player_id=None,
        )
       
        self.parties[party_id] = party
        await self.async_save()
        return party

    async def update_party(self, party_id: str, updates: PartyUpdate) -> Party:
        """Update an existing party."""
        if party_id not in self.parties:
            raise KeyError(f"Party {party_id} not found")
            
        party = self.parties[party_id]
        if updates.name is not None:
            party.name = updates.name
        if updates.sessions is not None:
            party.sessions = updates.sessions
        if updates.media_player_id is not None:
            party.media_player_id = updates.media_player_id
        if updates.active is not None:
            party.active = updates.active

        await self.async_save()
        return party

    async def delete_party(self, party_id: str) -> None:
        """Delete a party."""
        if party_id in self.parties:
            del self.parties[party_id]
            await self.async_save()

    async def add_to_history(self, party_id: str, artist: str, title: str) -> None:
        """Add playback history to a party."""
        if party_id not in self.parties:
            return
            
        party = self.parties[party_id]
        party.history.append(Song(title=title, artist=artist))
        await self.async_save()

    async def remove_from_history(self, party_id: str, index: int) -> None:
        """Remove an item from the history by index."""
        if party_id in self.parties:
            history = self.parties[party_id].history
            if 0 <= index < len(history):
                history.pop(index)
                await self.async_save()

    async def clear_history(self, party_id: str) -> None:
        """Clear all history for a party."""
        if party_id in self.parties:
            self.parties[party_id].history = []
            await self.async_save()
