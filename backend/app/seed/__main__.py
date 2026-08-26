"""CLI entry point: ``python -m app.seed``."""

from __future__ import annotations

import argparse
import asyncio
import logging

from app.core.config import settings
from app.core.database import dispose_engine, engine, session_scope
from app.models import Base
from app.seed import run


async def _main(reset: bool, demo: bool) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if reset:
        if settings.is_production:
            raise SystemExit("Refusing to --reset a production database.")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("schema recreated")

    async with session_scope() as db:
        report = await run(db, demo=demo)

    width = max(len(k) for k in report)
    for key, value in report.items():
        print(f"  {key.ljust(width)}  {value}")
    print(f"\nAdmin: {settings.BOOTSTRAP_ADMIN_EMAIL}")
    await dispose_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Frontline Prep database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop and recreate every table first (blocked in production)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="also generate a starter question bank from sample articles",
    )
    args = parser.parse_args()
    asyncio.run(_main(args.reset, args.demo))
