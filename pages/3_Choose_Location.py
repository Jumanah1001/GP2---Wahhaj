"""
pages/3_Choose_Location.py
==========================
Choose a site by drawing an AOI rectangle on the map.

Behavior in this version
------------------------
1. Search/manual coordinates are used to move the map to the desired place.
2. The user must draw a rectangle (AOI) on the map.
3. The saved analysis location is the drawn AOI itself.
4. The AOI centre is calculated automatically and stored as the selected location.
5. All downstream analysis uses this saved AOI.
"""

import logging

import requests as _req
import streamlit as st

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
    require_login,
    reset_pipeline_for_new_location,
    reset_location_ui_state,
    reset_active_analysis_state,
    set_dataset_state,
    ui_icon,
)
from Wahhaj.FeatureExtractor import Dataset

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Choose Location", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── page-level working state ────────────────────────────────────────────────
for _k, _v in {
    "loc_candidate_lat": None,
    "loc_candidate_lon": None,
    "loc_candidate_name": "",
    "loc_search_input": "",
    "loc_map_lat": 24.7136,
    "loc_map_lon": 46.6753,
    "loc_candidate_aoi": None,          # draft rectangle before save
    "loc_rectangle_drawn": False,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── optional Folium ─────────────────────────────────────────────────────────
try:
    import folium
    from folium.plugins import Draw
    from streamlit_folium import st_folium
    _FOLIUM = True
except ImportError:
    _FOLIUM = False

# ── geocoding helpers ───────────────────────────────────────────────────────
def _geocode(query: str):
    """
    Returns (lat, lon, name) where name is ALWAYS the user's typed query string.
    """
    try:
        r = _req.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={
                "User-Agent": "WAHHAJ-App/1.0",
                "Accept-Language": "en",
            },
            timeout=8,
        )
        r.raise_for_status()
        results = r.json()
        if results:
            res = results[0]
            return float(res["lat"]), float(res["lon"]), query.strip()
    except Exception as e:
        logger.debug("Geocode error: %s", e)
    return None


def _reverse_geocode(lat: float, lon: float):
    """
    English-only reverse geocode.
    """
    try:
        r = _req.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "accept-language": "en",
                "namedetails": 1,
            },
            headers={"User-Agent": "WAHHAJ-App/1.0"},
            timeout=8,
        )
        r.raise_for_status()
        result = r.json()
        name_details = result.get("namedetails", {})
        english_name = (
            name_details.get("name:en")
            or result.get("display_name")
            or ""
        )
        return english_name.strip() or None
    except Exception as e:
        logger.debug("Reverse geocode error: %s", e)
    return None


def _center_from_aoi(aoi):
    lon_min, lat_min, lon_max, lat_max = aoi
    return (
        round((lat_min + lat_max) / 2.0, 6),
        round((lon_min + lon_max) / 2.0, 6),
    )


def _aoi_from_drawn_geojson(geojson):
    """
    Convert drawn rectangle/polygon GeoJSON into:
    (lon_min, lat_min, lon_max, lat_max)
    """
    try:
        geometry = geojson.get("geometry", {})
        coords = geometry.get("coordinates", [])
        if not coords:
            return None

        ring = coords[0]
        lons = [pt[0] for pt in ring]
        lats = [pt[1] for pt in ring]

        lon_min = round(min(lons), 6)
        lon_max = round(max(lons), 6)
        lat_min = round(min(lats), 6)
        lat_max = round(max(lats), 6)

        if lon_max <= lon_min or lat_max <= lat_min:
            return None

        return (lon_min, lat_min, lon_max, lat_max)
    except Exception as e:
        logger.debug("AOI extraction error: %s", e)
        return None


def _persist_selected_location(location_name: str, latitude: float, longitude: float, aoi):
    """
    Save selected location + explicit AOI to session_state and initialise a draft dataset ref.
    """
    location_dict = {
        "location_name": location_name.strip(),
        "latitude": latitude,
        "longitude": longitude,
    }
    st.session_state["selected_location"] = location_dict
    st.session_state["location_saved"] = True
    st.session_state["aoi"] = aoi

    draft_dataset = Dataset(
        name=location_name.strip(),
        aoi=aoi,
        images=[],
    )
    set_dataset_state(
        draft_dataset,
        status="location_selected",
        source="session",
        image_count=0,
        aoi=aoi,
        name=location_name.strip(),
    )
    return location_dict


