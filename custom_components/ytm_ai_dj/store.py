"""Storage for AI DJ parties."""
from __future__ import annotations

from typing import Any
import uuid
import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORAGE_KEY = f"{DOMAIN}.parties"
STORAGE_VERSION = 1


class PartyStore:
    """Class to hold Party data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self.hass = hass
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, STORAGE_KEY)
        self.parties: dict[str, Any] = {}
        self._load_task = None

    async def async_load(self) -> None:
        """Load data from storage."""
        if self._load_task is None:
            data = await self._store.async_load()
            if data is None:
                self.parties = {}
            else:
                self.parties = data.get("parties", {})
            self._load_task = True

    async def async_save(self) -> None:
        """Save data to storage."""
        await self._store.async_save({"parties": self.parties})

    def get_parties(self) -> list[dict[str, Any]]:
        """Return all parties."""
        return list(self.parties.values())

    async def create_party(self, name: str) -> dict[str, Any]:
        """Create a new party."""
        party_id = str(uuid.uuid4())
        party = {
            "id": party_id,
            "name": name,
            "vibe": "",
            "start_time": None,
            "end_time": None,
            "history": [],
            "active": False,
            "media_player_id": "",
        }
        self.parties[party_id] = party
        await self.async_save()
        return party

    async def update_party(self, party_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update an existing party."""
        if party_id not in self.parties:
            raise KeyError(f"Party {party_id} not found")
            
        party = self.parties[party_id]
        for key, value in updates.items():
            if key in ["vibe", "start_time", "end_time", "active", "media_player_id"]:
                party[key] = value
                
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
        party["history"].append({
            "artist": artist,
            "title": title,
            "played_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        await self.async_save()

    async def remove_from_history(self, party_id: str, index: int) -> None:
        """Remove an item from the history by index."""
        if party_id in self.parties:
            history = self.parties[party_id]["history"]
            if 0 <= index < len(history):
                history.pop(index)
                await self.async_save()

    async def clear_history(self, party_id: str) -> None:
        """Clear all history for a party."""
        if party_id in self.parties:
            self.parties[party_id]["history"] = []
            await self.async_save()
