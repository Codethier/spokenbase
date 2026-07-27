# Worker Protocol

This directory is the canonical, versioned cross-language contract between the
Community API and customer-controlled workers.

Workers are pull-based queue consumers. They register and lease work through
the authenticated Community worker-control API; they do not expose a public
FastAPI service or connect directly to PostgreSQL, Redis, or BullMQ.

The schema is intentionally minimal during Milestone 0. TypeScript and Python
models must later be generated from or validated against the same schemas.
