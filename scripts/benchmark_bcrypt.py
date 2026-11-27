"""Run with python -m scripts.benchmark_bcrypt; uses no database or real users."""

import argparse
import asyncio
import json
import os
from time import perf_counter

import bcrypt


async def measure(threaded: bool, hashed: str, operations: int) -> dict[str, float]:
    from app.core.security import verify_password, verify_password_async

    delays = []
    finished = False

    async def heartbeat() -> None:
        while not finished:
            started = perf_counter()
            await asyncio.sleep(0.005)
            delays.append(max(0, perf_counter() - started - 0.005))

    ticker = asyncio.create_task(heartbeat())
    await asyncio.sleep(0)
    started = perf_counter()
    try:
        if threaded:
            results = await asyncio.gather(
                *(
                    verify_password_async("benchmark-password", hashed)
                    for _ in range(operations)
                )
            )
        else:
            results = [
                verify_password("benchmark-password", hashed) for _ in range(operations)
            ]
        assert all(results)
        elapsed = perf_counter() - started
        await asyncio.sleep(0.01)
    finally:
        finished = True
        await ticker
    return {"wall_seconds": elapsed, "max_event_loop_delay_ms": max(delays) * 1000}


async def run(rounds: int, operations: int) -> None:
    hashed = bcrypt.hashpw(b"benchmark-password", bcrypt.gensalt(rounds)).decode()
    print(
        json.dumps(
            {
                "rounds": rounds,
                "operations": operations,
                "blocking": await measure(False, hashed, operations),
                "threaded": await measure(True, hashed, operations),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, choices=range(4, 15), default=12)
    parser.add_argument("--operations", type=int, choices=range(1, 17), default=4)
    args = parser.parse_args()
    # Settings are needed by security.py; this isolated process uses test values.
    os.environ.update(
        APP_ENV="test",
        DATABASE_URL="sqlite+aiosqlite://",
        SECRET_KEY="test-secret-benchmark-only-1234567890123456",
    )
    asyncio.run(run(args.rounds, args.operations))


if __name__ == "__main__":
    main()
