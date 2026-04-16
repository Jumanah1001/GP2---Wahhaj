"""
pages/3_Choose_Location.py
==========================
Let the user pick or confirm a location before uploading UAV data.

On "Save Location" the page calls ui_helpers.save_selected_location() which:
  1. Stores the human-readable location dict.
  2. Computes the AOI tuple (lon_min, lat_min, lon_max, lat_max).
  3. Creates a FeatureExtractor.Dataset — the pipeline data carrier.

The "Next" button is blocked until a location has been saved.

For a real interactive map, install streamlit-folium:
    pip install streamlit-folium folium requests
The page gracefully degrades to a text-input + manual coord entry when the
package is absent.
"""
import streamlit as st
import requests as _req

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
    save_selected_location,
    require_login,
)

st.set_page_config(page_title="Choose Location", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── page-level working state (not persisted to backend until Save) ────────────
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

# ── try importing folium ───────────────────────────────────────────────────────
try:
    import folium
    from streamlit_folium import st_folium
    _FOLIUM = True
except ImportError:
    _FOLIUM = False

# ── geocoding helper ───────────────────────────────────────────────────────────
def _geocode(query: str):
    """Nominatim geocoding — returns (lat, lon, display_name) or None."""
    try:
        r = _req.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "WAHHAJ-App/1.0"},
            timeout=8,
        )
        r.raise_for_status()
        results = r.json()
        if results:
            res = results[0]
            return float(res["lat"]), float(res["lon"]), res["display_name"]
    except Exception:
        pass
    return None

def _reverse_geocode(lat: float, lon: float):
    """Nominatim reverse geocoding — returns display_name or None."""
    try:
        r = _req.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "jsonv2"},
            headers={"User-Agent": "WAHHAJ-App/1.0"},
            timeout=8,
        )
        r.raise_for_status()
        result = r.json()
        return result.get("display_name")
    except Exception:
        pass
    return None

