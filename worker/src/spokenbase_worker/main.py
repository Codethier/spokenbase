# SPDX-License-Identifier: AGPL-3.0-only

"""FastAPI control surface for the Redpanda-fed processing worker."""

from __future__ import annotations

import platform
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from spokenbase_worker import __version__
from spokenbase_worker.protocol import (
    CapabilityResponse,
    HealthResponse,
    QueueHealth,
    ReadinessResponse,
)
from spokenbase_worker.redpanda import RedpandaCommandConsumer
from spokenbase_worker.settings import WorkerSettings
from spokenbase_worker.state import RuntimeSnapshot, RuntimeState


def _queue_health(snapshot: RuntimeSnapshot) -> QueueHealth:
    return QueueHealth(
        enabled=snapshot.queue_enabled,
        connected=snapshot.queue_connected,
        messages_handled=snapshot.messages_handled,
        active_jobs=snapshot.active_jobs,
        last_error_code=snapshot.last_error_code,
    )


def create_app(settings: WorkerSettings | None = None) -> FastAPI:
    resolved_settings = settings or WorkerSettings.from_env()
    state = RuntimeState(queue_enabled=resolved_settings.queue_enabled)
    consumer = RedpandaCommandConsumer(resolved_settings, state)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        consumer.start()
        try:
            yield
        finally:
            consumer.stop()

    application = FastAPI(
        title="Spokenbase Worker",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )

    @application.get("/healthz", response_model=HealthResponse)
    async def health() -> HealthResponse:
        snapshot = state.snapshot()
        return HealthResponse(
            status="ok",
            worker_id=resolved_settings.worker_id,
            worker_version=__version__,
            uptime_seconds=snapshot.uptime_seconds,
            queue=_queue_health(snapshot),
        )

    @application.get(
        "/readyz",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse}},
    )
    async def readiness() -> ReadinessResponse | JSONResponse:
        snapshot = state.snapshot()
        response = ReadinessResponse(
            status="ready" if snapshot.ready else "not-ready",
            worker_id=resolved_settings.worker_id,
            queue=_queue_health(snapshot),
        )
        if snapshot.ready:
            return response
        return JSONResponse(
            status_code=503,
            content=response.model_dump(mode="json", by_alias=True),
        )

    @application.get("/v1/capabilities", response_model=CapabilityResponse)
    async def capabilities() -> CapabilityResponse:
        return CapabilityResponse(
            worker_id=resolved_settings.worker_id,
            worker_version=__version__,
            cpu=platform.processor() or platform.machine() or "unknown",
            gpu=resolved_settings.gpu_model,
            supported_stages=resolved_settings.supported_stages,
            command_topics=resolved_settings.redpanda_command_topics,
        )

    application.state.worker_settings = resolved_settings
    application.state.worker_state = state
    application.state.redpanda_consumer = consumer
    return application


app = create_app()
