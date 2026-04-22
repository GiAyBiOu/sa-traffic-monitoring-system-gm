"""TMS Real-Time Traffic Dashboard — Bolivia National Monitoring."""
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

VIDEO_FEEDS = {
    "Av. Cristo Redentor (SCZ)": "https://res.cloudinary.com/dppju38gx/video/upload/v1776782872/14468488_3840_2160_30fps_iayndn.mp4",
    "Doble Via La Guardia (SCZ)": "https://res.cloudinary.com/dppju38gx/video/upload/v1776782805/8321860-hd_1920_1080_30fps_zl1abc.mp4",
}

LOCATION_MAP = {
    "Av. Cristo Redentor (SCZ)":  ("loc-scz-001", 60),
    "Doble Via La Guardia (SCZ)": ("loc-scz-002", 80),
}

VEHICLE_CLASSES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

st.set_page_config(
    page_title="TMS Bolivia",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
.stAlert { background-color: #101010 !important; border: 1px solid #3d3a39; }
</style>""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#101010", plot_bgcolor="#050507", font_color="#f2f2f2",
    colorway=["#00d992", "#2fd6a1", "#818cf8", "#fb565b", "#ffba00", "#4cb3d4"],
    xaxis=dict(gridcolor="#3d3a39", linecolor="#3d3a39"),
    yaxis=dict(gridcolor="#3d3a39", linecolor="#3d3a39"),
    margin=dict(l=40, r=20, t=50, b=40),
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def safe_get(url, default=None):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", default)
    except Exception:
        pass
    return default


def random_plate():
    digits  = "".join(random.choices(string.digits, k=4))
    letters = "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ", k=3))
    city    = random.choice(["SCZ", "LPZ", "CBB"])
    return f"{digits}-{letters}-{city}"


def push_events_to_gateway(detections: list, feed_name: str) -> list:
    location_id, speed_limit = LOCATION_MAP.get(feed_name, ("loc-scz-001", 60))
    events = []
    for det in detections:
        speed = round(float(max(5, np.random.normal(loc=speed_limit - 5, scale=14))), 1)
        events.append({
            "location_id": location_id,
            "plate": random_plate(),
            "speed_kmh": speed,
            "direction": random.choice(["N", "S", "E", "W"]),
            "is_infraction": speed > speed_limit,
            "traffic_state": "free_flow",
        })
    if events:
        try:
            requests.post(
                f"{GATEWAY_URL}/api/v1/events/batch",
                json={"events": events},
                timeout=5,
            )
        except Exception:
            pass
    return events


@st.cache_resource(show_spinner="Loading YOLO model (yolov8n.pt)...")
def load_yolo():
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        return model, True
    except Exception as e:
        return None, str(e)


def _render_panel(stats_slot, log_slot, total, frames, detections, log):
    with stats_slot.container():
        st.metric("Total Detected", total)
        st.metric("Frames Processed", frames)
        by_class = {}
        for d in detections:
            by_class[d["class"]] = by_class.get(d["class"], 0) + 1
        for cls_name, cnt in by_class.items():
            st.caption(f"{cls_name}: {cnt}")
    if log:
        with log_slot.container():
            st.markdown("**Events pushed**")
            for evt in reversed(log[-8:]):
                status = "INFRACTION" if evt.get("is_infraction") else "OK"
                st.caption(f"{evt['plate']}, {evt['speed_kmh']} km/h, {status}")


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🇧🇴 TMS Bolivia")
    page = st.radio(
        "View",
        ["Dashboard", "Live Detection"],
        label_visibility="collapsed",
    )
    st.divider()

    auto_refresh = st.toggle("Auto-refresh every 10s", value=False)
    selected_city = st.selectbox("Filter by City", ["All", "Santa Cruz", "La Paz", "Cochabamba"])
    st.divider()

    st.markdown("**Service Health**")
    proc_health = safe_get(f"{PROCESSOR_URL}/health") or {}
    for label, url in {
        "Gateway":   GATEWAY_URL,
        "Processor": PROCESSOR_URL,
        "Metrics":   METRICS_URL,
        "Vehicles":  VEHICLES_URL,
    }.items():
        h = safe_get(f"{url}/health")
        status = h.get("status", "unknown") if h else "offline"
        dot = "🟢" if status == "healthy" else "🔴"
        extra = f", {proc_health.get('events_processed', 0):,} events" if label == "Processor" and proc_health else ""
        st.caption(f"{dot} **{label}**: {status}{extra}")


