"""IoT Gateway Service: validates, normalizes, and publishes sensor events to Kafka."""
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.settings import load_settings
from shared.logger import get_logger
from shared.models import VehicleEvent
from shared.locations import BOLIVIA_LOCATIONS, VIDEO_FEED_URLS
from shared.observability import MetricsCollector, PrometheusMiddleware, add_metrics_endpoint

settings = load_settings()
logger = get_logger("iot-gateway", settings.log_level)

producer = None
collector = MetricsCollector("iot-gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage Kafka producer lifecycle."""
    global producer
    kafka_enabled = os.getenv("KAFKA_ENABLED", "false").lower() == "true"
    if kafka_enabled:
        try:
            from confluent_kafka import Producer
            producer = Producer({"bootstrap.servers": settings.kafka.bootstrap_servers})
            logger.info("Kafka producer initialized", extra={"extra_fields": {"broker": settings.kafka.bootstrap_servers}})
        except Exception as e:
            logger.warning(f"Kafka unavailable, running in mock mode: {e}")
            producer = None
    else:
        logger.info("Kafka disabled, running in mock mode")
        producer = None
    yield
    if producer:
        producer.flush()
        logger.info("Kafka producer flushed and closed")


app = FastAPI(
    title="TMS IoT Gateway Service",
    description="National Traffic Monitoring System Bolivia - Event ingestion gateway.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(PrometheusMiddleware, collector=collector)
add_metrics_endpoint(app, collector)


def publish_event(topic: str, key: str, value: dict) -> bool:
    payload = json.dumps(value)
    if producer:
        producer.produce(topic, key=key, value=payload)
        producer.poll(0)
        return True
    logger.info(f"[MOCK KAFKA] topic={topic} key={key} payload_size={len(payload)}")
    return False


def build_response(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        "data": data,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat(), "version": "v1", "request_id": str(uuid.uuid4())},
    })


@app.get("/health")
async def health_check():
    kafka_status = "connected" if producer else "mock_mode"
    return build_response({
        "service": "iot-gateway",
        "status": "healthy",
        "kafka": kafka_status,
        "environment": settings.app_env,
        "locations_configured": len(BOLIVIA_LOCATIONS),
        "video_feeds": len(VIDEO_FEED_URLS),
    })


@app.post("/api/v1/events/vehicle")
async def ingest_vehicle_event(request: Request):
    body = await request.json()
    required = ["location_id", "plate", "speed_kmh"]
    missing = [f for f in required if f not in body]
    if missing:
        return build_response({"error": f"Missing fields: {missing}"}, status=400)

    event = VehicleEvent(
        location_id=body["location_id"],
        plate=body["plate"],
        speed_kmh=float(body["speed_kmh"]),
        direction=body.get("direction", "N"),
        is_infraction=body.get("is_infraction", False),
        traffic_state=body.get("traffic_state", "free_flow"),
    )
    publish_event(topic=settings.kafka.topic_vehicle_detected, key=event.location_id, value=event.to_dict())
    logger.info("Vehicle event ingested", extra={"extra_fields": {"location": event.location_id, "plate": event.plate, "speed": event.speed_kmh}})
    return build_response({"event_id": event.id, "published": True}, status=201)


@app.post("/api/v1/events/batch")
async def ingest_batch_events(request: Request):
    body = await request.json()
    events = body.get("events", [])
    if not events:
        return build_response({"error": "Empty events list"}, status=400)

    published = 0
    for evt_data in events:
        event = VehicleEvent(
            location_id=evt_data.get("location_id", "unknown"),
            plate=evt_data.get("plate", "UNKNOWN"),
            speed_kmh=float(evt_data.get("speed_kmh", 0)),
            direction=evt_data.get("direction", "N"),
            is_infraction=evt_data.get("is_infraction", False),
            traffic_state=evt_data.get("traffic_state", "free_flow"),
            timestamp=evt_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
        publish_event(topic=settings.kafka.topic_vehicle_detected, key=event.location_id, value=event.to_dict())
        published += 1

    logger.info(f"Batch ingested: {published} events")
    return build_response({"published": published, "total": len(events)}, status=201)


@app.get("/api/v1/config/locations")
async def list_locations():
    return build_response({"locations": BOLIVIA_LOCATIONS, "count": len(BOLIVIA_LOCATIONS)})


@app.get("/api/v1/config/video-feeds")
async def list_video_feeds():
    return build_response({"feeds": VIDEO_FEED_URLS, "count": len(VIDEO_FEED_URLS)})
