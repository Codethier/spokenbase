# Spokenbase Worker

The worker owns FFmpeg inspection and normalization, faster-whisper
transcription, pyannote diarization, optional alignment, model management, and
capability reporting.

It is a small FastAPI process with a lifecycle-managed Redpanda consumer.
Commands arrive through versioned topics; FastAPI exposes only liveness,
readiness, version, and capability information. It is not a synchronous
upload-to-transcript endpoint.

The broker poll loop is reserved for validation, durable claims, and dispatch.
FFmpeg, ASR, diarization, and summarization must run in a bounded executor with
backpressure so long recordings do not stop consumer heartbeats.

Remote workers make outbound Redpanda connections using TLS and SASL and do
not need publicly reachable inbound ports. Workers never receive PostgreSQL
credentials, provider credentials, media bytes, or transcript bodies in broker
records.

Milestone 0 implements the control surface, protocol validation, and broker
wiring. Processing handlers remain capability-gated until their milestones are
implemented.

## Run locally

Queue consumption is disabled by default, so the HTTP surface can be developed
without a broker:

```text
python -m venv .venv
python -m pip install -e ".[test]"
spokenbase-worker
```

The service listens on `127.0.0.1:8080` and exposes:

```text
GET /healthz
GET /readyz
GET /v1/capabilities
```

From the `community` directory, the Milestone 0 broker/worker stack runs with:

```text
docker compose --env-file .env.example -f infra/compose/compose.yaml up --build
```

This reference stack uses one development Redpanda broker and plaintext only
inside its local Compose network. The worker ID is stable, the worker endpoint
is published on localhost, and Redpanda Console is opt-in through the
`observability` profile.

The current handler emits a durable terminal rejection for every processing
command. It does not claim transcription support until the faster-whisper
handler and its integration tests are implemented.
