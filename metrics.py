"""
observability/metrics.py

Lightweight in-process metrics — request counts, latency histograms, error rates.
In production: Prometheus client with /metrics endpoint.
"""

from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Metrics:
    request_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_count:   Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latencies:     Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    def record_request(self, endpoint: str, latency_ms: float, status_code: int):
        self.request_count[endpoint] += 1
        self.latencies[endpoint].append(latency_ms)
        if status_code >= 400:
            self.error_count[endpoint] += 1

    def p95(self, endpoint: str) -> float:
        lats = sorted(self.latencies.get(endpoint, [0.0]))
        idx = int(len(lats) * 0.95)
        return lats[min(idx, len(lats) - 1)]

    def summary(self) -> dict:
        return {
            ep: {
                "requests": self.request_count[ep],
                "errors":   self.error_count[ep],
                "p95_ms":   round(self.p95(ep), 2),
            }
            for ep in self.request_count
        }


_metrics = Metrics()

def get_metrics() -> Metrics:
    return _metrics
