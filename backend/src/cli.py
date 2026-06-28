"""CLI 入口 / CLI entry point.

用法: python -m src.cli run --ticks 5
"""

import asyncio
import argparse

from src.engine.orchestrator import Orchestrator


async def run_ticks(n: int) -> None:
    orch = Orchestrator()
    for i in range(n):
        result = await orch.run_tick()
        tick = result["tick"]
        narrative = result.get("narrative", "")
        actions = result.get("events", [])
        errors = result.get("errors", [])

        print(f"\n{'='*60}")
        print(f"[Tick {tick}]")
        if narrative:
            print(f"  📖 {narrative}")
        for action in actions[:5]:
            print(f"  ⚡ {action}")
        if errors:
            print(f"  ❌ Errors: {errors}")
        print(f"{'='*60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIGameWorld CLI")
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("run", help="Run N ticks")
    run_parser.add_argument("--ticks", type=int, default=5, help="Number of ticks to run")

    args = parser.parse_args()

    if args.command == "run":
        asyncio.run(run_ticks(args.ticks))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
