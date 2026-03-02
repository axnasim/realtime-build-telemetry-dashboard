from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BuildMetric(BaseModel):
    agent_id: str = Field(..., description="CI agent identifier")
    build_id: str = Field(..., description="Unique build identifier")
    status: str = Field(..., description="Build status: PASS or FAIL")
    duration_ms: int = Field(..., description="Build duration in milliseconds")
    timestamp: Optional[datetime] = None
    metadata: Optional[dict] = None