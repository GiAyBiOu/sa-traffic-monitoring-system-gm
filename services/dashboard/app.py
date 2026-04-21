"""TMS Real-Time Traffic Dashboard — Bolivia National Monitoring."""
import os
import sys
import time
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

METRICS_URL = os.getenv("METRICS_SERVICE_URL", "http://localhost:8003")
VEHICLES_URL = os.getenv("VEHICLES_SERVICE_URL", "http://localhost:8004")
GATEWAY_URL = os.getenv("IOT_GATEWAY_URL", "http://localhost:8001")

st.set_page_config(page_title="TMS Bolivia", page_icon="🚦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    .stApp { background-color: #050507; color: #f2f2f2; font-family: 'Inter', sans-serif; }
    [data-testid="stHeader"] { background-color: #050507; border-bottom: 1px solid #3d3a39; }
    [data-testid="stSidebar"] { background-color: #101010; border-right: 1px solid #3d3a39; }
    [data-testid="stMetric"] { background-color: #101010; border: 1px solid #3d3a39; border-radius: 8px; padding: 16px; }
    [data-testid="stMetricValue"] { color: #00d992; font-size: 2rem; font-weight: 600; }
    [data-testid="stMetricLabel"] { color: #b8b3b0; font-weight: 500; }
    [data-testid="stMetricDelta"] { color: #2fd6a1; }
    h1 { color: #f2f2f2 !important; font-weight: 400; letter-spacing: -0.65px; }
    h2, h3 { color: #f2f2f2 !important; font-weight: 400; }
    .stDivider { border-color: #3d3a39 !important; }
    .stDataFrame { border: 1px solid #3d3a39; border-radius: 8px; }
    div[data-testid="stExpander"] { background-color: #101010; border: 1px solid #3d3a39; border-radius: 8px; }
    .stSelectbox label, .stMultiSelect label { color: #b8b3b0 !important; }
    .stPlotlyChart { border: 1px solid #3d3a39; border-radius: 8px; overflow: hidden; }
</style>""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#101010", plot_bgcolor="#050507", font_color="#f2f2f2",
    colorway=["#00d992", "#2fd6a1", "#818cf8", "#fb565b", "#ffba00", "#4cb3d4", "#ff6b9d", "#c084fc"],
    xaxis=dict(gridcolor="#3d3a39", linecolor="#3d3a39"),
    yaxis=dict(gridcolor="#3d3a39", linecolor="#3d3a39"),
    margin=dict(l=40, r=20, t=50, b=40),
)

VIDEO_FEEDS = [
    "https://res.cloudinary.com/dppju38gx/video/upload/v1776782872/14468488_3840_2160_30fps_iayndn.mp4",
    "https://res.cloudinary.com/dppju38gx/video/upload/v1776782805/8321860-hd_1920_1080_30fps_zl1abc.mp4",
]


def safe_get(url, default=None):
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json().get("data", default)
    except Exception:
        pass
    return default


st.markdown("# 🚦 TMS — Traffic Monitoring System")
st.markdown("*National real-time traffic analytics across Bolivia — Santa Cruz, La Paz, Cochabamba*")
st.divider()

with st.sidebar:
    st.markdown("## 🇧🇴 Control Panel")
    auto_refresh = st.toggle("Auto-refresh (10s)", value=False)
    selected_city = st.selectbox("Filter by City", ["All", "Santa Cruz", "La Paz", "Cochabamba"])
    st.divider()
    st.markdown("### Service Health")
    for name, url in {"IoT Gateway": GATEWAY_URL, "Metrics": METRICS_URL, "Vehicles": VEHICLES_URL}.items():
        h = safe_get(f"{url}/health")
        s = h.get("status", "unknown") if h else "offline"
        c = "#00d992" if s == "healthy" else "#fb565b"
        st.markdown(f"<span style='color:{c}'>● </span> **{name}**: {s}", unsafe_allow_html=True)
    st.divider()
    st.markdown("### 📹 Live Camera Feeds")
    feed_tab = st.selectbox("Select Feed", ["Av. Cristo Redentor", "Doble Via La Guardia"])
    st.video(VIDEO_FEEDS[0] if feed_tab == "Av. Cristo Redentor" else VIDEO_FEEDS[1])

city_param = f"&city={selected_city}" if selected_city != "All" else ""
summary = safe_get(f"{METRICS_URL}/api/v1/metrics/summary")
if summary and summary.get("summary"):
    s = summary["summary"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vehicles Observed", f"{s.get('total_vehicles_observed', 0):,}")
    c2.metric("Infractions Detected", f"{s.get('total_infractions', 0):,}")
    c3.metric("Avg Speed", f"{s.get('average_speed_kmh', 0)} km/h")
    c4.metric("Active Locations", s.get("active_locations", 0))
else:
    st.warning("Metrics service is starting up...")

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
                          title="Average Speed by Hour", labels={"hour": "Hour", "avg_speed_kmh": "Speed (km/h)"})
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
        weather_icons = {"CLEAR": "☀️", "RAIN": "🌧️", "SNOW": "❄️", "FOG": "🌫️", "STORM": "⛈️"}
        st.markdown("### Weather Conditions")
        if "weather_condition" in df.columns:
            latest = df.groupby("location_name").last().reset_index()
            for _, row in latest.iterrows():
                cond = row.get("weather_condition", "CLEAR")
                icon = weather_icons.get(cond, "🌤️")
                st.markdown(f"{icon} **{row['location_name']}**: {cond}")

st.divider()
st.markdown("### Recent Infractions")
inf_data = safe_get(f"{VEHICLES_URL}/api/v1/infractions?limit=25")
if inf_data and inf_data.get("infractions"):
    df_inf = pd.DataFrame(inf_data["infractions"])
    cols = [c for c in ["vehicle_plate", "location_id", "speed_kmh", "speed_limit", "triggered_at", "status"] if c in df_inf.columns]
    st.dataframe(df_inf[cols], use_container_width=True, hide_index=True)
else:
    st.info("No infractions available yet")

if auto_refresh:
    time.sleep(10)
    st.rerun()
