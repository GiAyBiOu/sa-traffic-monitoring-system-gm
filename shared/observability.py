"""Prometheus-compatible metrics collection middleware for FastAPI services."""
import time
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse


class MetricsCollector:
    """In-process metrics collector exposing Prometheus text format."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.request_count = defaultdict(int)
        self.request_latency_sum = defaultdict(float)
        self.request_latency_count = defaultdict(int)
        self.error_count = defaultdict(int)
        self.start_time = time.time()

    def record_request(self, method: str, path: str, status: int, duration: float):
        key = f'{method}_{path}_{status}'
        self.request_count[key] += 1
        self.request_latency_sum[key] += duration
        self.request_latency_count[key] += 1
        if status >= 400:
            self.error_count[key] += 1

    def render_prometheus(self) -> str:
        lines = []
        lines.append(f"# HELP smt_uptime_seconds Time since service started")
        lines.append(f"# TYPE smt_uptime_seconds gauge")
        lines.append(f'smt_uptime_seconds{{service="{self.service_name}"}} {time.time() - self.start_time:.1f}')
        lines.append("")
        lines.append("# HELP smt_http_requests_total Total HTTP requests")
        lines.append("# TYPE smt_http_requests_total counter")
        for key, count in self.request_count.items():
            method, path, status = key.rsplit("_", 2)
            lines.append(f'smt_http_requests_total{{service="{self.service_name}",method="{method}",path="{path}",status="{status}"}} {count}')
        lines.append("")
        lines.append("# HELP smt_http_request_duration_seconds Total request duration")
        lines.append("# TYPE smt_http_request_duration_seconds counter")
        for key, total in self.request_latency_sum.items():
            method, path, status = key.rsplit("_", 2)
            count = self.request_latency_count[key]
            avg = total / count if count else 0
            lines.append(f'smt_http_request_duration_seconds{{service="{self.service_name}",method="{method}",path="{path}",quantile="avg"}} {avg:.4f}')
        lines.append("")
        lines.append("# HELP smt_http_errors_total Total HTTP errors")
        lines.append("# TYPE smt_http_errors_total counter")
        for key, count in self.error_count.items():
            method, path, status = key.rsplit("_", 2)
            lines.append(f'smt_http_errors_total{{service="{self.service_name}",method="{method}",path="{path}",status="{status}"}} {count}')
        return "\n".join(lines) + "\n"


class PrometheusMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that records request metrics."""

    def __init__(self, app, collector: MetricsCollector):
        super().__init__(app)
        self.collector = collector

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        path = request.url.path.split("?")[0]
        if path != "/metrics":
            self.collector.record_request(request.method, path, response.status_code, duration)
        return response


def add_metrics_endpoint(app, collector: MetricsCollector):
    """Register /metrics endpoint on a FastAPI app."""
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        return PlainTextResponse(collector.render_prometheus(), media_type="text/plain; charset=utf-8")