# ── page style ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
.location-page { position:relative; z-index:2; padding-top:10px; }
.page-title {
    font-family:'Capriola',sans-serif; font-size:clamp(34px,3vw,44px);
    color:#1a1a1a; line-height:1; margin-bottom:6px; text-align:center;
}
.page-subtitle {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#444; margin-bottom:14px; text-align:center;
}
.search-label {
    font-family:'Capriola',sans-serif; font-size:17px;
    color:#1a1a1a; font-weight:600; margin-bottom:8px;
}

/* ── unified content card ── */
.loc-card-anchor { height:0; }

div[data-testid="stVerticalBlock"]:has(.loc-card-anchor) {
    background: rgba(255,255,255,0.94);
    border: 1px solid #e2e8f0;
    border-radius: 22px;
    padding: 24px 26px 18px;
    margin: 18px 0 20px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}

div[data-testid="stVerticalBlock"]:has(.loc-card-anchor) > div[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 0 !important;
}

div[data-testid="stVerticalBlock"]:has(.loc-card-anchor) .loc-card-anchor {
    display:block;
    height:0;
    margin:0;
    padding:0;
}

/* ── input text ── */
div[data-testid="stTextInput"] input {
    background:#F0EEEE !important;
    color:#1a1a1a !important;
    border:1px solid #ccc !important;
    border-radius:6px !important;
    min-height:42px !important;
    font-family:'Capriola',sans-serif !important;
    font-size:15px !important;
    padding-left:12px !important;
    box-shadow:none !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color:#999 !important;
}

