# Spokenbase Community

Spokenbase Community is the public, self-hosted foundation for turning
recordings into searchable, editable, and shareable spoken knowledge.

The intended Community deployment is deliberately lean:

```text
Browser
  -> Nuxt
     -> NestJS modular monolith
        -> PostgreSQL
        -> Redpanda
        -> local filesystem or S3-compatible storage
        -> optional Redpanda-fed FastAPI CPU/GPU workers
```

The project is currently at **Milestone 0 — Repository Bootstrap**. The
checked-in application and worker files are structural skeletons, not a
production release. See `CURRENT_MILESTONE.md` for the active scope.

Community is designed to run without a Spokenbase account, paid license, or
Spokenbase-operated infrastructure. Commercial Hosted and Enterprise
capabilities live outside this public repository.

## Development

Requirements:

- Node.js 22 or newer;
- pnpm 10;
- Python 3.12 for worker development;
- Docker with Compose for integration environments.

Install the JavaScript workspace:

```bash
pnpm install --frozen-lockfile
```

Common commands:

```bash
pnpm dev
pnpm build
pnpm typecheck
pnpm test
```

Read `AGENTS.md` before implementation.

## License

Application code is licensed under `AGPL-3.0-only` unless a file explicitly
states otherwise. See `LICENSE`.
