# SPDX-License-Identifier: AGPL-3.0-only

"""Versioned Redpanda command, event, and worker HTTP models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ProtocolModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        extra="forbid",
        populate_by_name=True,
    )

    @field_validator("created_at", check_fields=False)
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("createdAt must include a timezone")
        return value


ProcessingStage = Literal[
    "ingest",
    "validate",
    "inspect",
    "normalize",
    "voice-activity-detection",
    "transcribe",
    "diarize",
    "align",
    "clean",
    "apply-glossary",
    "summarize",
    "index",
    "export",
    "maintenance",
]


class ProcessingCommand(ProtocolModel):
    protocol_version: Literal["1"]
    message_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=160)
    created_at: datetime
    command_type: Literal["run-stage"]
    processing_run_id: UUID
    organization_id: UUID
    stage: ProcessingStage
    attempt: int = Field(ge=1, le=100)
    required_capabilities: tuple[
        Annotated[str, Field(min_length=1, max_length=128)],
        ...,
    ] = ()

    @field_validator("required_capabilities")
    @classmethod
    def require_unique_capabilities(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("requiredCapabilities must contain unique values")
        return value


ProcessingEventType = Literal[
    "accepted",
    "rejected",
    "started",
    "progress",
    "completed",
    "failed",
    "cancelled",
]


class ProcessingEvent(ProtocolModel):
    protocol_version: Literal["1"] = "1"
    message_id: UUID
    causation_message_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=256)
    created_at: datetime
    event_type: ProcessingEventType
    processing_run_id: UUID
    organization_id: UUID
    stage: ProcessingStage
    worker_id: str = Field(min_length=1, max_length=128)
    error_code: str | None = Field(default=None, max_length=128)
    retryable: bool | None = None


class DeadLetterEvent(ProtocolModel):
    protocol_version: Literal["1"] = "1"
    message_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=256)
    created_at: datetime
    event_type: Literal["dead-letter"] = "dead-letter"
    worker_id: str = Field(min_length=1, max_length=128)
    source_topic: str = Field(min_length=1, max_length=249)
    source_partition: int = Field(ge=0)
    source_offset: int = Field(ge=0)
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    error_code: str = Field(min_length=1, max_length=128)


class QueueHealth(ProtocolModel):
    enabled: bool
    connected: bool
    messages_handled: int = Field(ge=0)
    active_jobs: int = Field(ge=0)
    last_error_code: str | None = None


class HealthResponse(ProtocolModel):
    status: Literal["ok"]
    worker_id: str
    worker_version: str
    uptime_seconds: float = Field(ge=0)
    queue: QueueHealth


class ReadinessResponse(ProtocolModel):
    status: Literal["ready", "not-ready"]
    worker_id: str
    queue: QueueHealth


class CapabilityResponse(ProtocolModel):
    protocol_version: Literal["1"] = "1"
    worker_id: str
    worker_version: str
    cpu: str
    gpu: str | None
    supported_stages: tuple[str, ...]
    command_topics: tuple[str, ...]
