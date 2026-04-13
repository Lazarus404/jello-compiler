#!/usr/bin/env python3
"""Benchmark REPL startup time and per-line latency.

Measures:
  - startup: Time from launch until first prompt (empty input exits immediately).
  - single_line: Time for one line (let i = 2) to complete.
  - two_line: Time for two lines (let i = 2; i) using incremental compile.
"""
import argparse
import os
import statistics
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_JELLOC = os.path.join(ROOT, "jelloc", "target", "release", "jelloc")


def run_repl(jelloc: str, input_lines: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [jelloc, "--repl"],
        input=input_lines,
        capture_output=True,
        text=True,
        timeout=30,
    )


def time_startup(jelloc: str, runs: int, warmup: int) -> list[float]:
    """Time from process start until first prompt (empty input exits immediately)."""
    times = []
    for _ in range(warmup):
        run_repl(jelloc, "")
    for _ in range(runs):
        t0 = time.perf_counter()
        run_repl(jelloc, "")
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    return times


def time_single_line(jelloc: str, runs: int, warmup: int) -> list[float]:
    """Time for one line (let i = 2) to complete."""
    input_line = "let i = 2"
    times = []
    for _ in range(warmup):
        run_repl(jelloc, input_line)
    for _ in range(runs):
        t0 = time.perf_counter()
        p = run_repl(jelloc, input_line)
        t1 = time.perf_counter()
        if p.returncode != 0:
            raise SystemExit(f"REPL failed (exit {p.returncode}): {p.stderr or p.stdout}")
        times.append((t1 - t0) * 1000)
    return times


def time_two_lines(jelloc: str, runs: int, warmup: int) -> list[float]:
    """Time for two lines (let i = 2; i) using incremental compile."""
    input_lines = "let i = 2\ni"
    times = []
    for _ in range(warmup):
        run_repl(jelloc, input_lines)
    for _ in range(runs):
        t0 = time.perf_counter()
        p = run_repl(jelloc, input_lines)
        t1 = time.perf_counter()
        if p.returncode != 0:
            raise SystemExit(f"REPL failed (exit {p.returncode}): {p.stderr or p.stdout}")
        if "2" not in p.stdout:
            raise SystemExit(f"REPL output unexpected: {p.stdout!r}")
        times.append((t1 - t0) * 1000)
    return times


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmark REPL startup and per-line latency")
    ap.add_argument("--jelloc", default=DEFAULT_JELLOC, help="Path to jelloc binary")
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--warmup", type=int, default=3)
    args = ap.parse_args()

    if not os.path.exists(args.jelloc):
        raise SystemExit(f"error: jelloc not found at {args.jelloc} (build with: cargo build -p jelloc --release)")

    print("REPL benchmarks (jelloc --repl)")
    print()

    # Startup
    startup = time_startup(args.jelloc, args.runs, args.warmup)
    print(f"Startup (empty input, exit): median={statistics.median(startup):.1f}ms, mean={statistics.fmean(startup):.1f}ms")

    # Single line
    single = time_single_line(args.jelloc, args.runs, args.warmup)
    print(f"Single line (let i = 2): median={statistics.median(single):.1f}ms, mean={statistics.fmean(single):.1f}ms")

    # Two lines (incremental)
    two = time_two_lines(args.jelloc, args.runs, args.warmup)
    print(f"Two lines (let i=2; i): median={statistics.median(two):.1f}ms, mean={statistics.fmean(two):.1f}ms")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
