"""Vast.ai PyWorker for the KataGo HTTP wrapper (katago_http_wrapper.py)."""
from vastai import Worker, WorkerConfig, HandlerConfig, BenchmarkConfig, LogActionConfig


def _workload(payload: dict) -> float:
    visits = float(payload.get("maxVisits") or 30)
    turns = len(payload.get("analyzeTurns") or [1])
    return visits * turns


def _bench_payload() -> dict:
    return {
        "boardXSize": 19, "boardYSize": 19, "rules": "japanese", "komi": 6.5,
        "maxVisits": 100,
        "moves": [["B", "Q16"], ["W", "D4"], ["B", "Q4"], ["W", "D16"]],
        "analyzeTurns": [4],
    }


worker_config = WorkerConfig(
    model_server_url="http://127.0.0.1",
    model_server_port=18000,
    model_log_file="/var/log/portal/katago.log",
    handlers=[
        HandlerConfig(
            route="/analyze",
            allow_parallel_requests=True,   # katago analysis engine batches concurrent queries
            max_queue_time=60.0,
            workload_calculator=_workload,
            benchmark_config=BenchmarkConfig(generator=_bench_payload, runs=4, concurrency=2),
        ),
    ],
    log_action_config=LogActionConfig(
        on_load=["KATAGO_HTTP_READY"],
        on_error=["Traceback (most recent call last):", "Could not open", "CUDA error"],
        on_info=["Loaded model"],
    ),
)

Worker(worker_config).run()
