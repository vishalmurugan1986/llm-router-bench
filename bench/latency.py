"""Simple percentile helpers -- no numpy dependency needed for this scale of data."""

from __future__ import annotations

import math


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


def p50(values: list[float]) -> float:
    return percentile(values, 0.50)


def p95(values: list[float]) -> float:
    return percentile(values, 0.95)