/* ── info card ── */
.coord-card {
    background:rgba(255,255,255,0.88);
    border-radius:12px;
    padding:14px 18px;
    font-family:'Capriola',sans-serif;
    font-size:15px;
    color:#1a1a1a;
    margin-top:10px;
    box-shadow:0 2px 8px rgba(0,0,0,0.06);
    border:1px solid #e0e0e0;
    line-height:1.85;
}
.coord-card b { color:#0070FF; }

/* ── save confirmation ── */
.save-confirm {
    background:#dcfce7;
    border-radius:10px;
    padding:10px 16px;
    font-family:'Capriola',sans-serif;
    font-size:14px;
    color:#166534;
    margin-top:10px;
    border:1px solid #bbf7d0;
    font-weight:600;
}

/* ── status note ── */
.status-note {
    font-family:'Capriola',sans-serif;
    font-size:14px;
    color:#444;
    margin-top:10px;
    text-align:center;
}

.area-hint {
    font-family:'Capriola',sans-serif;
    font-size:17px;
    color:#4b5563;
    margin-top:10px;
    line-height:1.85;
}

/* ── buttons ── */
div.stButton > button:disabled,
div.stButton > button[disabled],
div.stButton > button:not(:disabled) {
    min-height:44px !important;
    height:44px !important;
    width:100% !important;
    border-radius:6px !important;
    font-family:'Capriola',sans-serif !important;
    font-size:16px !important;
    padding:0 18px !important;
    box-sizing:border-box !important;
}

div.stButton > button:disabled,
div.stButton > button[disabled] {
    background:#d0d0d0 !important;
    color:#777 !important;
    border:1px solid #bbb !important;
    box-shadow:none !important;
    cursor:not-allowed !important;
    opacity:1 !important;
}

div.stButton > button:not(:disabled) {
    background:#0070FF !important;
    color:white !important;
    border:none !important;
    box-shadow:4px 5px 4px rgba(0,0,0,0.16) !important;
}

div.stButton > button:not(:disabled):hover {
    background:#005fe0;
}

.next-hint {
    font-family:'Capriola',sans-serif;
    font-size:13px;
    color:#6b7280;
    text-align:center;
    margin-top:6px;
}
</style>
""", unsafe_allow_html=True)

render_top_home_button("pages/2_Home.py")

st.markdown('<div class="location-page">', unsafe_allow_html=True)
st.markdown('<div class="page-title">Choose Location</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Search the site, then draw the analysis boundary on the map</div>',
    unsafe_allow_html=True,
)

card_box = st.container()
with card_box:
    st.markdown('<div class="loc-card-anchor"></div>', unsafe_allow_html=True)
    left_col, right_col = st.columns([1.12, 0.88], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT: controls
# ═══════════════════════════════════════════════════════════════════════════
with left_col:

    st.markdown('<div class="search-label">Search Location</div>', unsafe_allow_html=True)
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        search_val = st.text_input(
            "Search",
            value=st.session_state["loc_search_input"],
            placeholder="e.g. Rumah, Al-Qassim, Riyadh",
            label_visibility="collapsed",
            key="loc_search_txt",
        )
    with sc2:
        search_go = st.button("Search", use_container_width=True, key="loc_search_btn")

    if search_go and search_val.strip():
        st.session_state["loc_search_input"] = search_val.strip()
        result = _geocode(search_val.strip())
        if result:
            lat, lon, display = result
            st.session_state.update({
                "loc_candidate_lat": lat,
                "loc_candidate_lon": lon,
                "loc_candidate_name": display,
                "loc_map_lat": lat,
                "loc_map_lon": lon,
            })
            st.success(f"Found: {display}")
        else:
            st.warning("Location not found. Try another name or enter coordinates manually.")

    with st.expander("Enter coordinates manually", expanded=False):
        mc1, mc2 = st.columns(2)
        with mc1:
            m_lat = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=float(st.session_state["loc_candidate_lat"] or 24.7136),
                format="%.6f",
                key="manual_lat",
            )
        with mc2:
            m_lon = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=float(st.session_state["loc_candidate_lon"] or 46.6753),
                format="%.6f",
                key="manual_lon",
            )
        m_name = st.text_input(
            "Location name",
            value=st.session_state["loc_candidate_name"] or "",
            placeholder="e.g. Al-Qassim Solar Field",
            key="manual_name",
        )
        if st.button("Use these coordinates", key="use_manual_btn"):
            st.session_state.update({
                "loc_candidate_lat": m_lat,
                "loc_candidate_lon": m_lon,
                "loc_candidate_name": m_name.strip() or f"{m_lat:.4f}°N, {m_lon:.4f}°E",
                "loc_map_lat": m_lat,
                "loc_map_lon": m_lon,
            })
            st.rerun()

    c_lat = st.session_state["loc_candidate_lat"]
    c_lon = st.session_state["loc_candidate_lon"]
    c_name = st.session_state["loc_candidate_name"]
    c_aoi = st.session_state.get("loc_candidate_aoi")

    if c_aoi is not None:
        lon_min, lat_min, lon_max, lat_max = c_aoi
        display_name = c_name.strip() if c_name else f"{c_lat:.4f}°N, {c_lon:.4f}°E"
        st.markdown(
            f"""
            <div class="coord-card">
                {ui_icon('location', 16, '#0070FF')} <b>{display_name}</b><br>
                Center Latitude:&nbsp;&nbsp; {c_lat:.5f}°<br>
                Center Longitude: {c_lon:.5f}°<br>
                Boundary selected successfully
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif c_lat is not None and c_lon is not None:
        display_name = c_name.strip() if c_name else f"{c_lat:.4f}°N, {c_lon:.4f}°E"
        st.markdown(
            f"""
            <div class="coord-card">
                {ui_icon('location', 16, '#0070FF')} <b>{display_name}</b><br>
                Center Latitude:&nbsp;&nbsp; {c_lat:.5f}°<br>
                Center Longitude: {c_lon:.5f}°<br>
                Draw a rectangle on the map to define the analysis area
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Search for a location, then draw the analysis boundary on the map.")

    st.markdown(
        """
        <div class="area-hint">
            1) Search or move to your site<br>
            2) Use the rectangle tool on the map<br>
            3) Draw the exact analysis boundary<br>
            4) Save the location
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("Save Location", use_container_width=True, key="save_loc_btn"):
            if c_aoi is None:
                st.warning("Please draw the analysis boundary rectangle on the map first.")
            else:
                prev_loc = st.session_state.get("selected_location", {}) or {}
                prev_aoi = st.session_state.get("aoi")
                prev_signature = (
                    prev_loc.get("location_name"),
                    prev_loc.get("latitude"),
                    prev_loc.get("longitude"),
                    tuple(prev_aoi) if isinstance(prev_aoi, (list, tuple)) else prev_aoi,
                )
                new_signature = (
                    (c_name or "").strip() or f"{c_lat:.4f}°N, {c_lon:.4f}°E",
                    c_lat,
                    c_lon,
                    tuple(c_aoi),
                )

                if prev_signature != new_signature:
                    reset_pipeline_for_new_location(clear_uploaded=True)

                _persist_selected_location(
                    location_name=new_signature[0],
                    latitude=c_lat,
                    longitude=c_lon,
                    aoi=c_aoi,
                )
                st.rerun()

    with b2:
        if st.button("Clear", use_container_width=True, key="clear_loc_btn"):
            reset_location_ui_state()
            reset_active_analysis_state(clear_location=True)
            st.rerun()

    with b3:
        location_is_saved = st.session_state.get("location_saved", False)

        if not location_is_saved:
            st.button(
                "Next →",
                use_container_width=True,
                key="next_loc_btn",
                disabled=True,
            )
            st.markdown(
                '<div class="next-hint">Save an analysis boundary first</div>',
                unsafe_allow_html=True,
            )
        else:
            if st.button("Next →", use_container_width=True, key="next_loc_btn"):
                st.switch_page("pages/4_Upload_Image.py")

    st.write("")
    saved_loc = st.session_state.get("selected_location", {})
    saved_name = saved_loc.get("location_name", "")

    if st.session_state.get("location_saved") and saved_name:
        st.markdown(
            f'<div class="save-confirm">✅ Location saved: {saved_name}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-note">No analysis boundary saved yet</div>',
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: map
# ═══════════════════════════════════════════════════════════════════════════
with right_col:
    if not _FOLIUM:
        st.markdown(
            """
            <div style="width:100%;height:380px;border-radius:18px;
                 background:linear-gradient(135deg,rgba(79,195,247,.18),rgba(249,178,51,.18));
                 display:flex;align-items:center;justify-content:center;
                 color:#333;font-family:'Capriola',sans-serif;font-size:15px;
                 text-align:center;padding:20px;box-sizing:border-box;
                 border:1px solid #ddd;">
                Interactive map requires:<br>
                <code>pip install streamlit-folium folium requests</code><br><br>
                Search for a place, then draw the analysis boundary rectangle.
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        centre_lat = st.session_state["loc_map_lat"]
        centre_lon = st.session_state["loc_map_lon"]
        zoom = 10 if st.session_state["loc_candidate_lat"] is not None else 6

        m = folium.Map(
            location=[centre_lat, centre_lon],
            zoom_start=zoom,
            tiles="OpenStreetMap",
        )

        Draw(
            export=False,
            draw_options={
                "polyline": False,
                "polygon": False,
                "circle": False,
                "circlemarker": False,
                "marker": False,
                "rectangle": True,
            },
            edit_options={"edit": False, "remove": True},
        ).add_to(m)

        draft_aoi = st.session_state.get("loc_candidate_aoi")
        saved_aoi = st.session_state.get("aoi")

        # Show draft AOI if present, otherwise show saved AOI
        aoi_to_show = draft_aoi if draft_aoi is not None else saved_aoi
        if aoi_to_show:
            lon_min, lat_min, lon_max, lat_max = aoi_to_show
            folium.Rectangle(
                bounds=[[lat_min, lon_min], [lat_max, lon_max]],
                color="#0070FF",
                fill=True,
                fill_opacity=0.12,
                tooltip="Analysis boundary",
            ).add_to(m)

        loc = st.session_state.get("selected_location", {})
        if loc.get("latitude") is not None and loc.get("longitude") is not None:
            folium.Marker(
                location=[loc["latitude"], loc["longitude"]],
                tooltip=loc.get("location_name", "Selected"),
                icon=folium.Icon(color="blue", icon="sun", prefix="fa"),
            ).add_to(m)
        elif c_lat is not None and c_lon is not None:
            folium.Marker(
                location=[c_lat, c_lon],
                tooltip=c_name or "Candidate center",
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(m)

        map_data = st_folium(
            m,
            width="100%",
            height=400,
            returned_objects=["last_active_drawing"],
            key="loc_main_map",
        )

        if map_data and map_data.get("last_active_drawing"):
            drawn = map_data["last_active_drawing"]
            drawn_aoi = _aoi_from_drawn_geojson(drawn)

            if drawn_aoi is not None:
                prev_aoi = st.session_state.get("loc_candidate_aoi")
                if prev_aoi != drawn_aoi:
                    center_lat, center_lon = _center_from_aoi(drawn_aoi)

                    user_typed = st.session_state.get("loc_search_input", "").strip()
                    if user_typed:
                        resolved_name = user_typed
                    else:
                        resolved_name = (
                            _reverse_geocode(center_lat, center_lon)
                            or f"AOI Center ({center_lat:.4f}, {center_lon:.4f})"
                        )

                    st.session_state.update({
                        "loc_candidate_aoi": drawn_aoi,
                        "loc_rectangle_drawn": True,
                        "loc_candidate_lat": center_lat,
                        "loc_candidate_lon": center_lon,
                        "loc_candidate_name": resolved_name,
                        "loc_map_lat": center_lat,
                        "loc_map_lon": center_lon,
                    })
                    st.rerun()

        st.caption("Search the area, then use the rectangle tool on the map to define the analysis boundary.")

st.markdown("</div>", unsafe_allow_html=True)
render_footer()