# ── page style ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.location-page { position:relative; z-index:2; padding-top:10px; }
.page-title {
    font-family:'Capriola',sans-serif; font-size:clamp(34px,3vw,44px);
    color:#5A5959; line-height:1; margin-bottom:6px; text-align:center;
}
.page-subtitle {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#5E5B5B; margin-bottom:14px; text-align:center;
}
.search-label { font-family:'Capriola',sans-serif; font-size:18px; color:#333333; margin-bottom:8px; }
.coord-box {
    background:rgba(255,255,255,0.72); border-radius:14px; padding:14px 18px;
    font-family:'Capriola',sans-serif; font-size:13px; color:#444;
    margin-top:10px; box-shadow:0 4px 12px rgba(0,0,0,0.05);
}
.aoi-preview {
    background:rgba(0,112,255,0.07); border-radius:14px; padding:12px 18px;
    font-family:'Capriola',sans-serif; font-size:12px; color:#0050bb; margin-top:8px;
}
.selected-note {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#5A5959; margin-top:10px; text-align:center;
}
div[data-testid="stTextInput"] input {
    background:#F0EEEE !important; color:#6f6f6f !important; border:none !important;
    border-radius:6px !important; min-height:40px !important;
    font-family:'Capriola',sans-serif !important; font-size:13px !important;
    padding-left:12px !important; box-shadow:none !important;
}
div.stButton > button {
    background:#0070FF; color:white; border:none; border-radius:6px;
    min-height:44px; font-family:'Capriola',sans-serif; font-size:16px;
    box-shadow:4px 5px 4px rgba(0,0,0,0.16);
}
div.stButton > button:hover { background:#005fe0; color:white; }
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
            "Search", value=st.session_state["loc_search_input"],
            placeholder="e.g. Rumah, Al-Qassim, Riyadh",
            label_visibility="collapsed", key="loc_search_txt",
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
                "loc_candidate_name": display,
                "loc_map_lat": lat,
                "loc_map_lon": lon,
            })
            st.success(f"Found: {display}")
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
            placeholder="e.g. Al-Qassim Solar Field", key="manual_name",
        )
        if st.button("Use these coordinates", key="use_manual_btn"):
            st.session_state.update({
                "loc_candidate_lat":  m_lat,
                "loc_candidate_lon":  m_lon,
                "loc_candidate_name": m_name or f"{m_lat:.4f}, {m_lon:.4f}",
                "loc_map_lat": m_lat,
                "loc_map_lon": m_lon,
            })
            st.rerun()

    # ── candidate info ────────────────────────────────────────────────────
    c_lat  = st.session_state["loc_candidate_lat"]
    c_lon  = st.session_state["loc_candidate_lon"]
    c_name = st.session_state["loc_candidate_name"]
    _HALF  = 0.1  # degrees ≈ 11 km

    if c_lat is not None and c_lon is not None:
        st.markdown(
            f"""
            <div class="coord-box">
                <b>📍 Candidate point</b><br>
                Name &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;: {c_name or "—"}<br>
                Latitude &nbsp;: {c_lat:.6f}°<br>
                Longitude: {c_lon:.6f}°
            </div>
            <div class="aoi-preview">
                <b>AOI that will be saved</b> (±{_HALF}° ≈ 11 km)<br>
                lon_min={c_lon-_HALF:.4f} &nbsp; lat_min={c_lat-_HALF:.4f}<br>
                lon_max={c_lon+_HALF:.4f} &nbsp; lat_max={c_lat+_HALF:.4f}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Search for a location or click on the map to pick a point.")

    st.write("")

    # ── action buttons ────────────────────────────────────────────────────
    b1, b2, b3 = st.columns(3)

    with b1:
        if st.button("Save Location", use_container_width=True, key="save_loc_btn"):
            if c_lat is None or c_lon is None:
                st.warning("Please search for a location or enter coordinates first.")
            else:
                name = c_name or f"{c_lat:.4f}, {c_lon:.4f}"
                save_selected_location(
                    location_name = name,
                    latitude      = c_lat,
                    longitude     = c_lon,
                    aoi_half_deg  = _HALF,
                )
                st.success(f"Location saved: **{name}**")
                st.rerun()

    with b2:
        if st.button("Clear", use_container_width=True, key="clear_loc_btn"):
            for _k in ("loc_candidate_lat","loc_candidate_lon","loc_candidate_name",
                       "loc_search_input"):
                st.session_state[_k] = None if "lat" in _k or "lon" in _k else ""
            st.session_state["loc_map_lat"] = 24.7136
            st.session_state["loc_map_lon"] = 46.6753
            st.session_state["selected_location"] = {
                "location_name": "", "latitude": None, "longitude": None
            }
            st.session_state["location_saved"] = False
            st.session_state["aoi"]    = None
            st.session_state["dataset"] = None
            st.rerun()

    with b3:
        # ── GUARD: Next is only active once location is saved ─────────────
        if not st.session_state.get("location_saved"):
            st.button("Next →", use_container_width=True,
                      key="next_loc_btn", disabled=True)
            st.caption("Save a location first")
        else:
            if st.button("Next →", use_container_width=True, key="next_loc_btn"):
                st.switch_page("pages/4_Upload_Image.py")

    # ── status badge ──────────────────────────────────────────────────────
    saved_loc  = st.session_state["selected_location"]
    saved_name = saved_loc["location_name"] or "No location saved yet"
    flag = "✅ Saved" if st.session_state.get("location_saved") else "⬜ Not saved"
    st.markdown(
        f'<div class="selected-note">{flag} &nbsp;·&nbsp; {saved_name}</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("location_saved"):
        aoi = st.session_state.get("aoi")
        ds  = st.session_state.get("dataset")
        if aoi and ds:
            st.markdown(
                f"""
                <div class="aoi-preview" style="margin-top:12px;">
                    <b>Backend objects ready ✓</b><br>
                    AOI: ({aoi[0]:.4f}, {aoi[1]:.4f}, {aoi[2]:.4f}, {aoi[3]:.4f})<br>
                    Dataset: <i>{ds.name}</i>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ═══════════════════════════════════════════════════════════════════════════
# RIGHT: interactive map (Folium) or fallback placeholder
# ═══════════════════════════════════════════════════════════════════════════
with right_col:
    if not _FOLIUM:
        st.markdown(
            """
            <div style="width:100%;height:380px;border-radius:18px;
                 background:linear-gradient(135deg,rgba(79,195,247,.18),rgba(249,178,51,.18));
                 display:flex;align-items:center;justify-content:center;
                 color:#5A5959;font-family:'Capriola',sans-serif;font-size:15px;
                 text-align:center;padding:20px;box-sizing:border-box;">
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

        m = folium.Map(location=[centre_lat, centre_lon],
                       zoom_start=zoom, tiles="OpenStreetMap")

        # Draw saved AOI rectangle
        aoi = st.session_state.get("aoi")
        if aoi:
            lon_min, lat_min, lon_max, lat_max = aoi
            folium.Rectangle(
                bounds=[[lat_min, lon_min], [lat_max, lon_max]],
                color="#0070FF", fill=True, fill_opacity=0.12,
                tooltip="Current AOI",
            ).add_to(m)

        # Mark saved point
        loc = st.session_state.get("selected_location", {})
        if loc.get("latitude") and loc.get("longitude"):
            folium.Marker(
                location=[loc["latitude"], loc["longitude"]],
                tooltip=loc.get("location_name", "Selected"),
                icon=folium.Icon(color="blue", icon="sun", prefix="fa"),
            ).add_to(m)

        map_data = st_folium(
            m, width="100%", height=400,
            returned_objects=["last_clicked"], key="loc_main_map",
        )

        # Handle map clicks
        if map_data and map_data.get("last_clicked"):
            click   = map_data["last_clicked"]
            clk_lat = click["lat"]
            clk_lon = click["lng"]
            prev_lat = st.session_state.get("loc_candidate_lat")
            prev_lon = st.session_state.get("loc_candidate_lon")
            if (prev_lat is None or prev_lon is None
                    or abs(clk_lat - prev_lat) > 0.00001
                    or abs(clk_lon - prev_lon) > 0.00001):
                reverse_name = _reverse_geocode(clk_lat, clk_lon)
                st.session_state.update({
                    "loc_candidate_lat":  round(clk_lat, 6),
                    "loc_candidate_lon":  round(clk_lon, 6),
                    "loc_candidate_name": (
                        reverse_name or
                        st.session_state.get("loc_search_input") or
                        f"{clk_lat:.4f}, {clk_lon:.4f}"
                    ),
                })
                st.rerun()

        st.caption("Click the map to pick a location, or use the search box.")

st.markdown("</div>", unsafe_allow_html=True)
render_footer()