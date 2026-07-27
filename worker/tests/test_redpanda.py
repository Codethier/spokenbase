# SPDX-License-Identifier: AGPL-3.0-only

import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from spokenbase_worker.protocol import ProcessingCommand
from spokenbase_worker.redpanda import RedpandaCommandConsumer
from spokenbase_worker.settings import WorkerSettings
from spokenbase_worker.state import RuntimeState


class FakeMessage:
    def __init__(self, value: bytes, key: bytes | None = None) -> None:
        self._value = value
        self._key = key

    def value(self) -> bytes:
        return self._value

    def key(self) -> bytes | None:
        return self._key

    @staticmethod
    def topic() -> str:
        return "spokenbase.transcription.commands.v1"

    @staticmethod
    def partition() -> int:
        return 2

    @staticmethod
    def offset() -> int:
        return 9


class FakeProducer:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def produce(self, **record: object) -> None:
        self.records.append(record)
        callback = record["on_delivery"]
        callback(None, None)

    @staticmethod
    def flush(timeout: float) -> int:
        assert timeout == 10
        return 0


class FakeConsumer:
    def __init__(self) -> None:
        self.committed: list[FakeMessage] = []

    def commit(self, *, message: FakeMessage, asynchronous: bool) -> None:
        assert asynchronous is False
        self.committed.append(message)


def valid_command_bytes() -> bytes:
    return json.dumps(
        {
            "protocolVersion": "1",
            "messageId": str(uuid4()),
            "idempotencyKey": "run:attempt:1",
            "createdAt": "2026-07-27T12:00:00Z",
            "commandType": "run-stage",
            "processingRunId": str(uuid4()),
            "organizationId": str(uuid4()),
            "stage": "transcribe",
            "attempt": 1,
            "requiredCapabilities": ["asr"],
        }
    ).encode()


def valid_message() -> FakeMessage:
    raw_value = valid_command_bytes()
    processing_run_id = json.loads(raw_value)["processingRunId"]
    return FakeMessage(raw_value, str(processing_run_id).encode())


def validate_protocol_event(schema_name: str, event: dict[str, object]) -> None:
    schema_path = (
        Path(__file__).parents[2] / "contracts" / "worker-protocol" / "schemas" / schema_name
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(event)


def test_valid_command_emits_rejection_before_committing_offset() -> None:
    settings = WorkerSettings(worker_id="test-worker", queue_enabled=False)
    state = RuntimeState(queue_enabled=True)
    redpanda = RedpandaCommandConsumer(settings, state)
    consumer = FakeConsumer()
    producer = FakeProducer()
    message = valid_message()

    redpanda._handle_message(consumer, producer, message)

    assert consumer.committed == [message]
    assert len(producer.records) == 1
    assert producer.records[0]["topic"] == settings.redpanda_event_topic
    event = json.loads(producer.records[0]["value"])
    validate_protocol_event("processing-event.schema.json", event)
    assert event["eventType"] == "rejected"
    assert event["errorCode"] == "WORKER_CAPABILITY_NOT_ENABLED"
    assert state.snapshot().messages_handled == 1


def test_mismatched_record_key_is_dead_lettered() -> None:
    settings = WorkerSettings(worker_id="test-worker", queue_enabled=False)
    state = RuntimeState(queue_enabled=True)
    redpanda = RedpandaCommandConsumer(settings, state)
    consumer = FakeConsumer()
    producer = FakeProducer()
    message = FakeMessage(valid_command_bytes(), b"wrong-processing-run")

    redpanda._handle_message(consumer, producer, message)

    record = producer.records[0]
    event = json.loads(record["value"])
    validate_protocol_event("dead-letter-event.schema.json", event)
    assert record["topic"] == settings.redpanda_dead_letter_topic
    assert event["errorCode"] == "INVALID_PROCESSING_COMMAND_KEY"
    assert consumer.committed == [message]


def test_handler_failure_leaves_offset_uncommitted() -> None:
    class FailingHandler:
        @staticmethod
        def handle(_command: ProcessingCommand) -> object:
            raise ValueError("processing failed")

    settings = WorkerSettings(worker_id="test-worker", queue_enabled=False)
    state = RuntimeState(queue_enabled=True)
    redpanda = RedpandaCommandConsumer(settings, state, handler=FailingHandler())
    consumer = FakeConsumer()
    producer = FakeProducer()

    with pytest.raises(ValueError, match="processing failed"):
        redpanda._handle_message(consumer, producer, valid_message())

    assert consumer.committed == []
    assert producer.records == []
    assert state.snapshot().messages_handled == 0


def test_invalid_command_dead_letters_only_a_payload_hash() -> None:
    settings = WorkerSettings(worker_id="test-worker", queue_enabled=False)
    state = RuntimeState(queue_enabled=True)
    redpanda = RedpandaCommandConsumer(settings, state)
    consumer = FakeConsumer()
    producer = FakeProducer()
    raw_value = b'{"providerKey":"must-not-be-republished"}'
    message = FakeMessage(raw_value)

    redpanda._handle_message(consumer, producer, message)

    record = producer.records[0]
    assert record["topic"] == settings.redpanda_dead_letter_topic
    assert raw_value not in record["value"]
    dead_letter = json.loads(record["value"])
    validate_protocol_event("dead-letter-event.schema.json", dead_letter)
    assert dead_letter["errorCode"] == "INVALID_PROCESSING_COMMAND"
    assert len(dead_letter["payloadSha256"]) == 64
    assert consumer.committed == [message]
