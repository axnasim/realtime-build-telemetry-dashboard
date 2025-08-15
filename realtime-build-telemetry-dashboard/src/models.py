from pydantic import BaseModel, Field
from typing import Literal, Optional
import time

Status = Literal["PASS", "FAIL"]

class BuildEvent(BaseModel):
    agent_id: str = Field(..., min_length=1)
    build_id: str = Field(..., min_length=1)
    status: Status
    duration_ms: int = Field(..., ge=0)
    timestamp: float = Field(default_factory=lambda: time.time())

class Summary(BaseModel):
    total: int
    passed: int
    failed: int
    avg_duration_ms: float
