"""Traffic data generator using Poisson, Gaussian, Weibull, and Markov distributions."""
import random
from datetime import datetime, timezone, timedelta

import numpy as np
from scipy.stats import norm, poisson, weibull_min

from shared.models import VehicleEvent, TrafficState, WeatherCondition


MARKOV_TRANSITIONS = {
    TrafficState.FREE_FLOW: [0.85, 0.13, 0.02],
    TrafficState.CONGESTION: [0.30, 0.60, 0.10],
    TrafficState.INCIDENT: [0.10, 0.40, 0.50],
}

STATE_PARAMS = {
    TrafficState.FREE_FLOW: {"lambda": 800, "speed_mu": 90, "speed_sigma": 12},
    TrafficState.CONGESTION: {"lambda": 1200, "speed_mu": 35, "speed_sigma": 8},
    TrafficState.INCIDENT: {"lambda": 200, "speed_mu": 10, "speed_sigma": 5},
}

STATES = [TrafficState.FREE_FLOW, TrafficState.CONGESTION, TrafficState.INCIDENT]
DIRECTIONS = ["N", "S", "E", "W", "NE", "NW", "SE", "SW"]

WEATHER_WEIGHTS = {
    WeatherCondition.CLEAR: 0.50,
    WeatherCondition.RAIN: 0.25,
    WeatherCondition.FOG: 0.10,
    WeatherCondition.SNOW: 0.10,
    WeatherCondition.STORM: 0.05,
}


def next_traffic_state(current: TrafficState) -> TrafficState:
    """Markov chain transition to the next traffic state."""
    probs = MARKOV_TRANSITIONS[current]
    return random.choices(STATES, weights=probs, k=1)[0]


def generate_mock_plate() -> str:
    """Generate a realistic Bolivian-style mock license plate."""
    letters = "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ", k=3))
    numbers = random.randint(100, 999)
    return f"{letters}-{numbers}"


def generate_weather() -> str:
    """Generate a random weather condition based on weighted probabilities."""
    conditions = list(WEATHER_WEIGHTS.keys())
    weights = list(WEATHER_WEIGHTS.values())
    return random.choices(conditions, weights=weights, k=1)[0].value


def generate_events_for_interval(
    location_id: str,
    speed_limit: float,
    traffic_state: TrafficState,
    base_time: datetime,
    interval_seconds: int = 300,
    lambda_override: int | None = None,
    speed_mu_override: float | None = None,
    speed_sigma_override: float | None = None,
) -> list[VehicleEvent]:
    """Generate vehicle events for a single time interval using Poisson + Gaussian."""
    params = STATE_PARAMS[traffic_state]
    lam = lambda_override or params["lambda"]
    mu = speed_mu_override or params["speed_mu"]
    sigma = speed_sigma_override or params["speed_sigma"]

    hourly_count = poisson.rvs(mu=lam)
    interval_count = max(1, int(hourly_count * (interval_seconds / 3600)))

    speeds = norm.rvs(loc=mu, scale=sigma, size=interval_count)
    offsets = np.sort(np.random.uniform(0, interval_seconds, size=interval_count))

    events = []
    for i in range(interval_count):
        speed = round(float(max(0, speeds[i])), 1)
        ts = base_time + timedelta(seconds=float(offsets[i]))

        events.append(VehicleEvent(
            location_id=location_id,
            timestamp=ts.isoformat(),
            plate=generate_mock_plate(),
            speed_kmh=speed,
            direction=random.choice(DIRECTIONS),
            is_infraction=speed > speed_limit,
            traffic_state=traffic_state.value,
        ))
    return events


def generate_events_for_hour(
    location_id: str,
    speed_limit: float,
    traffic_state: TrafficState,
    base_time: datetime,
    lambda_rate: int = 800,
    speed_mu: float = 90.0,
    speed_sigma: float = 12.0,
) -> list[VehicleEvent]:
    """Generate all vehicle events for one full hour (12 five-minute windows)."""
    all_events = []
    current_state = traffic_state
    for window in range(12):
        window_time = base_time + timedelta(minutes=window * 5)
        events = generate_events_for_interval(
            location_id=location_id,
            speed_limit=speed_limit,
            traffic_state=current_state,
            base_time=window_time,
            lambda_override=lambda_rate,
            speed_mu_override=speed_mu,
            speed_sigma_override=speed_sigma,
        )
        all_events.extend(events)
        current_state = next_traffic_state(current_state)
    return all_events