# ── Page: Dashboard ──────────────────────────────────────────────────────────

if page == "Dashboard":
    st.markdown("# 🚦 Traffic Monitoring System")
    st.markdown("*National real-time traffic analytics — Santa Cruz, La Paz, Cochabamba*")
    st.divider()

    city_param = f"&city={selected_city}" if selected_city != "All" else ""

    # KPI row — combines seed data + live Kafka counters
    summary = safe_get(f"{METRICS_URL}/api/v1/metrics/summary")
    live_events       = proc_health.get("events_processed", 0)
    live_infractions  = proc_health.get("total_infractions", 0)

    c1, c2, c3, c4 = st.columns(4)
    if summary and summary.get("summary"):
        s = summary["summary"]
        c1.metric("Vehicles (seeded)", f"{s.get('total_vehicles_observed', 0):,}")
        c2.metric("Infractions (seeded)", f"{s.get('total_infractions', 0):,}")
        c3.metric("Avg Speed", f"{s.get('average_speed_kmh', 0)} km/h")
    else:
        c1.metric("Vehicles (seeded)", "—")
        c2.metric("Infractions (seeded)", "—")
        c3.metric("Avg Speed", "—")
    c4.metric("Live Events (Kafka)", f"{live_events:,}", delta=f"+{live_infractions} infractions")

    # Charts from seeded metrics
    metrics_data = safe_get(f"{METRICS_URL}/api/v1/metrics?limit=200{city_param}")
    metrics_list = metrics_data.get("metrics", []) if metrics_data else []

    if metrics_list:
        df = pd.DataFrame(metrics_list)
        if "timestamp" in df.columns:
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        col_l, col_r = st.columns(2)
        with col_l:
            if {"hour", "avg_speed_kmh", "location_name"}.issubset(df.columns):
                fig = px.line(df, x="hour", y="avg_speed_kmh", color="location_name",
                              title="Average Speed by Hour (km/h)")
                fig.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)
        with col_r:
            if {"hour", "total_vehicles", "location_name"}.issubset(df.columns):
                fig = px.bar(df, x="hour", y="total_vehicles", color="location_name",
                             title="Vehicle Volume by Hour", barmode="group")
                fig.update_layout(**PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True)

        col_p, col_w = st.columns(2)
        with col_p:
            if {"location_name", "infraction_count"}.issubset(df.columns):
                pie_df = df.groupby("location_name")["infraction_count"].sum().reset_index()
                fig = px.pie(pie_df, names="location_name", values="infraction_count",
                             title="Infractions by Location", hole=0.45)
                fig.update_layout(**PLOTLY_LAYOUT)
                fig.update_traces(textfont_color="#f2f2f2")
                st.plotly_chart(fig, use_container_width=True)
        with col_w:
            if "weather_condition" in df.columns:
                icons = {"CLEAR": "☀️", "RAIN": "🌧️", "FOG": "🌫️", "STORM": "⛈️", "SNOW": "❄️"}
                st.markdown("**Weather by Location**")
                for _, row in df.groupby("location_name").last().reset_index().iterrows():
                    cond = row.get("weather_condition", "CLEAR")
                    st.caption(f"{icons.get(cond,'🌤️')} {row['location_name']}: {cond}")

    # Live infractions from Kafka Stream Processor
    st.divider()
    st.markdown("### Live Infractions — Kafka Stream")
    st.caption(
        f"Stream Processor: **{live_events:,}** events processed, "
        f"**{live_infractions:,}** infractions detected. "
        f"Auto-refresh: {'ON' if auto_refresh else 'OFF (toggle in sidebar)'}."
    )

    inf_data = safe_get(f"{PROCESSOR_URL}/api/v1/infractions")
    if inf_data and inf_data.get("infractions"):
        df_inf = pd.DataFrame(inf_data["infractions"])
        cols = [c for c in ["vehicle_plate", "location_id", "speed_kmh", "speed_limit", "triggered_at"] if c in df_inf.columns]
        st.dataframe(df_inf[cols], use_container_width=True, hide_index=True)
    else:
        st.info("No live infractions yet. The simulator pushes events every 15 s.")

    if auto_refresh:
        time.sleep(10)
        st.rerun()


