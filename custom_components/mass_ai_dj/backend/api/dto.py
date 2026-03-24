from typing import TypedDict, NotRequired

class SessionUpdateDict(TypedDict):
    vibe: str
    from_date: str
    to_date: str

class UpdatePartyMsg(TypedDict):
    id: int  
    type: str
    party_id: str
    sessions: NotRequired[list[SessionUpdateDict]]
    media_player_id: NotRequired[str]
    active: NotRequired[bool]
    
class CreatePartyMsg(TypedDict):
    id: int  
    type: str
    name: str
    
class GetPartiesMsg(TypedDict):
    id: int  
    type: str
    
class GetPlayersMsg(TypedDict):
    id: int  
    type: str
    
class DeletePartyMsg(TypedDict):
    id: int  
    type: str
    party_id: str
    
class RemoveFromHistoryMsg(TypedDict):
    id: int  
    type: str
    party_id: str
    index: int
    
class ClearHistoryMsg(TypedDict):
    id: int  
    type: str
    party_id: str
    