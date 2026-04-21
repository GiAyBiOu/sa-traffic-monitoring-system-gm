"""Metrics & Analytics Service: read-optimized API for aggregated traffic data."""
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.settings import load_settings
from shared.logger import get_logger
from shared.generators import generate_events_for_hour, generate_weather
from shared.models import TrafficMetric, TrafficState
from shared.locations import BOLIVIA_LOCATIONS
from shared.observability import MetricsCollector, PrometheusMiddleware, add_metrics_endpoint

settings = load_settings()
logger = get_logger("metrics-service", settings.log_level)
collector = MetricsCollector("metrics-service")

metrics_cache: list[dict] = []


def seed_mock_metrics():
    base = datetime(2026, 4, 21, 6, 0, 0, tzinfo=timezone.utc)
    for loc in BOLIVIA_LOCATIONS:
        for hour_offset in range(18):
            hour_time = base.replace(hour=6 + hour_offset)
            events = generate_events_for_hour(
                location_id=loc["id"],
                speed_limit=loc["speed_limit"],
                traffic_state=TrafficState.FREE_FLOW,
                base_time=hour_time,
                lambda_rate=loc["lambda_rate"],
                speed_mu=loc["speed_mu"],
                speed_sigma=loc["speed_sigma"],
            )
            if not events:
                continue
            speeds = [e.speed_kmh for e in events]
            metric = TrafficMetric(
                location_id=loc["id"],
                timestamp=hour_time.isoformat(),
                period_minutes=60,
                total_vehicles=len(events),
                avg_speed_kmh=sum(speeds) / len(speeds),
                max_speed_kmh=max(speeds),
                min_speed_kmh=max(0, min(speeds)),
                infraction_count=sum(1 for e in events if e.is_infraction),
                weather_condition=generate_weather(),
            )
            entry = metric.to_dict()
            entry["location_name"] = loc["name"]
            entry["city"] = loc["city"]
            metrics_cache.append(entry)
    logger.info(f"Seeded {len(metrics_cache)} metric records for {len(BOLIVIA_LOCATIONS)} Bolivian locations")


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_mock_metrics()
    yield


app = FastAPI(title="TMS Metrics & Analytics", version="1.0.0", lifespan=lifespan)
app.add_middleware(PrometheusMiddleware, collector=collector)
add_metrics_endpoint(app, collector)


def build_response(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        "data": data,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "v1"},
    })


@app.get("/health")
async def health_check():
    return build_response({"service": "metrics-analytics", "status": "healthy", "cached_records": len(metrics_cache)})


@app.get("/api/v1/metrics")
async def get_metrics(location_id: str = Query(None), city: str = Query(None), limit: int = Query(50)):
    results = metrics_cache
    if location_id:
        results = [m for m in results if m["location_id"] == location_id]
    if city:
        results = [m for m in results if m.get("city", "").lower() == city.lower()]
    return build_response({"metrics": results[-limit:], "total": len(results)})


@app.get("/api/v1/metrics/{location_id}")
async def get_location_metrics(location_id: str):
    results = [m for m in metrics_cache if m["location_id"] == location_id]
    return build_response({"location_id": location_id, "metrics": results, "total": len(results)})


@app.get("/api/v1/metrics/summary")
async def get_summary():
    if not metrics_cache:
        return build_response({"summary": {}})
    total_vehicles = sum(m["total_vehicles"] for m in metrics_cache)
    total_infractions = sum(m["infraction_count"] for m in metrics_cache)
    all_speeds = [m["avg_speed_kmh"] for m in metrics_cache if m["avg_speed_kmh"] > 0]
    locations = list(set(m["location_id"] for m in metrics_cache))
    cities = list(set(m.get("city", "Unknown") for m in metrics_cache))
    return build_response({
        "summary": {
            "total_vehicles_observed": total_vehicles,
            "total_infractions": total_infractions,
            "average_speed_kmh": round(sum(all_speeds) / len(all_speeds), 1) if all_speeds else 0,
            "active_locations": len(locations),
            "cities_covered": cities,
            "data_points": len(metrics_cache),
        }
    })


@app.get("/api/v1/locations")
async def get_locations():
    return build_response({"locations": BOLIVIA_LOCATIONS})
