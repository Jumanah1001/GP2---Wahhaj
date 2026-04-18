"""
pages/3_Choose_Location.py
==========================
Let the user pick or confirm a location before uploading UAV data.

Changes in this version
-----------------------
1. Backend/internal text removed from the user-facing UI:
   - "Backend objects ready ✓" (was developer debug text)
   - "AOI that will be saved" with raw coordinate values (backend detail)
   - "AOI: (lon, lat, lon, lat)" box after save (internal)
   Replaced with a clean, user-friendly confirmation message.

2. Next button visual fix:
   - Before save: grey background (#d0d0d0), dark text (#666), clearly disabled.
   - After save: blue (#0070FF), white text, enabled.
   Explicit CSS overrides Streamlit's semi-transparent disabled style.

3. Text input color improved:
   - Input text is now color:#1a1a1a (near-black on #F0EEEE background).
   - Contrast ratio ~12:1 — clearly readable.

4. Candidate info box simplified:
   - Shows Name / Latitude / Longitude clearly.
   - No raw AOI math or backend object references.

5. Status badge simplified:
   - Shows "✅ Location saved: <Name>" or "No location selected yet".
   - No backend coordinates shown.
"""
import streamlit as st
import requests as _req
import logging

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
    save_selected_location,
    require_login,
)

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Choose Location", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── page-level working state ───────────────────────────────────────────────────
for _k, _v in {
    "loc_candidate_lat":  None,
    "loc_candidate_lon":  None,
    "loc_candidate_name": "",
    "loc_search_input":   "",
    "loc_map_lat":        24.7136,
    "loc_map_lon":        46.6753,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── optional Folium ────────────────────────────────────────────────────────────
try:
    import folium
    from streamlit_folium import st_folium
    _FOLIUM = True
except ImportError:
    _FOLIUM = False

# ── geocoding helpers ──────────────────────────────────────────────────────────
def _geocode(query: str):
    """
    Returns (lat, lon, name) where name is ALWAYS the user's typed query string.
    We force Accept-Language: en so Nominatim returns English even if the
    browser/server locale is Arabic, but we still prefer the user's own text
    as the display name to guarantee it stays in English.
    """
    try:
        r = _req.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={
                "User-Agent": "WAHHAJ-App/1.0",
                "Accept-Language": "en",          # force English from Nominatim
            },
            timeout=8,
        )
        r.raise_for_status()
        results = r.json()
        if results:
            res = results[0]
            # Always use the query the user typed — never the Arabic display_name.
            return float(res["lat"]), float(res["lon"]), query.strip()
    except Exception as e:
        logger.debug("Geocode error: %s", e)
    return None


def _reverse_geocode(lat: float, lon: float):
    """
    English-only reverse geocode.
    Uses accept-language=en as a query param (more reliable than header)
    so Nominatim always returns English place names.
    """
    try:
        r = _req.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "accept-language": "en",   # query param forces English output
                "namedetails": 1,
            },
            headers={"User-Agent": "WAHHAJ-App/1.0"},
            timeout=8,
        )
        r.raise_for_status()
        result = r.json()
        # Use English name from namedetails if available, fallback to display_name
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


# ── page style ─────────────────────────────────────────────────────────────────
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
    font-family:'Capriola',sans-serif; font-size:16px;
    color:#1a1a1a; font-weight:600; margin-bottom:8px;
}

/* ── input text: dark on light background ── */
div[data-testid="stTextInput"] input {
    background:#F0EEEE !important;
    color:#1a1a1a !important;
    border:1px solid #ccc !important;
    border-radius:6px !important;
    min-height:40px !important;
    font-family:'Capriola',sans-serif !important;
    font-size:14px !important;
    padding-left:12px !important;
    box-shadow:none !important;
}
div[data-testid="stTextInput"] input::placeholder {
    color:#999 !important;
}

/* ── candidate info card ── */
.coord-card {
    background:rgba(255,255,255,0.88);
    border-radius:12px;
    padding:14px 18px;
    font-family:'Capriola',sans-serif;
    font-size:14px;
    color:#1a1a1a;
    margin-top:10px;
    box-shadow:0 2px 8px rgba(0,0,0,0.06);
    border:1px solid #e0e0e0;
    line-height:1.8;
}
.coord-card b { color:#0070FF; }

/* ── save confirmation (user-friendly, no backend data) ── */
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
    font-size:13px;
    color:#444;
    margin-top:10px;
    text-align:center;
}

