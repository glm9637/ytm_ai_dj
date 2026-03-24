from abc import ABC, abstractmethod

from homeassistant.util import dt as dt_util

from custom_components.mass_ai_dj.backend.model import VibeSession
from custom_components.mass_ai_dj.backend.model import Song


class LLMProvider(ABC):
    """The base strategy for all AI providers."""
    
    @abstractmethod
    async def _query_llm(self, prompt: str) -> Song:
        """
        Must return a Song dataclass
        """
        pass

    async def generate_song(self, vibe: VibeSession, history: list[Song]) -> Song:
        now = dt_util.utcnow()

        overtime_note = ""
        if(vibe.to_date and vibe.from_date):
            total_duration = (vibe.to_date - vibe.from_date).total_seconds()
            elapsed = (now - vibe.from_date).total_seconds()
            
            progress_percentage = 0
            if total_duration > 0:
                progress_percentage = int((elapsed / total_duration) * 100)
                
            if progress_percentage > 100:
                overtime_note = "The party has gone into overtime, keep the vibe going."
            
        history_str = ", ".join(
            f"{h.title} by {h.artist}" for h in history[-60:]
        )
        if not history_str:
            history_str = "None yet."

        prompt = (
            f"You are a DJ hosting a party for the following vibe: {vibe.vibe}. "
            f"Timeline Context:\n"
            f"These songs were played recently: {history_str}. What is your next pick? {overtime_note} "
            f"Respond strictly in JSON format: {{\"artist\": \"Name\", \"title\": \"Song Title\"}}"
        )
        return await self._query_llm(prompt)