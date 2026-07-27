# AGENTS.md — Spokenbase Community

## 1. Mission and Scope

This source tree is the complete public Spokenbase Community application.

It must provide a genuinely useful, self-hosted, provider-neutral web platform for turning recordings into searchable, editable, and shareable spoken knowledge.

Community includes:

- Nuxt browser application and PWA capabilities where useful;
- NestJS REST API;
- PostgreSQL;
- Redis and BullMQ;
- local filesystem or S3-compatible storage;
- local CPU and NVIDIA GPU workers;
- customer-operated remote workers;
- local transcription;
- organization BYOK transcription and summary providers;
- transcript playback, editing, revisions, search, and exports;
- organizations, teams, projects, provider connections, presets, usage, non-monetary budgets, basic roles, and basic audit history;
- Docker Compose self-hosting.

There is no Electron, SQLite, native desktop, or desktop synchronization architecture.

When this directory is inside the private integrated repository, the root `AGENTS.md` also applies. In the exported public repository, this file is the root instruction file.

Read `CURRENT_MILESTONE.md` before implementation when it exists. Do not implement a later milestone unless the task explicitly requests it.

---

## 2. Application Architecture

Use one Nuxt application and one NestJS modular monolith.

```text
Browser
  -> Nuxt web service
     -> NestJS REST API
        -> PostgreSQL
        -> Redis/BullMQ
        -> local filesystem or S3-compatible storage
        -> optional local or remote workers
        -> optional organization-approved external providers
```

Keep deployable services lean. Do not add Kafka, Kubernetes-only dependencies, a workflow engine, a vector database, or another application service without a demonstrated requirement.

Local processing means processing on customer-controlled worker infrastructure. It does not imply a desktop application.

---

## 3. Default Stack

### Frontend

- Nuxt;
- Vue 3;
- TypeScript;
- Nuxt UI;
- Nuxt server-side data fetching;
- PWA support where useful;
- Pinia only for genuinely shared client state;
- responsive layouts and Nuxt UI dark mode.

### Backend

- NestJS;
- native ESM;
- TypeScript;
- REST first;
- OpenAPI;
- dependency injection;
- thin controllers;
- modular monolith;
- MikroORM.

### Persistence and Jobs

- PostgreSQL;
- generated MikroORM migrations;
- PostgreSQL full-text search;
- Redis;
- BullMQ;
- local filesystem or S3-compatible object storage;
- MinIO only as a development or reference-Compose S3 service.

### Media and ML

- Python;
- pytest;
- FFmpeg;
- faster-whisper as the initial local ASR implementation;
- pyannote.audio for local diarization;
- Ollama or generic OpenAI-compatible local summaries;
- CPU support is mandatory;
- NVIDIA CUDA is the first optional GPU target.

### TypeScript Testing

- Vitest;
- `@nuxt/test-utils`;
- Vue Test Utils or Vue Testing Library;
- Playwright;
- `@nestjs/testing`;
- Supertest;
- Testcontainers with real PostgreSQL and Redis.

---

## 4. Public Repository Structure

```text
spokenbase/
├── AGENTS.md
├── CURRENT_MILESTONE.md
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── TRADEMARKS.md
├── THIRD_PARTY_NOTICES.md
├── package.json
├── pnpm-workspace.yaml
├── pnpm-lock.yaml
├── tsconfig.base.json
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── layouts/
│   │   ├── middleware/
│   │   ├── pages/
│   │   ├── plugins/
│   │   ├── public/
│   │   ├── server/
│   │   ├── nuxt.config.ts
│   │   └── package.json
│   └── api/
│       ├── src/
│       │   ├── main.ts
│       │   └── community-app.module.ts
│       ├── test/
│       ├── tsconfig.json
│       └── package.json
│
├── src/
│   ├── community-core.module.ts
│   ├── common/
│   ├── config/
│   ├── database/
│   ├── auth/
│   ├── organizations/
│   ├── teams/
│   ├── projects/
│   ├── folders/
│   ├── recordings/
│   ├── media/
│   ├── providers/
│   ├── processing/
│   ├── transcripts/
│   ├── diarization/
│   ├── summaries/
│   ├── search/
│   ├── exports/
│   ├── workers/
│   ├── usage/
│   ├── budgets/
│   ├── audit/
│   └── extension-points/
│
├── contracts/
│   └── worker-protocol/
├── worker/
│   ├── src/
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile.cpu
│   └── Dockerfile.cuda
├── migrations/
│   └── postgres/
├── infra/
│   ├── compose/
│   ├── docker/
│   └── scripts/
└── docs/
    ├── architecture/
    ├── deployment/
    ├── providers/
    ├── workers/
    └── security/
```

