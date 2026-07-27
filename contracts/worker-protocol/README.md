# Worker Protocol

This directory is the canonical, versioned cross-language contract between the
Community API and customer-controlled workers.

Workers run a minimal FastAPI health and capability surface while consuming
versioned Redpanda command topics in the background. The FastAPI surface is not
a synchronous transcription API. Workers never connect directly to PostgreSQL
and never receive provider credentials.

Command records contain identifiers and routing metadata. After an idempotent
claim, a worker obtains short-lived media and result-transfer URLs through the
authenticated API. PostgreSQL remains the authoritative state, and every
command and event is idempotent because Redpanda delivery is at least once.

The schema is intentionally minimal during Milestone 0. TypeScript and Python
models must later be generated from or validated against the same schemas.
