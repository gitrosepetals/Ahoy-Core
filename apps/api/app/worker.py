"""Background job runner.

    uv run python -m app.worker          # loop forever
    uv run python -m app.worker --once   # run every job once (cron / smoke test)

Each job runs in its own transaction guarded by a Postgres advisory xact lock, so several
workers (or an embedded worker plus a standalone one) never run the same job concurrently.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time
import zlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import SessionLocal
from app.observability import setup_observability
from app.services.jobs import expire_overdue_posts, send_expiry_reminders
from app.services.leads import rollup_daily_metrics
from app.services.publishing import publish_due_posts
from app.services.reviews import post_due_review_replies, sync_all_reviews, sync_gbp_performance

logger = logging.getLogger("ahoy.worker")

JobFn = Callable[[AsyncSession, Settings], Awaitable[object]]


@dataclass
class Job:
    name: str
    every_seconds: int
    fn: JobFn

    @property
    def lock_key(self) -> int:
        return zlib.crc32(f"ahoy-job:{self.name}".encode())


async def _expire(db: AsyncSession, _settings: Settings) -> int:
    return await expire_overdue_posts(db)


JOBS: list[Job] = [
    Job("publish_due_posts", 60, publish_due_posts),
    Job("send_expiry_reminders", 300, send_expiry_reminders),
    Job("expire_overdue_posts", 300, _expire),
    # Hourly + idempotent (re-counts today and the 2 prior days) instead of once nightly, so
    # the Treasure Map is never more than an hour stale and late Twilio callbacks are absorbed.
    Job("rollup_daily_metrics", 3600, rollup_daily_metrics),
    Job("sync_all_reviews", 1800, sync_all_reviews),
    Job("post_due_review_replies", 300, post_due_review_replies),
    Job("sync_gbp_performance", 6 * 3600, sync_gbp_performance),
]


def register(job: Job) -> None:
    """Later slices add jobs (rollups, review sync) without editing this list in place."""
    if all(j.name != job.name for j in JOBS):
        JOBS.append(job)


async def run_job(job: Job, settings: Settings) -> object | None:
    """Run one job in its own transaction. Returns the job's result, or None if locked."""
    async with SessionLocal() as db:
        got = await db.scalar(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": job.lock_key})
        if not got:
            return None
        try:
            result = await job.fn(db, settings)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.exception("Job %s failed", job.name)
            if settings.sentry_dsn:
                import sentry_sdk

                sentry_sdk.capture_exception(exc)
            return None
    if result:
        logger.info("Job %s -> %s", job.name, result)
    return result


async def run_once(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or get_settings()
    return {job.name: await run_job(job, settings) for job in JOBS}


async def run_forever(settings: Settings | None = None, stop: asyncio.Event | None = None) -> None:
    settings = settings or get_settings()
    stop = stop or asyncio.Event()
    last_run: dict[str, float] = {}
    logger.info("Worker started: %s", ", ".join(j.name for j in JOBS))
    while not stop.is_set():
        now = time.monotonic()
        for job in JOBS:
            if now - last_run.get(job.name, -1e9) >= job.every_seconds:
                last_run[job.name] = now
                await run_job(job, settings)
        try:
            await asyncio.wait_for(stop.wait(), timeout=5)
        except TimeoutError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="A-hoy background worker")
    parser.add_argument("--once", action="store_true", help="run every job once and exit")
    args = parser.parse_args()
    setup_observability(get_settings(), component="worker")
    if args.once:
        print(asyncio.run(run_once()))
    else:
        asyncio.run(run_forever())


if __name__ == "__main__":
    main()
