# SPDX-License-Identifier: AGPL-3.0-only

import pytest

from spokenbase_worker.settings import WorkerSettings


def test_queue_rejects_plaintext_broker_without_explicit_opt_in() -> None:
    with pytest.raises(ValueError, match="plaintext Redpanda access"):
        WorkerSettings.from_env(
            {
                "WORKER_QUEUE_ENABLED": "true",
                "REDPANDA_BROKERS": "redpanda:9092",
                "REDPANDA_SECURITY_PROTOCOL": "PLAINTEXT",
            }
        )


def test_local_compose_can_explicitly_enable_plaintext_broker() -> None:
    settings = WorkerSettings.from_env(
        {
            "WORKER_QUEUE_ENABLED": "true",
            "WORKER_ALLOW_INSECURE_REDPANDA": "true",
            "REDPANDA_BROKERS": "redpanda:9092",
            "REDPANDA_SECURITY_PROTOCOL": "PLAINTEXT",
        }
    )

    assert settings.queue_enabled is True
    assert settings.redpanda_brokers == ("redpanda:9092",)
    assert settings.supported_stages == ()


def test_broker_password_is_not_in_settings_representation() -> None:
    settings = WorkerSettings(
        queue_enabled=True,
        redpanda_security_protocol="SASL_SSL",
        redpanda_sasl_username="worker",
        redpanda_sasl_password="super-secret",
        redpanda_ssl_ca_location="/run/secrets/redpanda-ca.pem",
    )

    assert "super-secret" not in repr(settings)
