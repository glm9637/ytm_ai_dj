"""Background DJ Engine to drive active AI DJ parties."""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
from typing import Any

from ytmusicapi import YTMusic

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
        
        ytm: YTMusic | None = None
        gemini_key: str | None = None
        
        for key, value in services.items():
            if isinstance(value, dict) and "ytm" in value:
                ytm = value["ytm"]
                # Assuming you stored the key in __init__.py alongside ytm
                gemini_key = value.get("gemini_key") 
                break
                
        if not store or not ytm or not gemini_key:
            return

        active_parties = [p for p in store.get_parties() if p.get("active")]
        
        for party in active_parties:
            try:
                await self._process_party(party, store, ytm, gemini_key)
            except Exception as err:
                _LOGGER.error("Error processing party %s: %s", party.get("name"), err)

    async def _process_party(self, party: dict[str, Any], store: PartyStore, ytm: YTMusic, gemini_key: str) -> None:
        """Process an individual active party."""
        party_id = party["id"]
        
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
                
                # Check if this song is already in the party's HA history
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
        
        history_titles = [h.get("title", "").lower() for h in party.get("history", [])]
        
        queued_count = 0
        for track in tracks:
            title = track.get("title", "").lower()
            if title not in history_titles:
                queued_count += 1
                
        if queued_count < 2:
            _LOGGER.info("Queue for party %s is low (%s). Triggering LLM...", party["name"], queued_count)
            await self._generate_and_add_song(party, playlist_id, ytm, store, gemini_key)
            
    async def _generate_and_add_song(
        self, party: dict[str, Any], playlist_id: str, ytm: YTMusic, store: PartyStore, gemini_key: str
    ) -> None:
        """Trigger Gemini via REST API to get a recommendation and add to YTM playlist."""
        
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

        # Build the REST API request
        session = async_get_clientsession(self.hass)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error("Gemini API error: %s", error_text)
                    return
                
                response_data = await response.json()
                response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                
            parsed_data = json.loads(response_text)
            artist = parsed_data.get("artist", "")
            title = parsed_data.get("title", "")
            _LOGGER.info("LLM Suggested: %s by %s", title, artist)
        except Exception as err:
            _LOGGER.error("Failed to query Gemini API or parse response: %s", err)
            return

        def search_and_add_to_playlist():
            query = f"{title} {artist}"
            results = ytm.search(query, filter="songs", limit=3)
            
            for res in results:
                duration_str = res.get("duration", "0:0")
                parts = duration_str.split(":")
                seconds = 0
                if len(parts) == 2:
                    seconds = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                
                if MIN_DURATION_SEC <= seconds <= MAX_DURATION_SEC:
                    vid = res.get("videoId")
                    if vid:
                        ytm.add_playlist_items(playlist_id, [vid])
                        return vid
            
            # Fallback to first result if duration filter fails
            if results and results[0].get("videoId"):
                vid = results[0].get("videoId")
                ytm.add_playlist_items(playlist_id, [vid])
                return vid
            return None

        # Execute search and playlist addition
        video_id = await self.hass.async_add_executor_job(search_and_add_to_playlist)

        if video_id:
            # PUSH TO LIVE QUEUE via Home Assistant Media Player
            target_player = party.get("media_player_id")
            if target_player:
                _LOGGER.info("Enqueuing %s to live player: %s", video_id, target_player)
                await self.hass.services.async_call(
                    "media_player",
                    "play_media",
                    {
                        "entity_id": target_player,
                        "media_content_id": video_id,
                        "media_content_type": "music",
                        "enqueue": "add",
                    },
                )
            else:
                _LOGGER.warning("No media player selected for party %s. The song was added to the playlist but might not play automatically.", party.get("name"))

    def _ensure_playlist(self, ytm: YTMusic, name: str) -> str | None:
        """Find existing playlist or create a new one."""
        library = ytm.get_library_playlists(limit=50)
        for pl in library:
            if pl.get("title") == name:
                return pl.get("playlistId")
                
        try:
            return ytm.create_playlist(name, "AI DJ Generated Playlist")
        except Exception as e:
            _LOGGER.error("Could not create playlist: %s", e)
            return None