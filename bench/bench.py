import argparse
import os
import re
import shutil
import statistics
import subprocess
import sys
import time


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_DIR = os.path.join(ROOT, "bench")
OUT_DIR = os.path.join(BENCH_DIR, "out")


def _first_existing(*paths: str) -> str | None:
    """Return the first path that exists, or None."""
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


# jellovm: Prefer build/ (release.sh output) over in-place bin/.
# release.sh: build/bin/jellovm
# In-place (cmake -S . -B .): bin/jellovm
# Standalone vm build can have format mismatch with jelloc-linked bytecode.
JELLOVM_CANDIDATES = [
    os.path.join(ROOT, "build", "bin", "jellovm"),
    os.path.join(ROOT, "build", "release", "bin", "jellovm"),
    os.path.join(ROOT, "build", "debug", "bin", "jellovm"),
    os.path.join(ROOT, "bin", "jellovm"),
    os.path.join(ROOT, "vm", "build", "bin", "jellovm"),
]
DEFAULT_JELLOVM = _first_existing(*JELLOVM_CANDIDATES) or JELLOVM_CANDIDATES[0]

# jelloc: cargo target or Makefile symlinks in build/<type>/bin
JELLOC_DEBUG_CANDIDATES = [
    os.path.join(ROOT, "jelloc", "target", "debug", "jelloc"),
    os.path.join(ROOT, "build", "debug", "bin", "jelloc"),
    os.path.join(ROOT, "build", "release", "bin", "jelloc"),
]
JELLOC_RELEASE_CANDIDATES = [
    os.path.join(ROOT, "jelloc", "target", "release", "jelloc"),
    os.path.join(ROOT, "build", "release", "bin", "jelloc"),
    os.path.join(ROOT, "build", "debug", "bin", "jelloc"),
]
DEFAULT_JELLOC = _first_existing(*JELLOC_DEBUG_CANDIDATES) or JELLOC_DEBUG_CANDIDATES[0]
DEFAULT_JELLOC_RELEASE = _first_existing(*JELLOC_RELEASE_CANDIDATES) or JELLOC_RELEASE_CANDIDATES[0]


def which_lua() -> list[str]:
    # Prefer plain Lua unless only LuaJIT exists.
    if shutil.which("lua"):
        return ["lua"]
    if shutil.which("luajit"):
        return ["luajit"]
    raise SystemExit("error: neither `lua` nor `luajit` found on PATH")


def run_checked(cmd: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=cwd or ROOT)


def compile_jello(jelloc: str, jellovm: str, src: str, out: str) -> None:
    if not os.path.exists(jelloc):
        raise SystemExit(f"error: jelloc not found at {jelloc} (build it first)")
    if not os.path.exists(jellovm):
        raise SystemExit(f"error: jellovm not found at {jellovm} (build_root missing?)")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    run_checked([jelloc, src, "--out", out])


def time_many(cmd: list[str], runs: int, warmup: int) -> tuple[list[float], str]:
    last_out = ""
    for _ in range(warmup):
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        if p.returncode != 0:
            raise SystemExit(
                f"error: {cmd[0]!r} exited {p.returncode}\n"
                f"  stderr: {p.stderr.strip()!r}\n"
                f"  stdout: {p.stdout.strip()!r}"
            )
        last_out = p.stdout
    times: list[float] = []
    for _ in range(runs):
        t0 = time.perf_counter()
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
        t1 = time.perf_counter()
        if p.returncode != 0:
            raise SystemExit(
                f"error: {cmd[0]!r} exited {p.returncode}\n"
                f"  stderr: {p.stderr.strip()!r}\n"
                f"  stdout: {p.stdout.strip()!r}"
            )
        last_out = p.stdout
        times.append(t1 - t0)
    return times, last_out


