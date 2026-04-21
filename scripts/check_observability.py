"""Observability checker: health + Prometheus metrics for all TMS services."""
import sys
import os
import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SERVICES = {
    "iot-gateway"      : os.getenv("IOT_GATEWAY_URL",     "http://localhost:8001"),
    "stream-processor" : os.getenv("STREAM_PROCESSOR_URL","http://localhost:8002"),
    "metrics-service"  : os.getenv("METRICS_SERVICE_URL", "http://localhost:8003"),
    "vehicles-service" : os.getenv("VEHICLES_SERVICE_URL","http://localhost:8004"),
}


def check_health(base: str) -> dict:
    try:
        r = requests.get(f"{base}/health", timeout=5)
        data = r.json().get("data", {})
        return {"status": data.get("status", "unknown"), "http": r.status_code, "detail": data}
    except Exception as e:
        return {"status": "offline", "http": 0, "detail": str(e)}


def scrape_metrics(base: str) -> str:
    try:
        r = requests.get(f"{base}/metrics", timeout=5)
        lines = [l for l in r.text.splitlines() if not l.startswith("#") and l.strip()]
        return f"   /metrics: {len(lines)} series"
    except Exception:
        return "   /metrics: unreachable"


if __name__ == "__main__":
    print("\n=== TMS Observability Report ===\n")
    all_healthy = True
    for name, url in SERVICES.items():
        result = check_health(url)
        tag = "[OK  ]" if result["status"] == "healthy" else "[FAIL]"
        print(f"{tag} {name}")
        print(f"   status : {result['status']} (HTTP {result['http']})")
        if isinstance(result["detail"], dict):
            for k, v in result["detail"].items():
                if k != "status":
                    print(f"   {k:<32}: {v}")
        print(scrape_metrics(url))
        print()
        if result["status"] != "healthy":
            all_healthy = False

    print("=" * 40)
    print(f"Result: {'ALL HEALTHY' if all_healthy else 'DEGRADED - check docker compose logs'}")
    sys.exit(0 if all_healthy else 1)
