"""Event Simulator: generates mock traffic events for Bolivian locations."""
import os
import sys
import time
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from shared.settings import load_settings
from shared.logger import get_logger
from shared.generators import generate_events_for_interval, next_traffic_state
from shared.models import TrafficState
from shared.locations import BOLIVIA_LOCATIONS

settings = load_settings()
logger = get_logger("event-simulator", settings.log_level)
GATEWAY_URL = os.getenv("IOT_GATEWAY_URL", "http://localhost:8001")


def run_simulation():
    logger.info(f"Simulation started for {len(BOLIVIA_LOCATIONS)} Bolivian locations")
    states = {loc["id"]: TrafficState.FREE_FLOW for loc in BOLIVIA_LOCATIONS}
    cycle = 0
    while True:
        cycle += 1
        base_time = datetime.now(timezone.utc)
        total = 0
        for loc in BOLIVIA_LOCATIONS:
            state = states[loc["id"]]
            events = generate_events_for_interval(
                location_id=loc["id"], speed_limit=loc["speed_limit"],
                traffic_state=state, base_time=base_time, interval_seconds=300,
                lambda_override=loc["lambda_rate"], speed_mu_override=loc["speed_mu"],
                speed_sigma_override=loc["speed_sigma"],
            )
            batch = [e.to_dict() for e in events]
            try:
                resp = requests.post(f"{GATEWAY_URL}/api/v1/events/batch", json={"events": batch}, timeout=10)
                if resp.status_code == 201:
                    total += len(batch)
            except requests.exceptions.ConnectionError:
                logger.warning(f"Gateway unreachable for {loc['name']}")
            states[loc["id"]] = next_traffic_state(state)
        logger.info(f"Cycle {cycle}: {total} events published")
        time.sleep(int(os.getenv("SIMULATION_INTERVAL_SECONDS", "15")))


if __name__ == "__main__":
    time.sleep(5)
    run_simulation()
