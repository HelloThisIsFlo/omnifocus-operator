"""OmniFocus Bridge Benchmark Runner.

Runs variant scripts with progressively more fields to isolate
where the ~3s handleSnapshot() bottleneck lives.

Usage: uv run python .research/benchmark/run.py [--runs 5] [--warmup 2]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.parse
import uuid
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent
COMMON_JS = BENCHMARK_DIR / "_common.js"
VARIANTS_DIR = BENCHMARK_DIR / "variants"

IPC_DIR = (
    Path.home()
    / "Library"
    / "Containers"
    / "com.omnigroup.OmniFocus4"
    / "Data"
    / "Documents"
    / "omnifocus-operator"
    / "ipc"
)


def run_variant(script: str, timeout: float = 30.0) -> dict:
    """Send a single benchmark request to OmniFocus and return the response."""
    IPC_DIR.mkdir(parents=True, exist_ok=True)
    pid = os.getpid()
    request_id = uuid.uuid4()
    file_prefix = f"{pid}_{request_id}"

    # Write request
    request_path = IPC_DIR / f"{file_prefix}.request.json"
    request_path.write_text(json.dumps({"operation": "snapshot", "params": {}}))

    # Trigger OmniFocus
    encoded_script = urllib.parse.quote(script, safe="")
    encoded_arg = urllib.parse.quote(json.dumps(file_prefix), safe="")
    url = f"omnifocus:///omnijs-run?script={encoded_script}&arg={encoded_arg}"

    wall_start = time.monotonic()
    subprocess.run(["open", "-g", url], check=True, capture_output=True)

    # Poll for response
    response_path = IPC_DIR / f"{file_prefix}.response.json"
    while time.monotonic() - wall_start < timeout:
        if response_path.exists():
            wall_ms = (time.monotonic() - wall_start) * 1000
            response_text = response_path.read_text()
            size_kb = len(response_text.encode()) / 1024
            raw = json.loads(response_text)
            # Cleanup
            request_path.unlink(missing_ok=True)
            response_path.unlink(missing_ok=True)
            if not raw.get("success"):
                raise RuntimeError(f"OmniFocus error: {raw.get('error')}")
            data = raw["data"]
            return {
                "internal_ms": data.get("_benchmarkMs", -1),
                "wall_ms": wall_ms,
                "size_kb": size_kb,
            }
        time.sleep(0.05)

    # Timeout — cleanup
    request_path.unlink(missing_ok=True)
    response_path.unlink(missing_ok=True)
    raise TimeoutError(f"No response after {timeout}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniFocus Bridge Benchmark")
    parser.add_argument("--runs", type=int, default=3, help="Measured runs per variant")
    parser.add_argument("--warmup", type=int, default=1, help="Warmup runs (discarded)")
    args = parser.parse_args()

    common_js = COMMON_JS.read_text()
    variant_files = sorted(VARIANTS_DIR.glob("*.js"))

    if not variant_files:
        print("No variant files found in", VARIANTS_DIR)
        return

    total_runs = args.warmup + args.runs
    print(f"OmniFocus Bridge Benchmark ({args.runs} runs, {args.warmup} warmup)")
    print("=" * 75)
    print()
    print(f"{'Variant':<20} | {'Internal (ms)':<22} | {'Wall Clock (ms)':<22} | {'Size (KB)'}")
    print(f"{'':<20} | {'min / avg / max':<22} | {'min / avg / max':<22} |")
    print("-" * 20 + "-+-" + "-" * 22 + "-+-" + "-" * 22 + "-+-" + "-" * 9)

    for vf in variant_files:
        variant_name = vf.stem
        script = vf.read_text() + "\n" + common_js
        internals = []
        walls = []
        size_kb = 0

        for i in range(total_runs):
            label = "warmup" if i < args.warmup else f"run {i - args.warmup + 1}"
            print(f"  {variant_name}: {label}...", end="", flush=True)
            try:
                result = run_variant(script)
                print(f" {result['internal_ms']}ms (wall: {result['wall_ms']:.0f}ms)")
                if i >= args.warmup:
                    internals.append(result["internal_ms"])
                    walls.append(result["wall_ms"])
                    size_kb = result["size_kb"]
            except Exception as e:
                print(f" ERROR: {e}")
                if i >= args.warmup:
                    internals.append(-1)
                    walls.append(-1)

        if internals and all(v >= 0 for v in internals):
            i_min, i_avg, i_max = min(internals), sum(internals) / len(internals), max(internals)
            w_min, w_avg, w_max = min(walls), sum(walls) / len(walls), max(walls)
            print(
                f"{variant_name:<20} | {i_min:>4.0f} / {i_avg:>5.0f} / {i_max:<5.0f} "
                f"| {w_min:>4.0f} / {w_avg:>5.0f} / {w_max:<5.0f} "
                f"| {size_kb:>7.1f}"
            )
        else:
            print(f"{variant_name:<20} |        ERROR          |        ERROR          |   ERROR")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
