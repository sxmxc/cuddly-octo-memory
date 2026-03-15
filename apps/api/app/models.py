from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import ConfigDict
from sqlalchemy import Column, JSON as SAJSON
from sqlmodel import Field, SQLModel

from app.time_utils import utc_now


class AuthMode(str, Enum):
    none = "none"
    basic = "basic"
    api_key = "api_key"
    bearer = "bearer"


class EndpointDefinition(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str
    method: str
    path: str
    category: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(SAJSON))
    summary: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    auth_mode: AuthMode = AuthMode.none
    request_schema: Optional[Dict] = Field(default_factory=dict, sa_column=Column(SAJSON))
    response_schema: Optional[Dict] = Field(default_factory=dict, sa_column=Column(SAJSON))
    success_status_code: int = 200
    error_rate: float = 0.0
    latency_min_ms: int = 0
    latency_max_ms: int = 0
    seed_key: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    model_config = ConfigDict(arbitrary_types_allowed=True)
