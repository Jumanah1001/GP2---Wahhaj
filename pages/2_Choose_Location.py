"""
2_Choose_Location.py — Select AOI on interactive map
"""
import streamlit as st
from ui_helpers import init_state, apply_global_style, render_bg

st.set_page_config(page_title="Choose Location", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in"):
    st.warning("Please log in first.")
    st.stop()

if not st.session_state.get("uploaded_images"):
    st.warning("Upload images first.")
    if st.button("← Back to Upload"):
        st.switch_page("pages/3_Upload_Image.py")
    st.stop()

st.markdown("""
<style>
.loc-wrap  { position:relative; z-index:2; padding:24px 32px; }
.loc-title { font-family:'Capriola',sans-serif; font-size:28px; font-weight:700;
             color:#1a1a1a; margin-bottom:6px; }
.loc-sub   { font-size:14px; color:#888; margin-bottom:24px; }
.aoi-card  {
    background:rgba(255,255,255,0.82); border-radius:16px;
    padding:20px 24px; box-shadow:0 4px 20px rgba(0,0,0,0.06);
    margin-bottom:16px;
}
.aoi-label { font-size:13px; font-weight:600; color:#555; margin-bottom:8px; }
.aoi-val   { font-size:15px; font-weight:700; color:#1F3864; font-family:monospace; }
div.stButton > button[kind="primary"] {
    background:#0070FF !important; color:white !important;
    border-radius:10px !important; font-size:16px !important;
    min-height:48px !important; font-family:'Capriola',sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# session defaults
for key, val in {"aoi": None, "location_summary": None}.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.markdown('<div class="loc-wrap">', unsafe_allow_html=True)
st.markdown('<div class="loc-title">📍 Choose Analysis Location</div>', unsafe_allow_html=True)
st.markdown('<div class="loc-sub">Click on the map to set the analysis area, or enter coordinates manually.</div>', unsafe_allow_html=True)

col_map, col_ctrl = st.columns([1.8, 1], gap="large")

# ── MAP ───────────────────────────────────────────────────────
with col_map:
    try:
        import folium
        from streamlit_folium import st_folium

        aoi = st.session_state.get("aoi")
        center_lat = (aoi[1]+aoi[3])/2 if aoi else 24.7136
        center_lon = (aoi[0]+aoi[2])/2 if aoi else 46.6753

        m = folium.Map(location=[center_lat, center_lon],
                       zoom_start=7, tiles="CartoDB positron")

        if aoi:
            folium.Rectangle(
                bounds=[[aoi[1], aoi[0]], [aoi[3], aoi[2]]],
                color="#4CAF50", fill=True, fill_opacity=0.15,
                weight=2, tooltip="Selected AOI"
            ).add_to(m)
            folium.Marker(
                [center_lat, center_lon],
                icon=folium.Icon(color="green", icon="sun", prefix="fa"),
                tooltip="AOI Center"
            ).add_to(m)

        result = st_folium(m, height=500, use_container_width=True)

        click = result.get("last_clicked") if result else None
        if click and click.get("lat"):
            clat, clon = float(click["lat"]), float(click["lng"])
            radius = 0.25
            new_aoi = (round(clon-radius,4), round(clat-radius,4),
                       round(clon+radius,4), round(clat+radius,4))
            st.session_state["aoi"] = new_aoi
            st.session_state["location_summary"] = {
                "center_lat": clat, "center_lon": clon,
                "lon_min": new_aoi[0], "lat_min": new_aoi[1],
                "lon_max": new_aoi[2], "lat_max": new_aoi[3],
            }
            st.rerun()

    except ImportError:
        st.info("Install `streamlit-folium` and `folium` to use the map.\nUse manual input below.")

# ── CONTROLS ──────────────────────────────────────────────────
with col_ctrl:
    # Radius slider
    radius_km = st.slider("Bounding box radius (km)", 1.0, 50.0, 27.5, 0.5,
                          help="Size of the analysis area around the selected point")

    st.markdown("---")
    st.markdown("**Manual Coordinates**")
    mc1, mc2 = st.columns(2)
    with mc1:
        lon_min = st.number_input("lon_min", value=46.5,  format="%.4f")
        lat_min = st.number_input("lat_min", value=24.5,  format="%.4f")
    with mc2:
        lon_max = st.number_input("lon_max", value=47.0,  format="%.4f")
        lat_max = st.number_input("lat_max", value=25.0,  format="%.4f")

    if st.button("✅ Set from inputs", use_container_width=True):
        if lon_min < lon_max and lat_min < lat_max:
            st.session_state["aoi"] = (lon_min, lat_min, lon_max, lat_max)
            st.session_state["location_summary"] = {
                "lon_min": lon_min, "lat_min": lat_min,
                "lon_max": lon_max, "lat_max": lat_max,
                "center_lat": (lat_min+lat_max)/2,
                "center_lon": (lon_min+lon_max)/2,
            }
            st.success("AOI set ✓")
            st.rerun()
        else:
            st.error("Invalid coordinates.")

    # AOI summary card
    aoi = st.session_state.get("aoi")
    if aoi:
        st.markdown(f"""
        <div class="aoi-card">
          <div class="aoi-label">Selected AOI</div>
          <div class="aoi-val">
            {aoi[0]:.4f} → {aoi[2]:.4f}<br>
            {aoi[1]:.4f} → {aoi[3]:.4f}
          </div>
        </div>""", unsafe_allow_html=True)

        if st.button("🔄 Clear selection", use_container_width=True):
            st.session_state["aoi"] = None
            st.rerun()

# ── NAVIGATION ────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
nav1, nav2 = st.columns(2)
with nav1:
    if st.button("← Back to Upload"):
        st.switch_page("pages/3_Upload_Image.py")
with nav2:
    if st.session_state.get("aoi"):
        if st.button("Continue to Environmental Data →",
                     type="primary", use_container_width=True):
            st.switch_page("pages/4_Environmental_Data.py")
    else:
        st.info("🗺️ Click on the map or set coordinates to continue.")

st.markdown('</div>', unsafe_allow_html=True)