def fmt_ms(x: float) -> str:
    return f"{x * 1000:.2f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jellovm", default=DEFAULT_JELLOVM, help="Path override (debug/conformance only)")
    ap.add_argument("--jelloc", default=DEFAULT_JELLOC, help="Path override (debug/conformance only)")
    ap.add_argument("--release", action="store_true", help="Use release-built jelloc (faster compile)")
    ap.add_argument("--runs", type=int, default=int(os.environ.get("RUNS", "10")))
    ap.add_argument("--warmup", type=int, default=int(os.environ.get("WARMUP", "3")))
    ap.add_argument("--filter", default="", help="Regex filter for benchmark name")
    ap.add_argument("--no-compile", action="store_true", help="Skip jelloc compilation step")
    args = ap.parse_args()

    jelloc = args.jelloc
    if args.release:
        jelloc = DEFAULT_JELLOC_RELEASE

    # Validate binaries before running; give clear instructions if missing.
    jellovm = args.jellovm
    if not os.path.exists(jellovm):
        raise SystemExit(
            f"error: jellovm not found at {jellovm}\n"
            f"  Build with: cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build\n"
            f"  Or: ./configure && make"
        )
    if not os.path.exists(jelloc):
        raise SystemExit(
            f"error: jelloc not found at {jelloc}\n"
            f"  Build with: cargo build -p jelloc (debug) or cargo build -p jelloc --release"
        )

    print(f"jellovm: {jellovm}")
    print(f"jelloc:  {jelloc}")
    print()
    sys.stdout.flush()

    lua = which_lua()

    benches: list[dict[str, str]] = [
        {"name": "startup", "jello": "startup.jello", "lua": "startup.lua"},
        {"name": "fib", "jello": "fib.jello", "lua": "fib.lua"},
        {"name": "ackerman", "jello": "ackerman.jello", "lua": "ackerman.lua"},
        {"name": "fannkuch", "jello": "fannkuch.jello", "lua": "fannkuch.lua"},
        {"name": "recursive", "jello": "recursive.jello", "lua": "recursive.lua"},
        {"name": "tail_sum", "jello": "tail_sum.jello", "lua": "tail_sum.lua"},
        {"name": "nsieve", "jello": "nsieve.jello", "lua": "nsieve.lua"},
        {"name": "binary_trees", "jello": "binary_trees.jello", "lua": "binary_trees.lua"},
        {"name": "fp", "jello": "fp.jello", "lua": "fp.lua"},
        {"name": "module", "jello": "module.jello", "lua": "module.lua"},
        {"name": "nbodies", "jello": "nbodies.jello", "lua": "nbodies.lua"},
    ]

    rx: re.Pattern[str] | None = None
    if args.filter:
        rx = re.compile(args.filter)
        benches = [b for b in benches if rx.search(b["name"])]
        if not benches:
            raise SystemExit(f"error: no benchmarks matched --filter {args.filter!r}")

    print(f"Running {len(benches)} benchmarks ({args.runs} runs, {args.warmup} warmup)...")
    print()

    rows: list[dict[str, object]] = []
    for b in benches:
        name = b["name"]
        jello_src = os.path.join(BENCH_DIR, b["jello"]) if b["jello"] else ""
        lua_src = os.path.join(BENCH_DIR, b["lua"])
        jello_out = os.path.join(OUT_DIR, f"{name}.jlo")

        if jello_src and not args.no_compile:
            compile_jello(jelloc, args.jellovm, jello_src, jello_out)

        jt: list[float] = []
        jout = ""
        if jello_src:
            jt, jout = time_many([args.jellovm, jello_out], runs=args.runs, warmup=args.warmup)
        lt, lout = time_many(lua + [lua_src], runs=args.runs, warmup=args.warmup)

        # Basic correctness check: all our bench programs print exactly "ok".
        if jello_src and jout.strip() != "ok":
            raise SystemExit(
                f"error: {name}: jello output unexpected: {jout!r}\n"
                f"  cmd: {args.jellovm!r} {jello_out!r}\n"
                f"  cwd: {ROOT}"
            )
        if lout.strip() != "ok":
            raise SystemExit(f"error: {name}: lua output unexpected: {lout!r}")

        lmed = statistics.median(lt)
        lmean = statistics.fmean(lt)
        jmed = statistics.median(jt) if jt else float("nan")
        jmean = statistics.fmean(jt) if jt else float("nan")
        rows.append(
            {
                "name": name,
                "jmed": jmed,
                "lmed": lmed,
                "jmean": jmean,
                "lmean": lmean,
                "speedup": (lmed / jmed) if jmed > 0 else float("nan"),
            }
        )

    # Summary table
    print(f"Lua runner: {lua[0]}")
    print()
    print("| bench | jello median (ms) | lua median (ms) | Lua/Jello |")
    print("|---|---:|---:|---:|")
    for r in rows:
        jmed = float(r["jmed"])
        if jmed != jmed:  # NaN
            print(f"| {r['name']} | (unsupported) | {fmt_ms(r['lmed'])} |  |")
            continue
        print(
            f"| {r['name']} | {fmt_ms(r['jmed'])} | {fmt_ms(r['lmed'])} | {r['speedup']:.2f}x |"
        )

    # Totals (median-of-medians-ish): use sum of medians as a rough overall indicator.
    jtot = sum(float(r["jmed"]) for r in rows if float(r["jmed"]) == float(r["jmed"]))
    ltot = sum(float(r["lmed"]) for r in rows)
    if rows:
        ratio = (ltot / jtot) if jtot > 0 else float("nan")
        print("| **TOTAL (sum of medians)** | "
              f"**{fmt_ms(jtot)}** | **{fmt_ms(ltot)}** | **{ratio:.2f}x** |")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

