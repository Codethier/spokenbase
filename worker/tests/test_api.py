# SPDX-License-Identifier: AGPL-3.0-only

import asyncio

from httpx import ASGITransport, AsyncClient, Response

from spokenbase_worker.main import create_app
from spokenbase_worker.settings import WorkerSettings


def test_health_readiness_and_capabilities_without_queue() -> None:
    settings = WorkerSettings(
        worker_id="test-worker",
        queue_enabled=False,
        supported_stages=("transcribe",),
    )

    async def exercise_api() -> tuple[Response, Response, Response, Response]:
        app = create_app(settings)
        transport = ASGITransport(app=app)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=transport,
                base_url="http://worker.test",
            ) as client,
        ):
            return (
                await client.get("/healthz"),
                await client.get("/readyz"),
                await client.get("/v1/capabilities"),
                await client.post("/transcribe"),
            )

    health, readiness, capabilities, unsupported_transcription = asyncio.run(exercise_api())

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["queue"] == {
        "enabled": False,
        "connected": False,
        "messagesHandled": 0,
        "activeJobs": 0,
        "lastErrorCode": None,
    }

    assert readiness.status_code == 200
    assert readiness.json()["status"] == "ready"

    assert capabilities.status_code == 200
    assert capabilities.json()["workerId"] == "test-worker"
    assert capabilities.json()["supportedStages"] == ["transcribe"]
    assert "redpandaBrokers" not in capabilities.json()
    assert "saslPassword" not in capabilities.json()
    assert unsupported_transcription.status_code == 404
