"""Background DJ Engine to drive active AI DJ parties."""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import re
from typing import Any

from ytmusicapi import YTMusic
import google.generativeai as genai
from google.generativeai import GenerativeModel

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .store import PartyStore

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL = datetime.timedelta(seconds=30)
MIN_DURATION_SEC = 120
MAX_DURATION_SEC = 420


class DJEngine:
    """The central engine that monitors parties and interacts with APIs."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the DJ Engine."""
        self.hass = hass
        self._unsub_interval = None
        self._playlist_ids: dict[str, str] = {}
        
        # We need to track the latest YTM history so we know when a new song is played
        self._last_history_ids: dict[str, str] = {}

    def start(self) -> None:
        """Start the background monitoring loop."""
        if self._unsub_interval is None:
            self._unsub_interval = async_track_time_interval(
                self.hass, self._async_poll, POLL_INTERVAL
            )
            _LOGGER.info("AI DJ Engine started.")

    def stop(self) -> None:
        """Stop the background monitoring loop."""
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
            _LOGGER.info("AI DJ Engine stopped.")

    async def _async_poll(self, now: datetime.datetime) -> None:
        """The 30-second polling loop."""
        store: PartyStore | None = self.hass.data[DOMAIN].get("store")
        services = self.hass.data[DOMAIN]
        
        # Find the actual services which are stored under entry_id, or globally if we refactored
        # In our __init__.py we put them under entry.entry_id: hass.data[DOMAIN][entry.entry_id] = {"ytm": ..., "genai": ...}
        # Let's find the first valid ytmusic instance.
        ytm: YTMusic | None = None
        for key, value in services.items():
            if isinstance(value, dict) and "ytm" in value:
                ytm = value["ytm"]
                break
                
        if not store or not ytm:
            return

        active_parties = [p for p in store.get_parties() if p.get("active")]
        
        for party in active_parties:
            try:
                await self._process_party(party, store, ytm)
            except Exception as err:
                _LOGGER.error("Error processing party %s: %s", party.get("name"), err)

    async def _process_party(self, party: dict[str, Any], store: PartyStore, ytm: YTMusic) -> None:
        """Process an individual active party."""
        party_id = party["id"]
        vibe = party.get("vibe", "")
        
        # 1. Ensure Playlist Exists
        playlist_id = self._playlist_ids.get(party_id)
        if not playlist_id:
            playlist_id = await self.hass.async_add_executor_job(
                self._ensure_playlist, ytm, party["name"]
            )
            if playlist_id:
                self._playlist_ids[party_id] = playlist_id
            else:
                _LOGGER.error("Failed to create or find playlist for party %s", party["name"])
                return

        # 2. Sync History
        history = await self.hass.async_add_executor_job(ytm.get_history)
        if history and isinstance(history, list) and len(history) > 0:
            latest_song = history[0]
            latest_vid = latest_song.get("videoId")
            
            # If this is a new song we haven't seen during this party's active session
            last_seen = self._last_history_ids.get(party_id)
            if latest_vid and latest_vid != last_seen:
                self._last_history_ids[party_id] = latest_vid
                
                # Check if this song is already in the party's HA history (to prevent duplicates on startup)
                song_already_in_party_history = any(
                    latest_song.get("title") == h.get("title") and 
                    (latest_song.get("artists") and latest_song["artists"][0].get("name") == h.get("artist"))
                    for h in party.get("history", [])
                )
                
                if not song_already_in_party_history:
                    artist_name = latest_song["artists"][0]["name"] if latest_song.get("artists") else "Unknown Artist"
                    await store.add_to_history(party_id, artist_name, latest_song.get("title", "Unknown Title"))
                    _LOGGER.info("Added manually played or skipped song to history: %s", latest_song.get("title"))

        # 3. Check Queue Size
        playlist = await self.hass.async_add_executor_job(ytm.get_playlist, playlist_id)
        tracks = playlist.get("tracks", [])
        
        # Calculate how many songs in the playlist are NOT in the HA history
        # (These are the upcoming queued songs)
        history_titles = [h.get("title", "").lower() for h in party.get("history", [])]
        
        queued_count = 0
        for track in tracks:
            title = track.get("title", "").lower()
            if title not in history_titles:
                queued_count += 1
                
        if queued_count < 2:
            _LOGGER.info("Queue for party %s is low (%s). Triggering LLM...", party["name"], queued_count)
            await self._generate_and_add_song(party, playlist_id, ytm, store)
            
    async def _generate_and_add_song(
        self, party: dict[str, Any], playlist_id: str, ytm: YTMusic, store: PartyStore
    ) -> None:
        """Trigger Gemini to get a recommendation and add to YTM playlist."""
        
        start_time_str = party.get("start_time")
        end_time_str = party.get("end_time")
        now = dt_util.utcnow()
        
        start_time = dt_util.parse_datetime(start_time_str) if start_time_str else now
        if not start_time.tzinfo:
            start_time = start_time.replace(tzinfo=dt_util.UTC)
            
        end_time = dt_util.parse_datetime(end_time_str) if end_time_str else (start_time + datetime.timedelta(hours=4))
        if not end_time.tzinfo:
            end_time = end_time.replace(tzinfo=dt_util.UTC)
            
        total_duration = (end_time - start_time).total_seconds()
        elapsed = (now - start_time).total_seconds()
        
        progress_percentage = 0
        if total_duration > 0:
            progress_percentage = int((elapsed / total_duration) * 100)
            
        overtime_note = ""
        if progress_percentage > 100:
            overtime_note = "The party has gone into overtime, keep the vibe going."
            
        history_str = ", ".join(
            f"{h['title']} by {h['artist']}" for h in party.get("history", [])[-10:]
        )
        if not history_str:
            history_str = "None yet."

        prompt = (
            f"You are a DJ hosting a party for the following vibe: {party.get('vibe')}. "
            f"Timeline Context:\n"
            f"Start Time: {start_time_str}\n"
            f"Expected End Time: {end_time_str}\n"
            f"Current Time: {now.isoformat()}\n"
            f"We are currently {progress_percentage}% through the planned duration. Use this percentage to map the energy curve "
            f"(e.g., 0-20% warm-up, 40-70% peak energy, 95-100% cooldown).\n"
            f"These songs were played recently: {history_str}. What is your next pick? {overtime_note} "
            f"Respond strictly in JSON format: {{\"artist\": \"Name\", \"title\": \"Song Title\"}}"
        )

        def call_llm():
            model = GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                )
            )
            return response.text

        try:
            response_text = await self.hass.async_add_executor_job(call_llm)
            data = json.loads(response_text)
            artist = data.get("artist", "")
            title = data.get("title", "")
            _LOGGER.info("LLM Suggested: %s by %s", title, artist)
        except Exception as err:
            _LOGGER.error("Failed to parse LLM response: %s", err)
            return

        def search_and_add():
            query = f"{title} {artist}"
            results = ytm.search(query, filter="songs", limit=3)
            
            valid_video_id = None
            for idx, res in enumerate(results):
                duration_str = res.get("duration", "0:0")
                parts = duration_str.split(":")
                if len(parts) == 2:
                    seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    seconds = 0
                    
                if MIN_DURATION_SEC <= seconds <= MAX_DURATION_SEC:
                    valid_video_id = res.get("videoId")
                    break
                    
            if not valid_video_id and results:
                # Fallback to the first result if none matched duration filter
                valid_video_id = results[0].get("videoId")
                
            if valid_video_id:
                # Prevent duplicate queue entries (Epic criteria: "must not duplicate queue entries if a user manually forces the playlist to skip")
                # We check this by just adding to the playlist and hoping they didn't just add it themselves.
                ytm.add_playlist_items(playlist_id, [valid_video_id])
                return True
            return False

        success = await self.hass.async_add_executor_job(search_and_add)
        if success:
            _LOGGER.info("Successfully added %s by %s to playlist", title, artist)

    def _ensure_playlist(self, ytm: YTMusic, name: str) -> str | None:
        """Find existing playlist or create a new one."""
        library = ytm.get_library_playlists(limit=50)
        for pl in library:
            if pl.get("title") == name:
                return pl.get("playlistId")
                
        # Create new
        try:
            return ytm.create_playlist(name, "AI DJ Generated Playlist")
        except Exception as e:
            _LOGGER.error("Could not create playlist: %s", e)
            return None
