from datetime import datetime
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
    timestamp: datetime
