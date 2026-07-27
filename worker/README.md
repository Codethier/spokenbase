# Spokenbase Worker

The worker will own FFmpeg inspection and normalization, faster-whisper
transcription, pyannote diarization, optional alignment, model management, and
capability reporting.

It is a small pull-based Python process fed through the Community API's
BullMQ-backed job system. BullMQ remains server-side; the worker leases jobs
over an authenticated HTTP control API, so remote workers require no inbound
ports and never receive database, Redis, or provider credentials.

Milestone 0 contains only packaging and protocol structure.
