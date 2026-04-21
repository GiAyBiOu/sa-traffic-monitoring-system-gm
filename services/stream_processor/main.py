"""Stream Processor Service: consumes events, detects infractions, computes metrics."""
import json
import os
import sys
import threading
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.settings import load_settings
from shared.logger import get_logger
from shared.models import VehicleEvent, TrafficMetric, Infraction
from shared.locations import BOLIVIA_LOCATIONS
from shared.observability import MetricsCollector, PrometheusMiddleware, add_metrics_endpoint

settings = load_settings()
logger = get_logger("stream-processor", settings.log_level)

SPEED_LIMITS = {loc["id"]: loc["speed_limit"] for loc in BOLIVIA_LOCATIONS}

metrics_buffer: dict[str, list[VehicleEvent]] = defaultdict(list)
infractions_store: list[Infraction] = []
metrics_store: list[TrafficMetric] = []
events_processed = 0
consumer_thread = None
running = False
collector = MetricsCollector("stream-processor")


def process_vehicle_event(event_data: dict) -> None:
    global events_processed
    valid_fields = {k for k in VehicleEvent.__dataclass_fields__}
    filtered = {k: event_data[k] for k in event_data if k in valid_fields}
    event = VehicleEvent(**filtered)
    metrics_buffer[event.location_id].append(event)
    events_processed += 1

    speed_limit = SPEED_LIMITS.get(event.location_id, settings.simulation.speed_limit)
    if event.speed_kmh > speed_limit:
        infraction = Infraction(
            location_id=event.location_id,
            vehicle_plate=event.plate,
            speed_kmh=event.speed_kmh,
            speed_limit=speed_limit,
            triggered_at=event.timestamp,
            vehicle_event_id=event.id,
        )
        infractions_store.append(infraction)
        logger.info(f"Infraction: {event.plate} at {event.speed_kmh} km/h (limit {speed_limit})")


def compute_metrics(location_id: str, events: list[VehicleEvent]) -> TrafficMetric:
    speeds = [e.speed_kmh for e in events]
    return TrafficMetric(
        location_id=location_id,
        total_vehicles=len(events),
        avg_speed_kmh=sum(speeds) / len(speeds) if speeds else 0,
        max_speed_kmh=max(speeds) if speeds else 0,
        min_speed_kmh=min(speeds) if speeds else 0,
        infraction_count=sum(1 for e in events if e.speed_kmh > SPEED_LIMITS.get(location_id, 110)),
    )


def flush_metrics() -> list[TrafficMetric]:
    computed = []
    for loc_id in list(metrics_buffer.keys()):
        events = metrics_buffer.pop(loc_id, [])
        if events:
            metric = compute_metrics(loc_id, events)
            metrics_store.append(metric)
            computed.append(metric)
    return computed


def kafka_consumer_loop():
    global running
    try:
        from confluent_kafka import Consumer
        consumer = Consumer({
            "bootstrap.servers": settings.kafka.bootstrap_servers,
            "group.id": "smt-stream-processors",
            "auto.offset.reset": "earliest",
        })
        consumer.subscribe([settings.kafka.topic_vehicle_detected])
        logger.info("Kafka consumer started")
        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.warning(f"Kafka consumer error: {msg.error()}")
                continue
            event_data = json.loads(msg.value().decode("utf-8"))
            process_vehicle_event(event_data)
        consumer.close()
    except Exception as e:
        logger.warning(f"Kafka consumer unavailable: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_thread, running
    kafka_enabled = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
    if kafka_enabled:
        running = True
        consumer_thread = threading.Thread(target=kafka_consumer_loop, daemon=True)
        consumer_thread.start()
    else:
        logger.info("Kafka disabled, standalone mode")
    yield
    running = False
    if consumer_thread:
        consumer_thread.join(timeout=5)


app = FastAPI(title="TMS Stream Processor", version="1.0.0", lifespan=lifespan)
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
        "service": "stream-processor",
        "status": "healthy",
        "events_processed": events_processed,
        "buffered_locations": len(metrics_buffer),
        "total_infractions": len(infractions_store),
        "total_metrics_computed": len(metrics_store),
    })


@app.post("/api/v1/process")
async def process_event_directly(event: dict):
    process_vehicle_event(event)
    return build_response({"processed": True})


@app.post("/api/v1/metrics/flush")
async def flush_metrics_endpoint():
    computed = flush_metrics()
    return build_response({"computed": len(computed), "metrics": [m.to_dict() for m in computed]})


@app.get("/api/v1/infractions")
async def list_infractions():
    return build_response({"infractions": [i.to_dict() for i in infractions_store[-100:]], "total": len(infractions_store)})


@app.get("/api/v1/metrics")
async def list_metrics():
    return build_response({"metrics": [m.to_dict() for m in metrics_store[-100:]], "total": len(metrics_store)})
