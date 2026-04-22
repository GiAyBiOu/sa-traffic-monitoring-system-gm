"""TMS Real-Time Traffic Dashboard — Bolivia National Monitoring with YOLO Detection."""
import os
import sys
import time
import random
import string
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

METRICS_URL   = os.getenv("METRICS_SERVICE_URL",   "http://localhost:8003")
VEHICLES_URL  = os.getenv("VEHICLES_SERVICE_URL",  "http://localhost:8004")
GATEWAY_URL   = os.getenv("IOT_GATEWAY_URL",        "http://localhost:8001")
PROCESSOR_URL = os.getenv("STREAM_PROCESSOR_URL",  "http://localhost:8002")

st.set_page_config(page_title="TMS Bolivia", page_icon="🚦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { background-color: #050507; color: #f2f2f2; font-family: 'Inter', sans-serif; }
    [data-testid="stHeader"] { background-color: #050507; border-bottom: 1px solid #3d3a39; }
    [data-testid="stSidebar"] { background-color: #101010; border-right: 1px solid #3d3a39; }
    [data-testid="stMetric"] { background-color: #101010; border: 1px solid #3d3a39; border-radius: 8px; padding: 16px; }
    [data-testid="stMetricValue"] { color: #00d992; font-size: 2rem; font-weight: 600; }
    [data-testid="stMetricLabel"] { color: #b8b3b0; font-weight: 500; }
    h1 { color: #f2f2f2 !important; font-weight: 400; letter-spacing: -0.65px; }
    h2, h3 { color: #f2f2f2 !important; font-weight: 400; }
    .stDataFrame { border: 1px solid #3d3a39; border-radius: 8px; }
    .stPlotlyChart { border: 1px solid #3d3a39; border-radius: 8px; overflow: hidden; }
</style>""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#101010", plot_bgcolor="#050507", font_color="#f2f2f2",
    colorway=["#00d992", "#2fd6a1", "#818cf8", "#fb565b", "#ffba00", "#4cb3d4"],
    xaxis=dict(gridcolor="#3d3a39", linecolor="#3d3a39"),
    yaxis=dict(gridcolor="#3d3a39", linecolor="#3d3a39"),
    margin=dict(l=40, r=20, t=50, b=40),
)

VIDEO_FEEDS = {
    "Av. Cristo Redentor": "https://res.cloudinary.com/dppju38gx/video/upload/v1776782872/14468488_3840_2160_30fps_iayndn.mp4",
    "Doble Via La Guardia": "https://res.cloudinary.com/dppju38gx/video/upload/v1776782805/8321860-hd_1920_1080_30fps_zl1abc.mp4",
}

VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
BOX_COLOR = (0, 217, 146)
CITIES = ["SCZ", "LPZ", "CBB"]


def safe_get(url, default=None):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", default)
    except Exception:
        pass
    return default


def generate_mock_plate():
    city = random.choice(CITIES)
    digits = ''.join(random.choices(string.digits, k=4))
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"{digits}-{letters}-{city}"


def push_detection_events(detections: list, location_name: str):
    """Push YOLO-detected vehicles as events to the IoT Gateway."""
    loc_map = {
        "Av. Cristo Redentor": "loc-scz-001",
        "Doble Via La Guardia": "loc-scz-002",
    }
    limit_map = {"loc-scz-001": 60, "loc-scz-002": 80}
    location_id = loc_map.get(location_name, "loc-scz-001")
    speed_limit = limit_map.get(location_id, 60)

    events = []
    for det in detections:
        speed = max(10, np.random.normal(loc=speed_limit - 5, scale=15))
        events.append({
            "location_id": location_id,
            "plate": generate_mock_plate(),
            "speed_kmh": round(speed, 1),
            "direction": random.choice(["N", "S", "E", "W"]),
            "is_infraction": speed > speed_limit,
            "traffic_state": "free_flow",
        })
    if events:
        try:
            requests.post(f"{GATEWAY_URL}/api/v1/events/batch", json={"events": events}, timeout=5)
        except Exception:
            pass
    return events


@st.cache_resource
def load_yolo_model():
    try:
        from ultralytics import YOLO
        return YOLO("yolov8n.pt"), True
    except ImportError:
        return None, False


# ──────── SIDEBAR ────────
with st.sidebar:
    st.markdown("## 🇧🇴 Control Panel")
    page = st.radio("Navigation", ["📊 Dashboard", "📹 Live Detection"], label_visibility="collapsed")
    auto_refresh = st.toggle("Auto-refresh (10s)", value=False)
    selected_city = st.selectbox("Filter by City", ["All", "Santa Cruz", "La Paz", "Cochabamba"])
    st.divider()
    st.markdown("### Service Health")
    for name, url in {"Gateway": GATEWAY_URL, "Processor": PROCESSOR_URL, "Metrics": METRICS_URL, "Vehicles": VEHICLES_URL}.items():
        h = safe_get(f"{url}/health")
        s = h.get("status", "unknown") if h else "offline"
        c = "#00d992" if s == "healthy" else "#fb565b"
        extra = ""
        if name == "Processor" and h:
            extra = f" · {h.get('events_processed', 0):,} events"
        st.markdown(f"<span style='color:{c}'>● </span> **{name}**: {s}{extra}", unsafe_allow_html=True)


# ──────── PAGE: DASHBOARD ────────
if page == "📊 Dashboard":
    st.markdown("# 🚦 TMS — Traffic Monitoring System")
    st.markdown("*National real-time traffic analytics across Bolivia*")
    st.divider()

    city_param = f"&city={selected_city}" if selected_city != "All" else ""
    summary = safe_get(f"{METRICS_URL}/api/v1/metrics/summary")

    processor_health = safe_get(f"{PROCESSOR_URL}/health")
    live_events = processor_health.get("events_processed", 0) if processor_health else 0
    live_infractions = processor_health.get("total_infractions", 0) if processor_health else 0

    if summary and summary.get("summary"):
        s = summary["summary"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vehicles (Seed)", f"{s.get('total_vehicles_observed', 0):,}")
        c2.metric("Infractions (Seed)", f"{s.get('total_infractions', 0):,}")
        c3.metric("Live Events (Kafka)", f"{live_events:,}", delta=f"+{live_infractions} infractions")
        c4.metric("Active Locations", s.get("active_locations", 0))
    else:
        c1, c2 = st.columns(2)
        c1.metric("Live Events (Kafka)", f"{live_events:,}", delta=f"+{live_infractions} infractions")
        c2.metric("Kafka Status", "Streaming" if live_events > 0 else "Starting...")

    metrics_data = safe_get(f"{METRICS_URL}/api/v1/metrics?limit=200{city_param}")
    metrics_list = metrics_data.get("metrics", []) if metrics_data else []

    if metrics_list:
        df = pd.DataFrame(metrics_list)
        if "timestamp" in df.columns:
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        col_l, col_r = st.columns(2)
        with col_l:
            if "hour" in df.columns and "avg_speed_kmh" in df.columns:
                fig = px.line(df, x="hour", y="avg_speed_kmh", color="location_name",
                              title="Average Speed by Hour (km/h)", labels={"hour": "Hour", "avg_speed_kmh": "Speed (km/h)"})
                fig.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            if "hour" in df.columns and "total_vehicles" in df.columns:
                fig = px.bar(df, x="hour", y="total_vehicles", color="location_name",
                             title="Vehicle Volume by Hour", barmode="group",
                             labels={"hour": "Hour", "total_vehicles": "Vehicles"})
                fig.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        col_p, col_w = st.columns(2)
        with col_p:
            if "infraction_count" in df.columns:
                pie_df = df.groupby("location_name")["infraction_count"].sum().reset_index()
                fig = px.pie(pie_df, names="location_name", values="infraction_count",
                             title="Infractions by Location", hole=0.45)
                fig.update_layout(**PLOTLY_LAYOUT)
                fig.update_traces(textfont_color="#f2f2f2")
                st.plotly_chart(fig, use_container_width=True)

        with col_w:
            weather_icons = {"CLEAR": "☀️", "RAIN": "🌧️", "FOG": "🌫️", "STORM": "⛈️"}
            st.markdown("### Weather Conditions")
            if "weather_condition" in df.columns:
                latest = df.groupby("location_name").last().reset_index()
                for _, row in latest.iterrows():
                    cond = row.get("weather_condition", "CLEAR")
                    icon = weather_icons.get(cond, "🌤️")
                    st.markdown(f"{icon} **{row['location_name']}**: {cond}")

    st.divider()
    st.markdown("### 🚨 Recent Infractions — Live from Kafka Stream")

    st.caption(f"Stream Processor: **{live_events:,}** events processed · **{live_infractions:,}** infractions detected")

    inf_data = safe_get(f"{PROCESSOR_URL}/api/v1/infractions")
    if inf_data and inf_data.get("infractions"):
        df_inf = pd.DataFrame(inf_data["infractions"])
        cols = [c for c in ["vehicle_plate", "location_id", "speed_kmh", "speed_limit", "triggered_at"] if c in df_inf.columns]
        st.dataframe(df_inf[cols], use_container_width=True, hide_index=True)
    else:
        st.info("No live infractions yet — simulator is feeding events every 15s")


# ──────── PAGE: LIVE DETECTION ────────
elif page == "📹 Live Detection":
    st.markdown("# 📹 YOLO Vehicle Detection — Live Feed")
    st.markdown("*Real-time object detection on simulated CCTV feeds*")
    st.divider()

    feed_name = st.selectbox("Select Camera Feed", list(VIDEO_FEEDS.keys()))
    feed_url = VIDEO_FEEDS[feed_name]

    col_cfg_1, col_cfg_2, col_cfg_3 = st.columns(3)
    with col_cfg_1:
        confidence = st.slider("Confidence Threshold", 0.1, 0.9, 0.35, 0.05)
    with col_cfg_2:
        frame_skip = st.slider("Process every N frames", 1, 10, 3)
    with col_cfg_3:
        push_events = st.toggle("Push detections as events", value=True)

    if st.button("▶ Start Detection", type="primary", use_container_width=True):
        model, yolo_available = load_yolo_model()

        if not yolo_available:
            st.warning("YOLO not installed in this environment. Install with: `pip install ultralytics opencv-python-headless`")
            st.info("Running in **Simulated Detection Mode** — generating mock vehicle detections from the feed.")

        col_video, col_stats = st.columns([2, 1])
        with col_video:
            frame_placeholder = st.empty()
            if not yolo_available:
                st.video(feed_url)
        with col_stats:
            stats_placeholder = st.empty()
            events_placeholder = st.empty()

        if yolo_available:
            try:
                import cv2
            except ImportError:
                st.error("OpenCV not installed. Run: pip install opencv-python-headless")
                st.stop()

            cap = cv2.VideoCapture(feed_url)
            if not cap.isOpened():
                st.error(f"Cannot open video feed: {feed_url}")
            else:
                frame_count = 0
                total_detected = 0
                detection_log = []
                stop = st.button("⏹ Stop Detection", key="stop_btn")

                while cap.isOpened() and not stop:
                    ret, frame = cap.read()
                    if not ret:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue

                    frame_count += 1
                    if frame_count % frame_skip != 0:
                        continue

                    results = model(frame, conf=confidence, verbose=False, classes=list(VEHICLE_CLASSES.keys()))
                    BOX_COLOR = (0, 217, 146)

                    detections = []
                    for box in results[0].boxes:
                        cls_id = int(box.cls[0])
                        conf_val = float(box.conf[0])
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = VEHICLE_CLASSES.get(cls_id, "vehicle")
                        detections.append({"class": label, "confidence": conf_val, "bbox": (x1, y1, x2, y2)})
                        cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)
                        text = f"{label} {conf_val:.0%}"
                        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), BOX_COLOR, -1)
                        cv2.putText(frame, text, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (5, 5, 7), 1)

                    total_detected += len(detections)
                    if push_events and detections:
                        pushed = push_detection_events(detections, feed_name)
                        detection_log.extend(pushed)

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

                    with stats_placeholder.container():
                        st.metric("Vehicles This Frame", len(detections))
                        st.metric("Total Detected", total_detected)
                        st.metric("Frames Processed", frame_count // frame_skip)

                    if detection_log:
                        with events_placeholder.container():
                            st.markdown("**Latest Events Pushed**")
                            for evt in reversed(detection_log[-8:]):
                                icon = "🔴" if evt.get("is_infraction") else "🟢"
                                st.caption(f"{icon} {evt['plate']} — {evt['speed_kmh']} km/h")

                    time.sleep(0.05)

                cap.release()
                st.success(f"Detection stopped. Total vehicles detected: {total_detected}")
        else:
            st.info("Running simulated detection — pushing mock events every 2 seconds")
            stop_sim = st.button("⏹ Stop Simulation", key="stop_sim_btn")
            sim_count = 0
            detection_log = []
            while not stop_sim:
                n_vehicles = random.randint(1, 5)
                fake_detections = [{"class": random.choice(["car", "bus", "truck"]), "confidence": round(random.uniform(0.6, 0.95), 2)} for _ in range(n_vehicles)]
                if push_events:
                    pushed = push_detection_events(fake_detections, feed_name)
                    detection_log.extend(pushed)
                    sim_count += n_vehicles

                with stats_placeholder.container():
                    st.metric("Simulated Vehicles", sim_count)
                    st.metric("This Batch", n_vehicles)

                if detection_log:
                    with events_placeholder.container():
                        st.markdown("**Latest Events Pushed**")
                        for evt in reversed(detection_log[-8:]):
                            icon = "🔴" if evt.get("is_infraction") else "🟢"
                            st.caption(f"{icon} {evt['plate']} — {evt['speed_kmh']} km/h")

                time.sleep(2)

    else:
        st.markdown("### Preview")
        st.video(feed_url)
        st.caption("Click **Start Detection** to activate YOLO vehicle detection on this feed.")


if auto_refresh and page == "📊 Dashboard":
    time.sleep(10)
    st.rerun()
