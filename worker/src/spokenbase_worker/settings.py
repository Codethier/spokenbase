# SPDX-License-Identifier: AGPL-3.0-only

"""Environment-backed worker configuration with secure broker defaults."""

from __future__ import annotations

import os
import socket
from collections.abc import Mapping
from dataclasses import dataclass, field

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_SECURITY_PROTOCOLS = frozenset({"PLAINTEXT", "SSL", "SASL_PLAINTEXT", "SASL_SSL"})


def _read_bool(environment: Mapping[str, str], name: str, default: bool) -> bool:
    raw_value = environment.get(name)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _read_csv(environment: Mapping[str, str], name: str, default: str) -> tuple[str, ...]:
    values = tuple(value.strip() for value in environment.get(name, default).split(","))
    filtered = tuple(value for value in values if value)
    if not filtered:
        raise ValueError(f"{name} must contain at least one value")
    return filtered


def _read_optional_csv(environment: Mapping[str, str], name: str) -> tuple[str, ...]:
    raw_value = environment.get(name, "")
    if not raw_value.strip():
        return ()
    return _read_csv(environment, name, "")


@dataclass(frozen=True, slots=True)
class WorkerSettings:
    """Validated worker settings.

    Secret fields are excluded from the dataclass representation so accidental
    settings logging cannot expose broker credentials.
    """

    worker_id: str = field(default_factory=socket.gethostname)
    http_host: str = "127.0.0.1"
    http_port: int = 8080
    queue_enabled: bool = False
    allow_insecure_redpanda: bool = False
    redpanda_brokers: tuple[str, ...] = ("localhost:19092",)
    redpanda_security_protocol: str = "PLAINTEXT"
    redpanda_sasl_mechanism: str = "SCRAM-SHA-256"
    redpanda_sasl_username: str | None = field(default=None, repr=False)
    redpanda_sasl_password: str | None = field(default=None, repr=False)
    redpanda_ssl_ca_location: str | None = None
    redpanda_consumer_group: str = "spokenbase-worker-cpu-v1"
    redpanda_command_topics: tuple[str, ...] = (
        "spokenbase.media.commands.v1",
        "spokenbase.transcription.commands.v1",
        "spokenbase.diarization.commands.v1",
    )
    redpanda_event_topic: str = "spokenbase.processing.events.v1"
    redpanda_dead_letter_topic: str = "spokenbase.processing.dead-letter.v1"
    redpanda_reconnect_backoff_seconds: float = 2.0
    supported_stages: tuple[str, ...] = ()
    gpu_model: str | None = None

    def __post_init__(self) -> None:
        if not self.worker_id or len(self.worker_id) > 128:
            raise ValueError("worker_id must contain between 1 and 128 characters")
        if not 1 <= self.http_port <= 65535:
            raise ValueError("http_port must be between 1 and 65535")
        if not self.redpanda_brokers:
            raise ValueError("at least one Redpanda broker is required")
        if not self.redpanda_command_topics:
            raise ValueError("at least one Redpanda command topic is required")
        if self.redpanda_reconnect_backoff_seconds <= 0:
            raise ValueError("redpanda_reconnect_backoff_seconds must be positive")

        protocol = self.redpanda_security_protocol.upper()
        if protocol not in _SECURITY_PROTOCOLS:
            raise ValueError("unsupported Redpanda security protocol")

        if not self.queue_enabled:
            return
        if protocol in {"PLAINTEXT", "SASL_PLAINTEXT"} and not self.allow_insecure_redpanda:
            raise ValueError(
                "plaintext Redpanda access requires WORKER_ALLOW_INSECURE_REDPANDA=true"
            )
        if protocol.startswith("SASL_") and (
            not self.redpanda_sasl_username or not self.redpanda_sasl_password
        ):
            raise ValueError("SASL Redpanda access requires a username and password")
        if protocol in {"SSL", "SASL_SSL"} and not self.redpanda_ssl_ca_location:
            raise ValueError("TLS Redpanda access requires REDPANDA_SSL_CA_LOCATION")

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None) -> WorkerSettings:
        values = os.environ if environment is None else environment
        return cls(
            worker_id=values.get("WORKER_ID", socket.gethostname()).strip(),
            http_host=values.get("WORKER_HTTP_HOST", "127.0.0.1").strip(),
            http_port=int(values.get("WORKER_HTTP_PORT", "8080")),
            queue_enabled=_read_bool(values, "WORKER_QUEUE_ENABLED", False),
            allow_insecure_redpanda=_read_bool(
                values,
                "WORKER_ALLOW_INSECURE_REDPANDA",
                False,
            ),
            redpanda_brokers=_read_csv(
                values,
                "REDPANDA_BROKERS",
                "localhost:19092",
            ),
            redpanda_security_protocol=values.get(
                "REDPANDA_SECURITY_PROTOCOL",
                "PLAINTEXT",
            )
            .strip()
            .upper(),
            redpanda_sasl_mechanism=values.get(
                "REDPANDA_SASL_MECHANISM",
                "SCRAM-SHA-256",
            ).strip(),
            redpanda_sasl_username=values.get("REDPANDA_SASL_USERNAME"),
            redpanda_sasl_password=values.get("REDPANDA_SASL_PASSWORD"),
            redpanda_ssl_ca_location=values.get("REDPANDA_SSL_CA_LOCATION"),
            redpanda_consumer_group=values.get(
                "REDPANDA_CONSUMER_GROUP",
                "spokenbase-worker-cpu-v1",
            ).strip(),
            redpanda_command_topics=_read_csv(
                values,
                "REDPANDA_COMMAND_TOPICS",
                (
                    "spokenbase.media.commands.v1,"
                    "spokenbase.transcription.commands.v1,"
                    "spokenbase.diarization.commands.v1"
                ),
            ),
            redpanda_event_topic=values.get(
                "REDPANDA_EVENT_TOPIC",
                "spokenbase.processing.events.v1",
            ).strip(),
            redpanda_dead_letter_topic=values.get(
                "REDPANDA_DEAD_LETTER_TOPIC",
                "spokenbase.processing.dead-letter.v1",
            ).strip(),
            redpanda_reconnect_backoff_seconds=float(
                values.get("REDPANDA_RECONNECT_BACKOFF_SECONDS", "2")
            ),
            supported_stages=_read_optional_csv(values, "WORKER_SUPPORTED_STAGES"),
            gpu_model=values.get("WORKER_GPU_MODEL"),
        )

    def common_redpanda_config(self) -> dict[str, object]:
        config: dict[str, object] = {
            "bootstrap.servers": ",".join(self.redpanda_brokers),
            "client.id": self.worker_id,
            "security.protocol": self.redpanda_security_protocol,
        }
        if self.redpanda_security_protocol.startswith("SASL_"):
            config.update(
                {
                    "sasl.mechanism": self.redpanda_sasl_mechanism,
                    "sasl.username": self.redpanda_sasl_username,
                    "sasl.password": self.redpanda_sasl_password,
                }
            )
        if self.redpanda_security_protocol in {"SSL", "SASL_SSL"}:
            config["ssl.ca.location"] = self.redpanda_ssl_ca_location
        return config
