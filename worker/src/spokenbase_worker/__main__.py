# SPDX-License-Identifier: AGPL-3.0-only

"""Run the worker as a single-process Uvicorn service."""

from __future__ import annotations

import uvicorn

from spokenbase_worker.main import create_app
from spokenbase_worker.settings import WorkerSettings


def main() -> None:
    settings = WorkerSettings.from_env()
    uvicorn.run(
        create_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        workers=1,
        access_log=False,
    )


if __name__ == "__main__":
    main()
