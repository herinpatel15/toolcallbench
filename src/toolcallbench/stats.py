"""Small statistics helpers for pass rates."""
from __future__ import annotations

import math


def wilson_interval(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Approximate 95% range for a pass rate (Wilson score interval), as fractions between 0 and 1.

    It treats every run as an independent trial, which is only roughly true (the same 20 tasks are
    used for every model), so read it as a guide to how much a number can move, not as a guarantee.
    """
    if total <= 0:
        return (0.0, 1.0)
    p = passed / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def ranges_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def format_range(passed: int, total: int) -> str:
    if total <= 0:
        return "-"
    low, high = wilson_interval(passed, total)
    return f"{100 * low:.0f}-{100 * high:.0f}%"