# ── Page: Live Detection ─────────────────────────────────────────────────────

elif page == "Live Detection":
    st.markdown("# YOLO Vehicle Detection — Live Feed")
    st.markdown("*Object detection on simulated CCTV feeds. Detected vehicles are pushed as events to the IoT Gateway → Kafka → Stream Processor.*")
    st.divider()

    feed_name = st.selectbox("Camera feed", list(VIDEO_FEEDS.keys()))
    feed_url  = VIDEO_FEEDS[feed_name]

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        confidence  = st.slider("Confidence threshold", 0.10, 0.90, 0.35, 0.05)
    with col_b:
        frame_skip  = st.slider("Process every N frames", 1, 10, 3)
    with col_c:
        push_toggle = st.toggle("Push detections as gateway events", value=True)

    model, yolo_ok = load_yolo()
    yolo_error = yolo_ok if isinstance(yolo_ok, str) else None
    yolo_ready = yolo_ok is True

    if yolo_error:
        st.warning(f"YOLO unavailable: {yolo_error}. Running in simulated mode.")

    if st.button("Start Detection", type="primary", use_container_width=True):
        import cv2

        col_vid, col_panel = st.columns([3, 1])
        frame_slot  = col_vid.empty()
        stats_slot  = col_panel.empty()
        log_slot    = col_panel.empty()

        total_detected = 0
        detection_log  = []
        stop_key = "stop_detection"

        with col_vid:
            if not yolo_ready:
                st.video(feed_url)
            stop_btn = st.button("Stop", key=stop_key)

        if yolo_ready:
            cap = cv2.VideoCapture(feed_url)
            if not cap.isOpened():
                st.error("Cannot open video stream.")
                st.stop()

            frame_n = 0
            BOX_COLOR = (0, 217, 146)  # emerald

            while cap.isOpened() and not stop_btn:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame_n += 1
                if frame_n % frame_skip != 0:
                    continue

                results = model(frame, conf=confidence, verbose=False,
                                classes=list(VEHICLE_CLASSES.keys()))
                detections = []
                for box in results[0].boxes:
                    cls_id   = int(box.cls[0])
                    conf_val = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label = VEHICLE_CLASSES.get(cls_id, "vehicle")
                    detections.append({"class": label, "confidence": conf_val})
                    cv2.rectangle(frame, (x1, y1), (x2, y2), BOX_COLOR, 2)
                    text = f"{label} {conf_val:.0%}"
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), BOX_COLOR, -1)
                    cv2.putText(frame, text, (x1 + 2, y1 - 4),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (5, 5, 7), 1)

                total_detected += len(detections)
                if push_toggle and detections:
                    pushed = push_events_to_gateway(detections, feed_name)
                    detection_log.extend(pushed)

                frame_slot.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                                 channels="RGB", use_container_width=True)
                _render_panel(stats_slot, log_slot, total_detected, frame_n // frame_skip,
                              detections, detection_log)
                time.sleep(0.04)

            cap.release()
            st.success(f"Stopped. {total_detected} vehicles detected total.")

        else:
            # Simulated mode — no YOLO, push random mock events
            st.info("Simulated detection active. Mock vehicle events are being pushed to the gateway every 2 s.")
            stop_sim = st.button("Stop Simulation", key="stop_sim")
            sim_total = 0

            while not stop_sim:
                n = random.randint(1, 5)
                fake = [{"class": random.choice(["car", "bus", "truck"]),
                         "confidence": round(random.uniform(0.60, 0.95), 2)}
                        for _ in range(n)]
                if push_toggle:
                    pushed = push_events_to_gateway(fake, feed_name)
                    detection_log.extend(pushed)
                sim_total += n
                _render_panel(stats_slot, log_slot, sim_total, sim_total // 3, fake, detection_log)
                time.sleep(2)

    else:
        st.video(feed_url)
        st.caption("Press **Start Detection** to run YOLO on this feed and push detections as real Kafka events.")

