from typing import Literal

from pydantic import BaseModel, Field


class IncidentRequest(BaseModel):
    service: str = Field(min_length=1, max_length=80)
    environment: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=240)
    symptoms: list[str] = Field(default_factory=list, max_length=30)
    logs: list[str] = Field(default_factory=list, max_length=50)


class Signal(BaseModel):
    name: str
    evidence: list[str]


class RunbookMatch(BaseModel):
    signal: str
    title: str
    guidance: list[str]


class TriageResponse(BaseModel):
    service: str
    environment: str
    mode: Literal["deterministic_baseline"] = "deterministic_baseline"
    signals: list[Signal]
    runbooks: list[RunbookMatch]
    recommended_actions: list[str]
    execution_authorized: Literal[False] = False