/* — Next button — same size in both states — */
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

/* disabled = grey */
div.stButton > button:disabled,
div.stButton > button[disabled] {
    background:#d0d0d0 !important;
    color:#777 !important;
    border:1px solid #bbb !important;
    box-shadow:none !important;
    cursor:not-allowed !important;
    opacity:1 !important;
}

/* enabled = blue */
div.stButton > button:not(:disabled) {
    background:#0070FF !important;
    color:white !important;
    border:none !important;
    box-shadow:4px 5px 4px rgba(0,0,0,0.16) !important;
}

div.stButton > button:not(:disabled):hover {
    background:#005fe0;
}

/* ── hint below disabled Next ── */
.next-hint {
    font-family:'Capriola',sans-serif;
    font-size:11px;
    color:#888;
    text-align:center;
    margin-top:4px;
}
</style>
""", unsafe_allow_html=True)

render_top_home_button("pages/2_Home.py")

st.markdown('<div class="location-page">', unsafe_allow_html=True)
st.markdown('<div class="page-title">Choose Location</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Select the target site before uploading the UAV image</div>',
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([1.1, 0.9], gap="large")

# ═══════════════════════════════════════════════════════════════════════════
# LEFT: controls
# ═══════════════════════════════════════════════════════════════════════════
with left_col:

    # ── search bar ────────────────────────────────────────────────────────
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
                "loc_candidate_lat":  lat,
                "loc_candidate_lon":  lon,
                "loc_candidate_name": search_val.strip(),
                "loc_map_lat": lat,
                "loc_map_lon": lon,
            })
            st.success(f"✅ Found: {search_val.strip()}")
        else:
            st.warning("Location not found. Try a different name or enter coordinates manually.")

    # ── manual coord entry ────────────────────────────────────────────────
    with st.expander("Enter coordinates manually", expanded=False):
        mc1, mc2 = st.columns(2)
        with mc1:
            m_lat = st.number_input(
                "Latitude", min_value=-90.0, max_value=90.0,
                value=float(st.session_state["loc_candidate_lat"] or 24.7136),
                format="%.6f", key="manual_lat",
            )
        with mc2:
            m_lon = st.number_input(
                "Longitude", min_value=-180.0, max_value=180.0,
                value=float(st.session_state["loc_candidate_lon"] or 46.6753),
                format="%.6f", key="manual_lon",
            )
        m_name = st.text_input(
            "Location name",
            value=st.session_state["loc_candidate_name"] or "",
            placeholder="e.g. Al-Qassim Solar Field",
            key="manual_name",
        )
        if st.button("Use these coordinates", key="use_manual_btn"):
            st.session_state.update({
                "loc_candidate_lat":  m_lat,
                "loc_candidate_lon":  m_lon,
                "loc_candidate_name": m_name or f"{m_lat:.4f}°N, {m_lon:.4f}°E",
                "loc_map_lat": m_lat,
                "loc_map_lon": m_lon,
            })
            st.rerun()

    # ── candidate info — user-friendly, no backend details ───────────────
    c_lat  = st.session_state["loc_candidate_lat"]
    c_lon  = st.session_state["loc_candidate_lon"]
    c_name = st.session_state["loc_candidate_name"]

    if c_lat is not None and c_lon is not None:
        display_name = c_name.strip() if c_name else f"{c_lat:.4f}°N, {c_lon:.4f}°E"
        st.markdown(
            f"""
            <div class="coord-card">
                📍 <b>{display_name}</b><br>
                Latitude:&nbsp;&nbsp; {c_lat:.5f}°<br>
                Longitude: {c_lon:.5f}°
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Search for a location or click on the map to select a point.")

    st.write("")

    # ── action buttons ────────────────────────────────────────────────────
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("Save Location", use_container_width=True, key="save_loc_btn"):
            if c_lat is None or c_lon is None:
                st.warning("Please search for a location or enter coordinates first.")
            else:
                name = (c_name or "").strip() or f"{c_lat:.4f}°N, {c_lon:.4f}°E"
                save_selected_location(
                    location_name = name,
                    latitude      = c_lat,
                    longitude     = c_lon,
                    aoi_half_deg  = 0.1,
                )
                st.rerun()

    with b2:
        if st.button("Clear", use_container_width=True, key="clear_loc_btn"):
            for _k in ("loc_candidate_lat", "loc_candidate_lon",
                       "loc_candidate_name", "loc_search_input"):
                st.session_state[_k] = None if "lat" in _k or "lon" in _k else ""
            st.session_state["loc_map_lat"] = 24.7136
            st.session_state["loc_map_lon"] = 46.6753
            st.session_state["selected_location"] = {
                "location_name": "", "latitude": None, "longitude": None
            }
            st.session_state["location_saved"] = False
            st.session_state["aoi"]     = None
            st.session_state["dataset"] = None
            st.rerun()

    with b3:
        location_is_saved = st.session_state.get("location_saved", False)

        if not location_is_saved:
            # ── Grey, disabled — user cannot proceed ───────────────────
            st.button(
                "Next →",
                use_container_width=True,
                key="next_loc_btn",
                disabled=True,
            )
            st.markdown(
                '<div class="next-hint">Save a location first</div>',
                unsafe_allow_html=True,
            )
        else:
            # ── Blue, enabled — user can proceed ───────────────────────
            if st.button("Next →", use_container_width=True, key="next_loc_btn"):
                st.switch_page("pages/4_Upload_Image.py")

    # ── status — clean, no backend data ─────────────────────────────────
    st.write("")
    saved_loc  = st.session_state.get("selected_location", {})
    saved_name = saved_loc.get("location_name", "")

    if st.session_state.get("location_saved") and saved_name:
        # User-friendly confirmation — no coordinates, no AOI, no backend text
        st.markdown(
            f'<div class="save-confirm">✅ Location saved: {saved_name}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="status-note">No location selected yet</div>',
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: map (Folium) or fallback
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
                Use the Search box or manual coordinate entry on the left.
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

        aoi = st.session_state.get("aoi")
        if aoi:
            lon_min, lat_min, lon_max, lat_max = aoi
            folium.Rectangle(
                bounds=[[lat_min, lon_min], [lat_max, lon_max]],
                color="#0070FF", fill=True, fill_opacity=0.12,
                tooltip="Selected area",
            ).add_to(m)

        loc = st.session_state.get("selected_location", {})
        if loc.get("latitude") and loc.get("longitude"):
            folium.Marker(
                location=[loc["latitude"], loc["longitude"]],
                tooltip=loc.get("location_name", "Selected"),
                icon=folium.Icon(color="blue", icon="sun", prefix="fa"),
            ).add_to(m)

        map_data = st_folium(
            m, width="100%", height=400,
            returned_objects=["last_clicked"],
            key="loc_main_map",
        )

        if map_data and map_data.get("last_clicked"):
            click   = map_data["last_clicked"]
            clk_lat = click["lat"]
            clk_lon = click["lng"]
            prev_lat = st.session_state.get("loc_candidate_lat")
            prev_lon = st.session_state.get("loc_candidate_lon")
            if (prev_lat is None or prev_lon is None
                    or abs(clk_lat - prev_lat) > 0.00001
                    or abs(clk_lon - prev_lon) > 0.00001):
                # 1) user typed a search term → use it as-is (always English)
                # 2) user clicked map directly → reverse geocode forced to English
                # 3) geocode fails → fall back to plain coordinates
                user_typed = st.session_state.get("loc_search_input", "").strip()
                if user_typed:
                    resolved_name = user_typed
                else:
                    resolved_name = (
                        _reverse_geocode(clk_lat, clk_lon)
                        or f"{round(clk_lat, 4)}N, {round(clk_lon, 4)}E"
                    )
                st.session_state.update({
                    "loc_candidate_lat":  round(clk_lat, 6),
                    "loc_candidate_lon":  round(clk_lon, 6),
                    "loc_candidate_name": resolved_name,
                })
                st.rerun()

        st.caption("Click the map to pick a location, or use the search box.")

st.markdown("</div>", unsafe_allow_html=True)
render_footer()