Shared code lives directly under `src/`. Do not create dozens of internal packages or publish internal modules to npm.

Every application declares its direct dependencies. A clean exported installation with the frozen public lockfile must succeed.

---

## 5. Authentication and Authorization

Use Better Auth for Community authentication.

Community must support:

- secure first-run administrator bootstrap;
- local credentials;
- organizations and organization membership;
- team authorization;
- no required external identity provider;
- server-side permission enforcement.

First-run setup rules:

- never ship default credentials;
- protect setup with a one-time bootstrap token supplied through deployment configuration;
- create the first administrator and initial organization transactionally;
- invalidate the bootstrap token after successful setup;
- disable the setup endpoint after initialization;
- audit setup completion;
- test interrupted setup and lockout recovery.

Every organization-scoped service method receives or resolves an organization context and enforces it in the service. Frontend visibility is never authorization.

Define and test a permission matrix before adding team-, project-, folder-, or provider-management endpoints.

---

## 6. NestJS Composition

Public Nest composition has two levels:

```text
CommunityCoreModule
  Public feature modules and neutral adapter tokens

CommunityAppModule
  CommunityCoreModule plus Community default adapter bindings
```

`src/community-core.module.ts` must be reusable by downstream composition roots without importing the Community runtime root.

Use a dynamic module or explicit provider-registration function so a composition root can bind neutral tokens such as:

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export const PROCESSING_AUTHORIZATION =
  Symbol('PROCESSING_AUTHORIZATION');
export const PROCESSING_ROUTE_RESOLVER =
  Symbol('PROCESSING_ROUTE_RESOLVER');
export const AUDIT_SINK =
  Symbol('AUDIT_SINK');
```

Community binds:

- budget-based processing authorization;
- local/BYOK route resolution;
- basic audit persistence;
- public feature registration.

`apps/api/src/community-app.module.ts` imports `CommunityCoreModule` with those Community bindings. Composition roots stay thin and contain no reusable business logic.

Do not statically import downstream or proprietary modules anywhere in this repository.

---

## 7. Public Extension Points

Commercial or third-party behavior integrates through neutral ports with useful Community implementations.

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export interface ProcessingAuthorizationPort {
  authorize(
    request: ProcessingAuthorizationRequest,
  ): Promise<ProcessingAuthorizationResult>;

  settle(request: ProcessingSettlementRequest): Promise<void>;

  release(reservationId: string): Promise<void>;
}
```

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export interface ProcessingRouteResolver {
  resolve(
    request: ProcessingRouteRequest,
  ): Promise<ProcessingRouteDecision>;
}
```

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export interface AuditSink {
  record(event: AuditEventInput): Promise<void>;
}
```

Rules:

- public interfaces use neutral terminology;
- public defaults provide real Community value;
- do not add empty enterprise placeholders;
- do not expose payment, wallet, customer-price, proprietary licensing, or vendor production-secret concepts in public types;
- change a public port only for a generally useful capability and add contract tests.

---

## 8. PostgreSQL and MikroORM

Community migrations live under:

```text
migrations/postgres
```

Rules:

- generate migrations with the Community MikroORM configuration;
- migrations are mandatory;
- production schema synchronization is forbidden;
- never rewrite applied migration history;
- review every generated migration;
- test clean installation and supported upgrades;
- use explicit transactions for multi-entity changes;
- avoid accidental lazy loading;
- load required relations explicitly;
- prefer UUID primary keys;
- store timestamps in UTC;
- store durations as integer milliseconds;
- store internal money estimates as bigint micro-units;
- store provider raw results as immutable JSONB or immutable artifact references;
- add idempotency constraints;
- return DTOs, never raw entities.

Do not create another ORM abstraction around MikroORM merely to hide ordinary queries.

---

## 9. Domain Model and Immutability

Minimum planned Community entities:

