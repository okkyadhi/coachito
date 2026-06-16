from datetime import datetime

from pydantic import BaseModel


class InviteOut(BaseModel):
    id: str
    code: str
    phone_e164: str | None
    expires_at: datetime
    landing_url: str
