from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid


class TrafficState(str, Enum):
    FREE_FLOW = "free_flow"
    CONGESTION = "congestion"
    INCIDENT = "incident"


class WeatherCondition(str, Enum):
    CLEAR = "CLEAR"
    RAIN = "RAIN"
    SNOW = "SNOW"
    FOG = "FOG"
    STORM = "STORM"


class InfractionStatus(str, Enum):
    OPEN = "OPEN"
    NOTIFIED = "NOTIFIED"
    RESOLVED = "RESOLVED"


@dataclass
class VehicleEvent:
    """Represents a single vehicle detection event."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    location_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    plate: str = ""
    speed_kmh: float = 0.0
    direction: str = "N"
    is_infraction: bool = False
    photo_ref: Optional[str] = None
    traffic_state: str = TrafficState.FREE_FLOW.value

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "location_id": self.location_id,
            "timestamp": self.timestamp,
            "plate": self.plate,
            "speed_kmh": self.speed_kmh,
            "direction": self.direction,
            "is_infraction": self.is_infraction,
            "photo_ref": self.photo_ref,
            "traffic_state": self.traffic_state,
        }


@dataclass
class TrafficMetric:
    """Aggregated traffic data for a time window."""
    location_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    period_minutes: int = 5
    total_vehicles: int = 0
    avg_speed_kmh: float = 0.0
    max_speed_kmh: float = 0.0
    min_speed_kmh: float = 0.0
    infraction_count: int = 0
    weather_condition: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "location_id": self.location_id,
            "timestamp": self.timestamp,
            "period_minutes": self.period_minutes,
            "total_vehicles": self.total_vehicles,
            "avg_speed_kmh": round(self.avg_speed_kmh, 1),
            "max_speed_kmh": round(self.max_speed_kmh, 1),
            "min_speed_kmh": round(self.min_speed_kmh, 1),
            "infraction_count": self.infraction_count,
            "weather_condition": self.weather_condition,
        }


@dataclass
class Infraction:
    """A speed violation record."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    location_id: str = ""
    vehicle_plate: str = ""
    speed_kmh: float = 0.0
    speed_limit: float = 0.0
    triggered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = InfractionStatus.OPEN.value
    vehicle_event_id: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "location_id": self.location_id,
            "vehicle_plate": self.vehicle_plate,
            "speed_kmh": round(self.speed_kmh, 1),
            "speed_limit": round(self.speed_limit, 1),
            "triggered_at": self.triggered_at,
            "status": self.status,
            "vehicle_event_id": self.vehicle_event_id,
        }
