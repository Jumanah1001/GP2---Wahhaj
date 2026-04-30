import numpy as np
import streamlit as st
from streamlit_folium import st_folium
from types import SimpleNamespace

from ui_helpers import (
    init_state,
    apply_global_style,
    apply_ui_consistency_patch,
    render_bg,
    render_footer,
    render_top_home_button,
    load_final_report_from_db,
)
from Wahhaj.models import Raster
from Wahhaj.SuitabilityHeatmap import SuitabilityHeatmap

st.set_page_config(page_title="Suitability Heatmap", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")


def _safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_aoi(value):
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            lon_min, lat_min, lon_max, lat_max = [float(v) for v in value]
            if lon_min < lon_max and lat_min < lat_max:
                return (lon_min, lat_min, lon_max, lat_max)
        except Exception:
            return None
    return None


def _suitability_from_storage(value):
    """Rebuild a lightweight raster-like object from saved report heatmap data."""
    if not isinstance(value, dict):
        return None

    data = value.get("data")
    if not isinstance(data, list) or not data:
        return None

    try:
        arr = np.asarray(data, dtype=float)
        if arr.ndim != 2:
            return None

        nodata_raw = value.get("nodata", None)
        nodata = float(nodata_raw) if nodata_raw is not None else -9999.0

        return SimpleNamespace(data=arr, nodata=nodata)

    except Exception:
        return None


def _load_saved_heatmap_from_report():
    """
    Load a saved heatmap from the report record when the live session raster is gone.
    This is used when View Heatmap is opened from a saved Final Report.
    """
    report_id = st.session_state.get("current_report_id")
    if not report_id:
        return None, None, {}, False

    saved_report = st.session_state.get("saved_report_data")
    if not saved_report or str(saved_report.get("report_id")) != str(report_id):
        saved_report = load_final_report_from_db(str(report_id))
        if saved_report:
            st.session_state["saved_report_data"] = saved_report

    if not saved_report:
        return None, None, {}, False

    criteria = saved_report.get("criteria_data") or {}
    display = criteria.get("display") if isinstance(criteria, dict) else {}
    display = display if isinstance(display, dict) else {}

    suitability_storage = None
    if isinstance(display, dict):
        suitability_storage = display.get("suitability_data") or display.get("heatmap_data")

    if suitability_storage is None and isinstance(criteria, dict):
        suitability_storage = criteria.get("suitability_data") or criteria.get("heatmap_data")

    suitability = _suitability_from_storage(suitability_storage)

    aoi = (
        _safe_aoi(saved_report.get("aoi"))
        or _safe_aoi(display.get("aoi"))
        or _safe_aoi(criteria.get("aoi") if isinstance(criteria, dict) else None)
    )

    lat = (
        _safe_float(saved_report.get("lat"))
        if saved_report.get("lat") is not None
        else _safe_float(display.get("selected_lat"))
    )
    lon = (
        _safe_float(saved_report.get("lon"))
        if saved_report.get("lon") is not None
        else _safe_float(display.get("selected_lon"))
    )

    location_name = (
        saved_report.get("location_name")
        or display.get("location_name")
        or display.get("selected_display_name")
        or "Selected Location"
    )

    selected_location = {
        "location_name": location_name,
        "latitude": lat,
        "longitude": lon,
    }

    if suitability is not None and aoi is not None:
        st.session_state["suitability_raster"] = suitability
        st.session_state["analysis_aoi"] = aoi
        st.session_state["selected_location"] = selected_location

    return suitability, aoi, selected_location, True


st.markdown(
    """
    <style>

    html, body {
        height: 100%;
    }

    .main {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
    }

    .block-container {
        flex: 1;
    }

    .main .block-container {
        max-width: 1280px;
        padding-top: 0.65rem;
        padding-bottom: 1.2rem;
    }

    .page-title {
        font-family: 'Capriola', sans-serif;
        font-size: clamp(40px, 3.4vw, 56px);
        color: #1F2638;
        line-height: 1;
        margin-top: 0.2rem;
        margin-bottom: 8px;
        text-align: center;
        font-weight: 800;
    }

    .page-subtitle {
        font-family: 'Capriola', sans-serif;
        font-size: 17px;
        color: #5E5B5B;
        margin-bottom: 22px;
        text-align: center;
        font-weight: 600;
    }

    .heatmap-page {
        position: relative;
        z-index: 2;
    }

    .heatmap-content {
        width: min(1280px, 88vw);
        margin-left: auto;
        margin-right: auto;
    }

    .heatmap-title-card {
        background: rgba(255,255,255,0.78);
        border: 1px solid rgba(220,226,235,0.95);
        border-radius: 22px;
        box-shadow: 0 10px 26px rgba(15,23,42,0.05);
        backdrop-filter: blur(12px);
        padding: 16px 22px;
        margin-bottom: 16px;
    }

    .heatmap-title {
        font-family: 'Capriola', sans-serif;
        font-size: 24px;
        font-weight: 800;
        color: #303149;
        margin: 0;
    }

    .map-frame {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(215,225,239,0.95);
        margin-bottom: 20px;
    }

    div[data-testid="stVerticalBlock"] {
        gap: 0.45rem;
    }

    .heatmap-actions-shell {
        width: 100%;
        margin: 0.72rem 0 0 0;
        position: relative;
        z-index: 2;
    }

    .heatmap-actions-shell div[data-testid="stButton"] > button,
    .heatmap-actions-shell div.stButton > button {
        min-height: 56px !important;
        height: auto !important;
        padding: 12px 20px !important;
        border-radius: 12px !important;
        font-family: 'Capriola', sans-serif !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        background: #0070FF !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }

    .heatmap-actions-shell div.stButton > button p,
    .heatmap-actions-shell div.stButton > button > div,
    .heatmap-actions-shell div[data-testid="stButton"] > button p,
    .heatmap-actions-shell div[data-testid="stButton"] > button > div {
        font-family: 'Capriola', sans-serif !important;
        font-size: 16px !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        margin: 0 !important;
        padding: 0 !important;
        white-space: normal !important;
    }

    .heatmap-actions-shell div[data-testid="stButton"] > button:hover,
    .heatmap-actions-shell div.stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.10) !important;
        background: #005fe0 !important;
        color: #FFFFFF !important;
    }

    .heatmap-feedback {
        width: min(1280px, 88vw);
        box-sizing: border-box;
        border-radius: 14px;
        padding: 13px 18px;
        margin: 0 auto 18px auto;
        font-family: 'Capriola', sans-serif;
        font-size: 15px;
        line-height: 1.6;
        background: rgba(255,90,90,0.10);
        border: 1px solid rgba(210,70,70,0.24);
        color: #b42318;
    }

    .footer {
        margin-top: auto;
        text-align: center;
        font-size: 13px;
        color: #666;
        padding-bottom: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# Home button must stay at the top like the rest of the pages
render_top_home_button("pages/2_Home.py")

# Page title stays centered under the Home button
st.markdown(
    """
    <div class="page-title">Site Suitability Map</div>
    <div class="page-subtitle">This map shows the overall suitability of the selected site as one unified area</div>
    """,
    unsafe_allow_html=True,
)


# These values should come from the real run after AHPModel.computeSuitabilityScore().
suitability_raster = st.session_state.get("suitability_raster")
analysis_aoi = st.session_state.get("analysis_aoi")
selected_location = st.session_state.get("selected_location", {})

loaded_from_saved_report = False

if suitability_raster is None or analysis_aoi is None:
    (
        saved_suitability_raster,
        saved_analysis_aoi,
        saved_selected_location,
        loaded_from_saved_report,
    ) = _load_saved_heatmap_from_report()

    if saved_suitability_raster is not None:
        suitability_raster = saved_suitability_raster

    if saved_analysis_aoi is not None:
        analysis_aoi = saved_analysis_aoi

    if saved_selected_location:
        selected_location = saved_selected_location

location_name = selected_location.get("location_name") or "Selected Location"
selected_lat = selected_location.get("latitude")
selected_lon = selected_location.get("longitude")


if suitability_raster is None:
    st.markdown(
        """
        <div class="heatmap-feedback">
            No saved suitability heatmap was found for this report. Please run a new analysis and open the Final Report once so the heatmap grid can be stored.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

if analysis_aoi is None:
    st.markdown(
        """
        <div class="heatmap-feedback">
            No AOI boundary was found for this heatmap. Please choose a location and run the analysis first.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


heatmap = SuitabilityHeatmap(resolution=100.0, color_scale="RdYlGn")
folium_map = heatmap.create_folium_map(
    scores=suitability_raster,
    aoi=analysis_aoi,
    location_name=location_name,
    selected_lon=selected_lon,
    selected_lat=selected_lat,
    zoom_start=11,
)

st.markdown('<div class="heatmap-page">', unsafe_allow_html=True)
st.markdown('<div class="heatmap-content">', unsafe_allow_html=True)

st.markdown(
    """
    <div class="heatmap-title-card">
        <div class="heatmap-title">Selected Location Suitability Distribution</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="map-frame">', unsafe_allow_html=True)
st_folium(folium_map, width=None, height=720, returned_objects=[])
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="heatmap-actions-shell">', unsafe_allow_html=True)
sp_left, report_col, sp_right = st.columns([1.70, 1.20, 1.70], gap="small")

with report_col:
    if st.button("View Final Report", use_container_width=True):
        st.switch_page("pages/8_Final_Report.py")

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="footer-spacer"></div>', unsafe_allow_html=True)

apply_ui_consistency_patch()
render_footer()