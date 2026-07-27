# SPDX-License-Identifier: AGPL-3.0-only

import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from pydantic import ValidationError as PydanticValidationError

from spokenbase_worker.protocol import ProcessingCommand


def command_payload() -> dict[str, object]:
    return {
        "protocolVersion": "1",
        "messageId": str(uuid4()),
        "idempotencyKey": "processing-run:attempt:1",
        "createdAt": "2026-07-27T12:00:00Z",
        "commandType": "run-stage",
        "processingRunId": str(uuid4()),
        "organizationId": str(uuid4()),
        "stage": "transcribe",
        "attempt": 1,
        "requiredCapabilities": ["asr", "cpu"],
    }


def command_schema() -> dict[str, object]:
    schema_path = (
        Path(__file__).parents[2]
        / "contracts"
        / "worker-protocol"
        / "schemas"
        / "processing-command.schema.json"
    )
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_processing_command_matches_canonical_schema() -> None:
    payload = command_payload()
    Draft202012Validator(
        command_schema(),
        format_checker=FormatChecker(),
    ).validate(payload)

    command = ProcessingCommand.model_validate(payload)

    assert command.model_dump(mode="json", by_alias=True) == payload


def test_processing_command_rejects_content_or_credentials() -> None:
    payload = command_payload()
    payload["mediaBytes"] = "not-allowed"

    with pytest.raises(ValidationError):
        Draft202012Validator(command_schema()).validate(payload)

    with pytest.raises(PydanticValidationError):
        ProcessingCommand.model_validate(payload)


def test_processing_command_rejects_duplicate_capabilities_and_naive_time() -> None:
    duplicate_capabilities = command_payload()
    duplicate_capabilities["requiredCapabilities"] = ["asr", "asr"]

    with pytest.raises(PydanticValidationError):
        ProcessingCommand.model_validate(duplicate_capabilities)

    naive_time = command_payload()
    naive_time["createdAt"] = "2026-07-27T12:00:00"

    with pytest.raises(PydanticValidationError):
        ProcessingCommand.model_validate(naive_time)
