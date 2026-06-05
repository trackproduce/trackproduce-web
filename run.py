"""Entry point: Flask app plus Prometheus metrics."""
from __future__ import annotations

import os

import psutil
from prometheus_client import Gauge
from prometheus_flask_exporter import PrometheusMetrics

from app import app

metrics: PrometheusMetrics = PrometheusMetrics(app)
metrics.info("app_info", "Application info", version="1.0.0")

_process: psutil.Process = psutil.Process(os.getpid())

memory_gauge: Gauge = Gauge(
    "app_process_memory_bytes", "Resident memory of the app process in bytes"
)
cpu_gauge: Gauge = Gauge(
    "app_process_cpu_percent", "CPU usage percent of the app process"
)


@memory_gauge.set_function
def _collect_memory() -> float:
    return float(_process.memory_info().rss)


@cpu_gauge.set_function
def _collect_cpu() -> float:
    return float(_process.cpu_percent())


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") not in ("0", "false", "False", "")
    app.run(host="0.0.0.0", port=7015, debug=debug)