```text
User
Organization
OrganizationMember
Team
TeamMember
Project
Folder
Tag

Recording
MediaAsset
MediaDerivative

ProviderConnection
ProviderConnectionSecret
ProcessingPreset
ProcessingPolicy
ProcessingRun
ProcessingStage

Transcript
TranscriptRevision
TranscriptSegment
TranscriptWord
Speaker

Summary
SummaryRevision
SummaryTemplate
ActionItem
Highlight
Comment

BudgetPolicy
UsageEvent

WorkerNode
WorkerCapability
ModelInstallation

ApiToken
BasicAuditEvent
```

Immutability means:

- original media bytes are never modified in place, although authorized deletion remains possible;
- a processing run's request and routing decision become immutable when queued;
- completed stage inputs, outputs, and raw provider evidence are immutable;
- run and stage statuses transition only through an explicit state machine;
- processing history is append-only;
- transcript edits create revisions;
- summary edits create revisions;
- edited output never overwrites generated evidence.

Do not call the entire live `ProcessingRun` record immutable: honest status, retry, cancellation, and completion transitions are required.

---

## 10. Canonical Transcript

All transcription providers normalize to one schema.

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export interface NormalizedTranscript {
  language?: string;
  languageConfidence?: number;
  durationMs: number;
  text: string;
  speakers: TranscriptSpeaker[];
  segments: TranscriptSegment[];
  metadata: TranscriptMetadata;
}

export interface TranscriptSegment {
  id: string;
  startMs: number;
  endMs: number;
  text: string;
  speakerId?: string;
  confidence?: number;
  words?: TranscriptWord[];
  source: TranscriptSource;
}

export interface TranscriptWord {
  startMs: number;
  endMs: number;
  text: string;
  confidence?: number;
  speakerId?: string;
}

export interface TranscriptSpeaker {
  id: string;
  displayName?: string;
  isIdentified: boolean;
}

export interface TranscriptSource {
  provider: string;
  model: string;
  processingRunId: string;
}
```

Rules:

- timestamped segments are mandatory;
- word timestamps are optional but preserved;
- store normalized output and sanitized raw provider evidence;
- never store only one large transcript string;
- preserve provider-specific metadata without mixing it into generic domain behavior.

---

## 11. Processing Pipeline

Use explicit stages:

```text
Ingest
Validate
Inspect
Normalize
Voice activity detection
Transcribe
Diarize
Align
Clean
Apply glossary
Summarize
Index
Export
```

Every stage must be idempotent, retryable, observable, represented in processing history, and cancellable where the underlying operation permits it.

A stage may run on:

- a server CPU or GPU worker;
- a customer remote CPU or GPU worker;
- an organization-approved external provider.

Record:

- worker or provider;
- model;
- region when known;
- whether media left customer-controlled infrastructure;
- processing duration;
- estimate;
- routing decision and relevant capabilities.

Do not implement the workflow as one opaque job.

---

## 12. Transcription Provider Contract

Capabilities are connection- and model-aware.

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export interface TranscriptionProvider {
  readonly id: string;

  getCapabilities(
    connection: ProviderConnectionContext,
    model: string,
  ): Promise<TranscriptionCapabilities>;

  estimate(
    request: TranscriptionRequest,
    context: ProcessingContext,
  ): Promise<TranscriptionCostEstimate>;

  submit(
    request: TranscriptionRequest,
    context: ProcessingContext,
  ): Promise<TranscriptionSubmission>;

  poll?(
    externalJobId: string,
    context: ProcessingContext,
  ): Promise<TranscriptionPollResult>;

  cancel?(
    externalJobId: string,
    context: ProcessingContext,
  ): Promise<void>;
}

export type TranscriptionSubmission =
  | {
      status: 'completed';
      result: TranscriptionResult;
    }
  | {
      status: 'submitted';
      externalJobId: string;
      providerMetadata?: Record<string, unknown>;
    };

export type TranscriptionPollResult =
  | { status: 'pending'; providerMetadata?: Record<string, unknown> }
  | { status: 'completed'; result: TranscriptionResult }
  | { status: 'failed'; error: ProviderFailure };

export interface TranscriptionResult {
  transcript: NormalizedTranscript;
  rawResponse: unknown;
  externalJobId?: string;
  providerMetadata: Record<string, unknown>;
}
```

