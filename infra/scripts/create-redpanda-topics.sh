#!/bin/sh
# SPDX-License-Identifier: AGPL-3.0-only

set -eu

brokers="${REDPANDA_BROKERS:?REDPANDA_BROKERS is required}"
admin_hosts="${REDPANDA_ADMIN_HOSTS:?REDPANDA_ADMIN_HOSTS is required}"
partitions="${REDPANDA_TOPIC_PARTITIONS:-6}"
replicas="${REDPANDA_TOPIC_REPLICAS:-1}"

rpk cluster config set auto_create_topics_enabled false \
  --no-confirm \
  -X "admin.hosts=$admin_hosts" \
  -X "brokers=$brokers"

create_topic() {
  topic="$1"
  retention_ms="$2"

  rpk topic create "$topic" \
    --if-not-exists \
    --partitions "$partitions" \
    --replicas "$replicas" \
    --topic-config cleanup.policy=delete \
    --topic-config "retention.ms=$retention_ms" \
    -X "brokers=$brokers"
}

create_topic spokenbase.media.commands.v1 604800000
create_topic spokenbase.transcription.commands.v1 604800000
create_topic spokenbase.diarization.commands.v1 604800000
create_topic spokenbase.summary.commands.v1 604800000
create_topic spokenbase.export.commands.v1 604800000
create_topic spokenbase.maintenance.commands.v1 604800000
create_topic spokenbase.processing.events.v1 2592000000
create_topic spokenbase.processing.dead-letter.v1 2592000000
