"""Vehicles & Infractions Service: manages infraction records and vehicle history."""
import os
import sys
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.settings import load_settings
from shared.logger import get_logger
from shared.generators import generate_events_for_interval
from shared.models import Infraction, TrafficState
from shared.locations import BOLIVIA_LOCATIONS
from shared.observability import MetricsCollector, PrometheusMiddleware, add_metrics_endpoint

settings = load_settings()
logger = get_logger("vehicles-service", settings.log_level)
collector = MetricsCollector("vehicles-service")

infractions_db: list[dict] = []
vehicles_db: dict[str, list[dict]] = {}


def seed_mock_infractions():
    base = datetime(2026, 4, 21, 8, 0, 0, tzinfo=timezone.utc)
    for loc in BOLIVIA_LOCATIONS:
        events = generate_events_for_interval(
            location_id=loc["id"],
            speed_limit=loc["speed_limit"],
            traffic_state=TrafficState.FREE_FLOW,
            base_time=base,
            interval_seconds=3600,
            lambda_override=loc["lambda_rate"],
            speed_mu_override=loc["speed_mu"],
            speed_sigma_override=loc["speed_sigma"],
        )
        for evt in events:
            if evt.plate not in vehicles_db:
                vehicles_db[evt.plate] = []
            vehicles_db[evt.plate].append(evt.to_dict())
            if evt.is_infraction:
                infraction = Infraction(
                    location_id=evt.location_id,
                    vehicle_plate=evt.plate,
                    speed_kmh=evt.speed_kmh,
                    speed_limit=loc["speed_limit"],
                    triggered_at=evt.timestamp,
                    vehicle_event_id=evt.id,
                )
                infractions_db.append(infraction.to_dict())
    logger.info(f"Seeded {len(infractions_db)} infractions, {len(vehicles_db)} plates across Bolivia")


app = FastAPI(title="TMS Vehicles & Infractions", version="1.0.0")


@app.on_event("startup")
async def startup():
    seed_mock_infractions()

app.add_middleware(PrometheusMiddleware, collector=collector)
add_metrics_endpoint(app, collector)


def build_response(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        "data": data,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "v1"},
    })


@app.get("/health")
async def health_check():
    return build_response({
        "service": "vehicles-infractions",
        "status": "healthy",
        "infractions_count": len(infractions_db),
        "unique_plates": len(vehicles_db),
    })


@app.get("/api/v1/infractions")
async def list_infractions(location_id: str = Query(None), limit: int = Query(50)):
    results = infractions_db
    if location_id:
        results = [i for i in results if i["location_id"] == location_id]
    return build_response({"infractions": results[-limit:], "total": len(results)})


@app.get("/api/v1/infractions/{infraction_id}")
async def get_infraction(infraction_id: str):
    for inf in infractions_db:
        if inf["id"] == infraction_id:
            return build_response({"infraction": inf})
    return build_response({"error": "Infraction not found"}, status=404)


@app.get("/api/v1/vehicles/{plate}/trajectory")
async def get_trajectory(plate: str):
    events = vehicles_db.get(plate, [])
    return build_response({"plate": plate, "trajectory": events, "total_events": len(events)})


@app.get("/api/v1/vehicles/{plate}/infractions")
async def get_vehicle_infractions(plate: str):
    results = [i for i in infractions_db if i["vehicle_plate"] == plate]
    return build_response({"plate": plate, "infractions": results, "total": len(results)})
