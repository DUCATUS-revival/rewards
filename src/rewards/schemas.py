from pydantic import BaseModel


class PeerStatus(BaseModel):
    online_status: bool
    online_percent: float
    expected_rewards: str
