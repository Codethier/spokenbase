# SPDX-License-Identifier: AGPL-3.0-only

"""Redpanda command consumer for the worker process."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from threading import Event, Thread
from typing import Protocol
from uuid import uuid4

from confluent_kafka import Consumer, KafkaException, Producer
from pydantic import ValidationError

from spokenbase_worker.protocol import (
    DeadLetterEvent,
    ProcessingCommand,
    ProcessingEvent,
)
from spokenbase_worker.settings import WorkerSettings
from spokenbase_worker.state import RuntimeState

logger = logging.getLogger(__name__)


class CommandHandler(Protocol):
    """Return an immediate disposition; never run media processing inline."""

    def handle(self, command: ProcessingCommand) -> ProcessingEvent: ...


class MilestoneZeroCommandHandler:
    """Honest placeholder until processing handlers are implemented."""

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings

    def handle(self, command: ProcessingCommand) -> ProcessingEvent:
        enabled = command.stage in self._settings.supported_stages
        error_code = "WORKER_STAGE_NOT_IMPLEMENTED" if enabled else "WORKER_CAPABILITY_NOT_ENABLED"
        return ProcessingEvent(
            message_id=uuid4(),
            causation_message_id=command.message_id,
            idempotency_key=f"{command.message_id}:rejected",
            created_at=datetime.now(UTC),
            event_type="rejected",
            processing_run_id=command.processing_run_id,
            organization_id=command.organization_id,
            stage=command.stage,
            worker_id=self._settings.worker_id,
            error_code=error_code,
            retryable=False,
        )


class RedpandaCommandConsumer:
    """Owns one thread-confined Kafka consumer and producer pair."""

    def __init__(
        self,
        settings: WorkerSettings,
        state: RuntimeState,
        handler: CommandHandler | None = None,
    ) -> None:
        self._settings = settings
        self._state = state
        self._handler = handler or MilestoneZeroCommandHandler(settings)
        self._stop_requested = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if not self._settings.queue_enabled or self._thread is not None:
            return
        self._stop_requested.clear()
        self._thread = Thread(
            target=self._run,
            name="spokenbase-redpanda-consumer",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 10.0) -> None:
        self._stop_requested.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout_seconds)
            if self._thread.is_alive():
                self._state.mark_queue_disconnected("REDPANDA_SHUTDOWN_TIMEOUT")
                return
            self._thread = None

    def _run(self) -> None:
        while not self._stop_requested.is_set():
            try:
                self._run_session()
            except (KafkaException, RuntimeError):
                self._state.mark_queue_disconnected("REDPANDA_SESSION_FAILED")
                logger.warning("redpanda_session_failed", exc_info=False)
            # This is the process-level supervisor boundary. A bad handler must
            # make readiness fail and retry the uncommitted record, not kill the worker.
            except Exception as error:  # noqa: BLE001
                self._state.mark_queue_disconnected("REDPANDA_UNEXPECTED_FAILURE")
                logger.error(
                    "redpanda_unexpected_failure exception_type=%s",
                    type(error).__name__,
                )

            self._stop_requested.wait(timeout=self._settings.redpanda_reconnect_backoff_seconds)

    def _run_session(self) -> None:
        consumer_config = self._settings.common_redpanda_config()
        consumer_config.update(
            {
                "group.id": self._settings.redpanda_consumer_group,
                "enable.auto.commit": False,
                "enable.auto.offset.store": False,
                "auto.offset.reset": "earliest",
                "isolation.level": "read_committed",
                "allow.auto.create.topics": False,
            }
        )
        producer_config = self._settings.common_redpanda_config()
        producer_config.update(
            {
                "enable.idempotence": True,
                "acks": "all",
                "compression.type": "zstd",
                "linger.ms": 5,
            }
        )

        consumer = Consumer(consumer_config)
        producer = Producer(producer_config)
        try:
            metadata = consumer.list_topics(timeout=10)
            if not metadata.brokers:
                raise RuntimeError("Redpanda returned no broker metadata")

            consumer.subscribe(list(self._settings.redpanda_command_topics))
            self._state.mark_queue_connected()

            while not self._stop_requested.is_set():
                message = consumer.poll(timeout=0.5)
                if message is None:
                    continue
                if message.error() is not None:
                    raise KafkaException(message.error())

                self._handle_message(consumer, producer, message)
        finally:
            try:
                producer.flush(timeout=5)
            finally:
                consumer.close()
                self._state.mark_queue_disconnected()

    def _handle_message(
        self,
        consumer: Consumer,
        producer: Producer,
        message: object,
    ) -> None:
        raw_value = message.value() or b""
        try:
            command = ProcessingCommand.model_validate_json(raw_value)
        except (ValidationError, json.JSONDecodeError):
            self._publish_dead_letter(
                producer,
                message=message,
                raw_value=raw_value,
                error_code="INVALID_PROCESSING_COMMAND",
            )
        else:
            expected_key = str(command.processing_run_id).encode("utf-8")
            if message.key() != expected_key:
                self._publish_dead_letter(
                    producer,
                    message=message,
                    raw_value=raw_value,
                    error_code="INVALID_PROCESSING_COMMAND_KEY",
                )
            else:
                event = self._handler.handle(command)
                self._publish(
                    producer,
                    topic=self._settings.redpanda_event_topic,
                    key=str(command.processing_run_id),
                    payload=event,
                )

        consumer.commit(message=message, asynchronous=False)
        self._state.mark_message_handled()

    def _publish_dead_letter(
        self,
        producer: Producer,
        *,
        message: object,
        raw_value: bytes,
        error_code: str,
    ) -> None:
        payload_hash = hashlib.sha256(raw_value).hexdigest()
        source_coordinate = f"{message.topic()}:{message.partition()}:{message.offset()}".encode()
        source_hash = hashlib.sha256(source_coordinate).hexdigest()
        event = DeadLetterEvent(
            message_id=uuid4(),
            idempotency_key=f"dead-letter:{source_hash}",
            created_at=datetime.now(UTC),
            worker_id=self._settings.worker_id,
            source_topic=message.topic(),
            source_partition=message.partition(),
            source_offset=message.offset(),
            payload_sha256=payload_hash,
            error_code=error_code,
        )
        self._publish(
            producer,
            topic=self._settings.redpanda_dead_letter_topic,
            key=payload_hash,
            payload=event,
        )

    @staticmethod
    def _publish(
        producer: Producer,
        *,
        topic: str,
        key: str,
        payload: ProcessingEvent | DeadLetterEvent,
    ) -> None:
        delivery_errors: list[str] = []

        def on_delivery(error: object, _message: object) -> None:
            if error is not None:
                delivery_errors.append("REDPANDA_DELIVERY_FAILED")

        encoded = json.dumps(
            payload.model_dump(mode="json", by_alias=True),
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        producer.produce(
            topic=topic,
            key=key.encode("utf-8"),
            value=encoded,
            on_delivery=on_delivery,
        )
        remaining = producer.flush(timeout=10)
        if remaining or delivery_errors:
            raise RuntimeError("Redpanda event delivery was not confirmed")
