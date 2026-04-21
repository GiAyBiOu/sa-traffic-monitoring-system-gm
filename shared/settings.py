import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap_servers: str = "localhost:9092"
    topic_vehicle_detected: str = "vehicle.detected.v1"
    topic_infraction_created: str = "infraction.created.v1"
    topic_metric_computed: str = "metric.computed.v1"
    topic_weather_alert: str = "weather.alert.v1"


@dataclass(frozen=True)
class PostgresSettings:
    host: str = "localhost"
    port: int = 5432
    user: str = "smt_user"
    password: str = "smt_dev_password"
    db_infractions: str = "smt_infractions"
    db_notifications: str = "smt_notifications"

    def dsn(self, db_name: str) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{db_name}"


@dataclass(frozen=True)
class TimescaleSettings:
    host: str = "localhost"
    port: int = 5432
    user: str = "smt_user"
    password: str = "smt_dev_password"
    db: str = "smt_metrics"

    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


@dataclass(frozen=True)
class RedisSettings:
    host: str = "localhost"
    port: int = 6379


@dataclass(frozen=True)
class SimulationSettings:
    poisson_lambda: int = 800
    speed_mu: float = 90.0
    speed_sigma: float = 12.0
    speed_limit: float = 110.0
    video_source_urls: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AppSettings:
    app_name: str = "smt"
    app_env: str = "development"
    log_level: str = "INFO"
    kafka: KafkaSettings = field(default_factory=KafkaSettings)
    postgres: PostgresSettings = field(default_factory=PostgresSettings)
    timescale: TimescaleSettings = field(default_factory=TimescaleSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    simulation: SimulationSettings = field(default_factory=SimulationSettings)


def load_settings() -> AppSettings:
    """Load all settings from environment variables (12-Factor: Factor III)."""
    video_urls_raw = os.getenv("VIDEO_SOURCE_URLS", "")
    video_urls = [u.strip() for u in video_urls_raw.split(",") if u.strip()]

    return AppSettings(
        app_name=os.getenv("APP_NAME", "smt"),
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        kafka=KafkaSettings(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            topic_vehicle_detected=os.getenv("KAFKA_TOPIC_VEHICLE_DETECTED", "vehicle.detected.v1"),
            topic_infraction_created=os.getenv("KAFKA_TOPIC_INFRACTION_CREATED", "infraction.created.v1"),
            topic_metric_computed=os.getenv("KAFKA_TOPIC_METRIC_COMPUTED", "metric.computed.v1"),
            topic_weather_alert=os.getenv("KAFKA_TOPIC_WEATHER_ALERT", "weather.alert.v1"),
        ),
        postgres=PostgresSettings(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "smt_user"),
            password=os.getenv("POSTGRES_PASSWORD", "smt_dev_password"),
            db_infractions=os.getenv("POSTGRES_DB_INFRACTIONS", "smt_infractions"),
            db_notifications=os.getenv("POSTGRES_DB_NOTIFICATIONS", "smt_notifications"),
        ),
        timescale=TimescaleSettings(
            host=os.getenv("TIMESCALE_HOST", "localhost"),
            port=int(os.getenv("TIMESCALE_PORT", "5432")),
            user=os.getenv("TIMESCALE_USER", "smt_user"),
            password=os.getenv("TIMESCALE_PASSWORD", "smt_dev_password"),
            db=os.getenv("TIMESCALE_DB", "smt_metrics"),
        ),
        redis=RedisSettings(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
        ),
        simulation=SimulationSettings(
            poisson_lambda=int(os.getenv("POISSON_LAMBDA_DEFAULT", "800")),
            speed_mu=float(os.getenv("SPEED_MU_DEFAULT", "90")),
            speed_sigma=float(os.getenv("SPEED_SIGMA_DEFAULT", "12")),
            speed_limit=float(os.getenv("SPEED_LIMIT_DEFAULT", "110")),
            video_source_urls=video_urls,
        ),
    )
