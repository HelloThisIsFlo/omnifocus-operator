"""Shared benchmark harness — timing, scale sweep, result formatting."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Timing:
    label: str
    samples_ms: list[float] = field(default_factory=list)
    result_count: int | None = None

    @property
    def min(self) -> float:
        return min(self.samples_ms)

    @property
    def median(self) -> float:
        return statistics.median(self.samples_ms)

    @property
    def mean(self) -> float:
        return statistics.fmean(self.samples_ms)

    @property
    def p95(self) -> float:
        if len(self.samples_ms) < 20:
            return max(self.samples_ms)
        sorted_samples = sorted(self.samples_ms)
        idx = int(0.95 * len(sorted_samples))
        return sorted_samples[idx]


def bench(
    label: str,
    fn: Callable[[], object],
    *,
    warmups: int = 2,
    iters: int = 10,
) -> Timing:
    """Run fn and record wall-clock timings in ms."""
    for _ in range(warmups):
        fn()
    t = Timing(label=label)
    for _ in range(iters):
        start = time.perf_counter()
        result = fn()
        elapsed_ms = (time.perf_counter() - start) * 1000
        t.samples_ms.append(elapsed_ms)
        if t.result_count is None:
            try:
                t.result_count = len(result)  # type: ignore[arg-type]
            except TypeError:
                t.result_count = -1
    return t


def print_timing_table(rows: list[tuple[str, Timing]]) -> None:
    """Print a compact comparison table."""
    print()
    print(f"{'scenario':<40}  {'result':>8}  {'min':>7}  {'median':>7}  {'mean':>7}  {'p95':>7}")
    print("-" * 88)
    for scale_label, t in rows:
        print(
            f"{scale_label:<40}  {t.result_count!s:>8}  "
            f"{t.min:>6.2f}  {t.median:>6.2f}  {t.mean:>6.2f}  {t.p95:>6.2f}  (ms)"
        )


def print_header(title: str) -> None:
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)