Synchronous and local providers return a completed submission. Asynchronous providers return an external job ID before polling or cancellation is possible.

Raw responses must be sanitized of secrets and persisted immutably before downstream transformation.

Capabilities include:

```text
batch
realtime
word timestamps
segment timestamps
diarization
multichannel
language detection
code switching
vocabulary prompting
confidence scores
audio events
```

Provider-specific behavior stays in adapters. Generic services never branch on a provider name.

Initial order:

1. local faster-whisper through the Python worker;
2. generic OpenAI-compatible;
3. OpenAI;
4. Deepgram;
5. ElevenLabs;
6. Mistral.

Do not add providers until normalization and shared contract tests are stable.

---

## 13. Provider Connections and Secrets

Use separate public configuration and encrypted secret persistence.

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export interface ProviderConnection {
  id: string;
  organizationId?: string;
  name: string;
  providerType: string;
  connectionKind: 'local-compute' | 'external-provider';
  credentialOwner: 'none' | 'organization' | 'deployment';
  baseUrl?: string;
  defaultModel?: string;
  enabled: boolean;
  configuration: Record<string, unknown>;
}

export interface ProviderConnectionSecret {
  connectionId: string;
  encryptedCredentials: string;
  keyVersion: string;
}
```

`configuration` contains only non-secret schema-validated fields. Secret inputs use write-only DTO fields and never return from read endpoints.

Rules:

- organization connections are configured by administrators;
- deployment-owned connections are neutral and optional;
- encrypt credentials with a deployment master key;
- support key versioning and rotation;
- never put keys in BullMQ payloads;
- resolve decrypted credentials only at provider invocation;
- never return or log decrypted keys;
- show only masked fingerprints;
- audit creation, testing, updates, rotation, and disabling.

---

## 14. Worker Protocol

The Python worker owns FFmpeg inspection, normalization, local ASR, diarization, optional alignment, model management, and capability reporting.

The canonical cross-language protocol lives under:

```text
contracts/worker-protocol
```

Use versioned JSON Schema or OpenAPI documents as the source of truth. Generate or validate TypeScript and Python models from the same schemas; do not maintain unrelated handwritten contracts.

Workers:

- register through the API with scoped registration tokens;
- pull jobs through an authenticated worker-control API;
- never connect directly to PostgreSQL or Redis;
- never receive provider credentials;
- receive short-lived signed media-download and result-upload URLs;
- use heartbeats and expiring job leases;
- report version, CPU, GPU, VRAM, installed models, capabilities, active jobs, and health;
- support explicit cancellation and honest recovery after disconnection.

The API container must not require GPU access.

A host-native worker installation is not required initially. CPU processing through the reference worker container is mandatory, and CUDA is an optional worker image.

---

## 15. Media, Diarization, and Summaries

Initial media formats:

```text
WAV MP3 M4A AAC FLAC OGG OPUS MP4 WebM MKV
```

Media rules:

- validate actual content, not only the extension;
- keep original media unchanged;
- calculate SHA-256;
- warn about duplicates only inside one organization;
- stream large uploads directly to storage;
- never buffer an entire large upload in application memory;
- generate a mono, 16 kHz PCM WAV derivative where the selected ASR requires it;
- sanitize filenames and object keys.

Diarization is separate from ASR. When it is separate:

1. align words with diarization intervals;
2. assign by greatest overlap;
3. rebuild segments around speaker changes;
4. preserve uncertainty;
5. never invent real-world identities.

Do not implement permanent voiceprints or workplace emotion scoring.

Summaries are independently configurable and use structured output. Generated decisions and actions reference transcript timestamps where possible. Inferred owners or dates are never presented as confirmed facts.

---

## 16. Usage and Non-Monetary Budgets

Community usage records factual processing, including zero-cost local jobs.

```ts
// SPDX-License-Identifier: AGPL-3.0-only
export interface UsageEvent {
  id: string;
  organizationId: string;
  userId?: string;
  teamId?: string;
  projectId?: string;
  processingRunId: string;
  executionLocation:
    | 'server-worker'
    | 'remote-worker'
    | 'external-provider';
  credentialOwner:
    | 'none'
    | 'organization'
    | 'deployment';
  mediaLeftCustomerInfrastructure: boolean;
  provider: string;
  model: string;
  audioDurationMs: number;
  estimatedExternalCostMicroUsd?: bigint;
  createdAt: Date;
}
```

Public usage records must not contain customer charges, wallet transactions, proprietary rate IDs, deposits, or payment identifiers.

Community budgets may limit audio duration, storage, providers, models, organizations, teams, users, projects, folders, API tokens, and presets. They may warn or hard-stop but never reserve or settle real money.

Concurrent hard-stop budgets require transactional authorization or reservations so parallel jobs cannot exceed a limit.

---

## 17. Search

Use PostgreSQL full-text search first.

Search titles, timestamped transcript segments, speakers, summaries, actions, tags, folders, and projects. Filter by organization and permissions before returning results.

Add `pgvector` only after approval of a concrete semantic-search feature.

---

## 18. API and Wire Contracts

Use REST with OpenAPI and a versioned base path:

```text
/api/v1/organizations
/api/v1/teams
/api/v1/projects
/api/v1/recordings
/api/v1/media
/api/v1/processing-runs
/api/v1/transcripts
/api/v1/summaries
/api/v1/provider-connections
/api/v1/presets
/api/v1/policies
/api/v1/budgets
/api/v1/usage
/api/v1/workers
/api/v1/exports
```

Rules:

- validate every input;
- keep controllers thin;
- enforce organization access in services;
- return DTOs, never entities;
- paginate collections with one documented cursor format;
- return a documented error envelope with stable machine-readable codes;
- support idempotency keys for uploads, processing requests, worker results, and other retryable writes;
- use short-lived signed URLs or scoped API transfer URLs;
- never trust frontend permission checks.

Domain values may use `Date` and `bigint`. JSON/OpenAPI DTOs use ISO-8601 UTC strings and decimal strings respectively. Never serialize JavaScript `bigint` directly.

---

## 19. Queue Rules

Initial queues:

```text
media
transcription
diarization
summary
export
maintenance
```

Queue payloads contain identifiers and routing metadata, never media bytes, transcript bodies, provider keys, raw provider results, or signed URLs with unnecessarily long lifetimes.

Separate queue producers and processors. Progress must reflect information actually available from the worker or provider; never invent precise percentages.

---

## 20. NestJS and Nuxt Rules

NestJS:

- native ESM only;
- use dependency injection and explicit tokens;
- keep modules cohesive and composition roots thin;
- keep provider SDKs in adapters;
- validate configuration and fail fast;
- use structured logs with redaction;
- avoid circular module dependencies.

Nuxt:

- use Nuxt UI;
- prefer server-side fetching where it improves security or resilience;
- use the generated API client;
- keep provider forms schema-driven;
- virtualize large transcripts;
- synchronize transcript segments and playback;
- preserve unsaved edits in the browser;
- make upload and processing state resilient to refresh;
- clearly label customer-worker and external-provider processing;
- never rely on frontend authorization.

---

## 21. Security and Privacy

Treat recordings, transcripts, summaries, credentials, and worker tokens as sensitive.

- do not send media externally without an approved recorded route;
- show when media leaves customer-controlled infrastructure;
- encrypt credentials and rotate the deployment key safely;
- validate uploads and sanitize filenames;
- run containers and workers as non-root;
- support deletion and configurable retention;
- keep telemetry optional and disabled by default;
- never use customer content for training without explicit informed opt-in;
- allow a self-hosted administrator to disable every external provider;
- do not place secrets or content in logs, queues, metrics labels, or error reports.

---

## 22. Testing

Prefer integration tests, end-to-end tests for critical flows, and focused unit/property tests for pure logic.

Required areas as their features are introduced:

- first-run setup and Better Auth integration;
- organization authorization and tenant isolation;
- PostgreSQL migrations and supported upgrades;
- streamed media uploads and signed URLs;
- provider normalization and raw-result preservation;
- transcript revisions;
- processing state transitions and idempotency;
- budget concurrency;
- worker protocol compatibility;
- worker leases, cancellation, disconnection, and recovery;
- search permission filtering;
- exports;
- credential encryption and rotation.

Every provider adapter covers:

- synchronous and asynchronous completion where supported;
- plain transcript;
- word and segment timestamps;
- diarization and language detection where supported;
- errors, rate limits, malformed responses, and cancellation;
- raw-result preservation;
- model-aware capabilities.

Live provider tests are opt-in.

Public CI must independently run frozen install, lint, typecheck, tests, integration tests, build, OCI image build, and Compose validation.

---

## 23. Container-First Deployment

Publish versioned OCI images. Docker Compose is the supported reference deployment, not an application runtime dependency.

Reference services:

```text
web
api
postgres
redis
optional minio
optional cpu or nvidia worker
```

Rules:

- Nuxt and Nest run as separate services;
- `web` and `api` remain stateless except that local-filesystem mode gives `api` a documented persistent media volume;
- PostgreSQL, Redis, and S3 endpoints are externally configurable;
- application code must not access the Docker socket;
- application configuration must not depend on Compose service names;
- migrations run as an explicit release command or one-shot job;
- pin production image versions;
- provide health and readiness endpoints;
- support secret files in addition to environment variables;
- document persistent volumes, backup, restore, upgrades, rollback, reverse proxies, NVIDIA Container Toolkit, and remote-worker registration;
- make air-gapped image and model import possible;
- do not require Kubernetes.

Suggested reference profiles:

```bash
docker compose --profile cpu up -d
docker compose --profile nvidia up -d
docker compose --profile external-processing up -d
```

---

## 24. Licensing

Community application code is `AGPL-3.0-only`.

Use SPDX headers in new source files:

```ts
// SPDX-License-Identifier: AGPL-3.0-only
```

Do not copy proprietary code into this repository. Keep third-party notices current and require contributor agreements according to `CONTRIBUTING.md`.

---

## 25. Delivery Plan

### Milestone 0 — Repository Bootstrap

Prove:

- standalone public workspace and frozen lockfile;
- clean-export install, typecheck, test, and build;
- public boundary verification;
- web and API skeletons;
- worker-protocol schema skeleton;
- OCI build and Compose validation;
- public licensing and contributor files.

### Milestone 1 — Authenticated Community Vertical Slice

Build:

- Nuxt web service;
- NestJS API service;
- PostgreSQL;
- Redis/BullMQ;
- local filesystem storage;
- Better Auth local credentials;
- one-time first-run administrator and initial organization setup;
- streamed file upload;
- FFmpeg inspection;
- versioned worker protocol;
- minimal co-located CPU faster-whisper worker;
- generic OpenAI-compatible provider;
- transcript playback and revision editing;
- Markdown, TXT, JSON, SRT, and VTT exports.

Acceptance:

```text
An administrator runs Docker Compose, completes protected first-run setup,
signs in, uploads an M4A file, transcribes it on the CPU worker, edits the
transcript, and exports Markdown.
```

### Milestone 2 — Organizations and Shared Repository

Build invitations, additional users, organization administration, teams, organization provider connections, shared recordings, and permission-filtered search.

### Milestone 3 — Distributed Workers

Build CUDA images, remote registration, capability discovery, heartbeats, leases, short-lived transfer credentials, cancellation, recovery, and worker-health UI.

The CPU worker already exists from Milestone 1; do not build a second implementation.

### Milestone 4 — Presets, Projects, and Budgets

Build processing presets, teams, projects/folders, user/team audio-hour budgets, provider allowlists, and local-versus-external reporting.

### Milestone 5 — Diarization and Summaries

Build pyannote diarization, speaker renaming, structured summaries, timestamp-linked decisions/actions, comments, and review.

---

## 26. Initial Non-Goals

Do not initially build:

- Electron, SQLite, or desktop synchronization;
- native mobile applications;
- meeting bots;
- realtime diarization;
- permanent voice identification;
- emotion analysis;
- collaborative live editing;
- dozens of providers;
- Kubernetes operators;
- a visual workflow designer;
- mandatory vector search;
- payment, wallet, proprietary licensing, SAML, SCIM, or legal-hold code.

---

## 27. Definition of Done

A Community feature is complete when:

- the browser flow works;
- authorization and organization isolation are enforced;
- migrations and DTO/OpenAPI changes are included;
- relevant integration tests pass;
- secrets and transcript content are not unnecessarily logged;
- CPU-only deployment remains supported;
- OCI images and Docker Compose still work where relevant;
- the clean exported repository installs, typechecks, tests, and builds;
- errors are actionable;
- documentation is updated.
