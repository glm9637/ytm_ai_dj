from dataclasses import dataclass
from datetime import datetime

@dataclass
class Song:
    """Class for keeping track of an song."""
    title: str
    artist: str
    played_at: str | None = None

@dataclass
class VibeSession:
    """Class for keeping track of a vibe session."""
    vibe: str
    from_date: datetime | None
    to_date: datetime | None

@dataclass
class Party:
    """Class for keeping track of a party."""
    name: str
    sessions: list[VibeSession]
    history: list[Song]
    id: str
    media_player_id: str | None = None
    active: bool = False
    
@dataclass
class PartyUpdate:
    """Class for keeping track of a party update."""
    name: str | None = None
    sessions: list[VibeSession] | None = None
    id: str = ""
    media_player_id: str | None = None
    active: bool | None = None



