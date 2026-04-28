import numpy as np
import streamlit as st
from streamlit_folium import st_folium

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
)
from Wahhaj.models import Raster
from Wahhaj.SuitabilityHeatmap import SuitabilityHeatmap

st.set_page_config(page_title="Suitability Heatmap", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

st.markdown("""
<style>

html, body {
    height: 100%;
}

.main {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.page-title{
    font-family:'Capriola',sans-serif;
    font-size:clamp(34px,3vw,44px);
    color:#5A5959;
    line-height:1;
    margin-bottom:4px;
    text-align:center;
}
.page-subtitle{
    font-family:'Capriola',sans-serif;
    font-size:14px;
    color:#5E5B5B;
    margin-bottom:22px;
    text-align:center;
}

.block-container {
    flex: 1;
}

/* الفوتر */
.footer {
    margin-top: auto;
    text-align: center;
    font-size: 12px;
    color: #666;
    padding-bottom: 12px;
}

.main .block-container {
    max-width: 1280px;
    padding-top: 0.65rem;
    padding-bottom: 1.2rem;
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
    font-size: 20px;
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

/* Same compact action style used in Final Report bottom controls */
.heatmap-actions-shell {
    width: 100%;
    margin: 0.72rem 0 0 0;
    position: relative;
    z-index: 2;
}

.heatmap-actions-shell div[data-testid="stButton"] > button,
.heatmap-actions-shell div.stButton > button {
    min-height: 38px !important;
    height: 38px !important;
    padding: 7px 14px !important;
    border-radius: 12px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: 1.1 !important;
    background: #0070FF !important;
    color: #FFFFFF !important;
    border: none !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}

.heatmap-actions-shell div[data-testid="stButton"] > button:hover,
.heatmap-actions-shell div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.10) !important;
    background: #005fe0 !important;
    color: #FFFFFF !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <div class="page-title">Site Suitability Map</div>
    <div class="page-subtitle">This map shows the overall suitability of the selected site as one unified area</div>
    """,
    unsafe_allow_html=True,
)
render_top_home_button("pages/2_Home.py")


# These values should come from the real run after AHPModel.computeSuitabilityScore().
suitability_raster = st.session_state.get("suitability_raster")
analysis_aoi = st.session_state.get("analysis_aoi")
selected_location = st.session_state.get("selected_location", {})

location_name = selected_location.get("location_name") or "Selected Location"
selected_lat = selected_location.get("latitude")
selected_lon = selected_location.get("longitude")


if suitability_raster is None:
    st.error("No real suitability result found. Please choose a location and run the analysis first.")
    st.stop()
    ai_source = st.session_state.get("ai_obstacle_source", "unknown")

    if ai_source != "AIModel":
        st.warning(
            f"This heatmap is not fully AI-validated. AI obstacle source: {ai_source}"
        )
    else:
        st.success("This heatmap uses AHP scoring with AI model obstacle validation.")

    if analysis_aoi is None:
        st.error("No AOI found. Please choose a location and run the analysis first.")
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
    unsafe_allow_html=True
)

st.markdown('<div class="map-frame">', unsafe_allow_html=True)
st_folium(folium_map, width=None, height=720, returned_objects=[])
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="heatmap-actions-shell">', unsafe_allow_html=True)
sp_left, report_col, sp_right = st.columns([1.70, 1.20, 1.70], gap="small")

with report_col:
    if st.button("View Final Report", use_container_width=True):
        st.switch_page("pages/8_Final_Report.py")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="footer-spacer"></div>', unsafe_allow_html=True)
render_footer()
