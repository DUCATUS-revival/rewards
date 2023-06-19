from pydantic import BaseModel

class ReferralStats(BaseModel):
    online_status: bool
    online_percent: float
    expected_rewards: float

