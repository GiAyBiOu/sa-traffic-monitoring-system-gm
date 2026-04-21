"""Load test script for TMS services — simulates concurrent traffic."""
import sys
import os
import time
import requests
import concurrent.futures
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.generators import generate_events_for_interval
from shared.models import TrafficState
from shared.locations import BOLIVIA_LOCATIONS

GATEWAY_URL = os.getenv("IOT_GATEWAY_URL", "http://localhost:8001")
METRICS_URL = os.getenv("METRICS_SERVICE_URL", "http://localhost:8003")
VEHICLES_URL = os.getenv("VEHICLES_SERVICE_URL", "http://localhost:8004")
CONCURRENCY = int(os.getenv("LOAD_TEST_CONCURRENCY", "4"))
CYCLES = int(os.getenv("LOAD_TEST_CYCLES", "5"))


def send_batch(loc: dict, cycle: int) -> dict:
    events = generate_events_for_interval(
        location_id=loc["id"], speed_limit=loc["speed_limit"],
        traffic_state=TrafficState.FREE_FLOW, base_time=datetime.now(timezone.utc),
        interval_seconds=300, lambda_override=loc["lambda_rate"],
        speed_mu_override=loc["speed_mu"], speed_sigma_override=loc["speed_sigma"],
    )
    batch = [e.to_dict() for e in events]
    start = time.time()
    try:
        r = requests.post(f"{GATEWAY_URL}/api/v1/events/batch", json={"events": batch}, timeout=30)
        return {"location": loc["name"], "events": len(batch), "status": r.status_code, "latency_ms": round((time.time() - start) * 1000)}
    except Exception as e:
        return {"location": loc["name"], "events": len(batch), "status": "error", "latency_ms": round((time.time() - start) * 1000), "error": str(e)}


def run_load_test():
    print(f"\n{'='*60}")
    print(f"TMS LOAD TEST — {CONCURRENCY} concurrent workers, {CYCLES} cycles")
    print(f"Target: {GATEWAY_URL}")
    print(f"Locations: {len(BOLIVIA_LOCATIONS)} across Bolivia")
    print(f"{'='*60}\n")

    all_results = []
    total_start = time.time()

    for cycle in range(1, CYCLES + 1):
        print(f"--- Cycle {cycle}/{CYCLES} ---")
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
            futures = [executor.submit(send_batch, loc, cycle) for loc in BOLIVIA_LOCATIONS]
            for f in concurrent.futures.as_completed(futures):
                result = f.result()
                all_results.append(result)
                print(f"  {result['location']}: {result['events']} events, {result['status']}, {result['latency_ms']}ms")

    total_time = time.time() - total_start
    total_events = sum(r["events"] for r in all_results)
    avg_latency = sum(r["latency_ms"] for r in all_results) / len(all_results)
    errors = sum(1 for r in all_results if r["status"] != 201)

    print(f"\n{'='*60}")
    print(f"RESULTS:")
    print(f"  Total events sent:    {total_events:,}")
    print(f"  Total time:           {total_time:.1f}s")
    print(f"  Throughput:           {total_events/total_time:.0f} events/sec")
    print(f"  Avg latency:          {avg_latency:.0f}ms")
    print(f"  Errors:               {errors}/{len(all_results)}")
    print(f"{'='*60}\n")

    print("Checking service metrics endpoints...")
    for name, url in [("Gateway", GATEWAY_URL), ("Metrics", METRICS_URL), ("Vehicles", VEHICLES_URL)]:
        try:
            r = requests.get(f"{url}/metrics", timeout=5)
            print(f"  {name} /metrics: {r.status_code} ({len(r.text)} bytes)")
        except Exception:
            print(f"  {name} /metrics: unreachable")


if __name__ == "__main__":
    run_load_test()
