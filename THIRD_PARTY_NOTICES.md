# Third-Party Notices

This file will list bundled third-party software and required notices as
dependencies and distribution artifacts are introduced.

The package lockfiles and Python project metadata are dependency inventories,
not substitutes for release-time license review or an SBOM.

## Redpanda Community Edition

The reference Docker Compose deployment pulls Redpanda and the optional
Redpanda Console as external runtime images. They are not covered by the
Spokenbase AGPL license.

Redpanda's current documentation states that its Community Edition products
are free and source-available under the Redpanda Business Source License, which
includes use restrictions and a delayed conversion to Apache-2.0. Review the
terms before redistribution or commercial deployment:

https://docs.redpanda.com/streaming/current/get-started/licensing/overview/

Spokenbase uses Kafka-compatible client protocols and does not require
Redpanda enterprise features.
