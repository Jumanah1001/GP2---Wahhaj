"""
pages/8_Final_Report.py
========================
Final report focused on the selected analysed site.

This version:
- removes the alternative candidate section from the page UI
- shows the same single-site map used in page 6
- keeps PDF/TXT export working as before
- keeps the rest of the report layout intact
"""

import io
import json
from datetime import datetime
from uuid import uuid4

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    require_login,
    render_top_home_button,
    render_footer,
    reset_for_new_analysis,
    save_analysis_to_history,
)

st.set_page_config(page_title="Final Report", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()

# ── top-right home button ──────────────────────────────────────────────────
render_top_home_button("pages/2_Home.py")

# ── page-level CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
 .rpt-card {
    background: rgba(255,255,255,0.96);
    border: 1px solid #dbe3ef;
    border-radius: 16px;
    padding: 26px 30px;
    margin-bottom: 18px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    position: relative;
    z-index: 2;
}
.rpt-section-title {
    font-family: 'Capriola', sans-serif;
    font-size: 16px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748b;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 7px;
}
.rpt-meta-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 15px;
    font-family: 'Capriola', sans-serif;
}
.rpt-meta-table td { padding: 9px 10px; vertical-align: middle; }
.rpt-meta-table tr:nth-child(odd) { background: #f8fafc; }
.rpt-meta-table .label {
    color: #64748b; font-weight: 600; white-space: nowrap; width: 130px;
}
.rpt-meta-table .value { color: #1a1a1a; font-weight: 600; }
.rpt-meta-table .value.done { color: #166534; }
.rpt-meta-table .value.mono {
    font-family: monospace; font-size: 13px; color: #475569;
}
.rpt-exec-summary {
    background: #1F3864; color: #dce8ff; border-radius: 10px;
    padding: 18px 22px; font-family: 'Capriola', sans-serif;
    font-size: 16px; line-height: 1.8;
}
.rpt-top-site {
    display: flex; align-items: center; gap: 18px;
    background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
    border: 1.5px solid rgba(31,56,100,0.14); border-radius: 12px;
    padding: 20px 22px; margin-bottom: 18px;
}
.rpt-top-site-icon {
    width: 58px; height: 58px; background: #1F3864; border-radius: 12px;
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.rpt-top-site-score { margin-left: auto; text-align: right; }
.rpt-top-site-score .big {
    font-size: 40px; font-weight: 800; line-height: 1;
    font-family: 'Capriola', sans-serif;
}
.rpt-top-site-score .lbl {
    font-size: 14px; color: #78716c; margin-top: 4px;
    font-family: 'Capriola', sans-serif;
}
.ahp-row {
    display: flex; align-items: center; gap: 12px; margin-bottom: 12px;
    font-family: 'Capriola', sans-serif;
}
.ahp-name { font-size: 15px; font-weight: 700; color: #1a1a1a; min-width: 220px; }
.ahp-bar-bg { flex: 1; background: #f1f5f9; border-radius: 5px; height: 12px; overflow: hidden; }
.ahp-bar-fill { height: 100%; border-radius: 5px; }
.ahp-pct { font-size: 14px; font-weight: 700; color: #475569; min-width: 52px; text-align: right; }
.ahp-dir { font-size: 13px; color: #94a3b8; min-width: 120px; text-align: right; }
.ahp-cr {
    background: #dcfce7; border: 1px solid #bbf7d0; border-radius: 8px;
    padding: 10px 16px; font-size: 14px; font-weight: 700; color: #166534;
    margin-top: 12px; display: inline-flex; align-items: center; gap: 6px;
    font-family: 'Capriola', sans-serif;
}
.rpt-status-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: #dcfce7; color: #166534; border-radius: 8px;
    padding: 7px 14px; font-size: 14px; font-weight: 700;
    font-family: 'Capriola', sans-serif; margin-bottom: 6px;
}
.rpt-page-header {
    position: relative;
    z-index: 2;
    text-align: center;
    margin: 6px 0 22px 0;
}
.rpt-page-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(34px, 3vw, 44px);
    color: #1a1a1a;
    line-height: 1;
    margin: 0 0 8px 0;
    text-align: center;
}
.rpt-page-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #5E5B5B;
    text-align: center;
    margin: 0 0 12px 0;
}
.rpt-actions-wrap {
    position: relative;
    z-index: 2;
    margin-top: 12px;
}
.rpt-actions-wrap div.stButton > button {
    min-height: 52px;
    font-size: 18px;
}

/* Home button: match other pages more closely */
.main .block-container > div[data-testid="stVerticalBlock"] > div:first-child div[data-testid="stHorizontalBlock"] div[data-testid="column"]:last-child div.stButton > button {
    min-height: 48px !important;
    font-size: 22px !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}

/* Download buttons */
div[data-testid="stDownloadButton"] button {
    min-height: 52px !important;
    border-radius: 10px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 18px !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.10) !important;
}
div[data-testid="stDownloadButton"]:first-of-type button {
    background: #1F3864 !important;
    color: #ffffff !important;
    border: none !important;
}
div[data-testid="stDownloadButton"]:last-of-type button {
    background: #EAF1FB !important;
    color: #1F3864 !important;
    border: 1px solid #C7D5EA !important;
}
</style>
""", unsafe_allow_html=True)

# ── SVG icon helpers ───────────────────────────────────────────────────────
def _icon(path_d, size=15, color="currentColor", sw=2):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{sw}" '
        f'stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">'
        f'{path_d}</svg>'
    )

ICON_REPORT   = _icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>')
ICON_SUN      = _icon('<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>')
ICON_MAP      = _icon('<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/>')
ICON_SCALE    = _icon('<line x1="12" y1="3" x2="12" y2="21"/><path d="M3 6l3 12"/><path d="M21 6l-3 12"/><path d="M3 6h18"/><path d="M6 18h12"/>')
ICON_DOWNLOAD = _icon('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>')
ICON_CHECK    = _icon('<polyline points="20 6 9 17 4 12"/>', color="#166534")
ICON_CLOCK    = _icon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
ICON_PIN      = _icon('<path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z"/><circle cx="12" cy="10" r="3"/>')
ICON_HASH     = _icon('<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>')


def _selected_site_badge(score: float):
    pct = float(score) * 100
    if pct >= 75:
        return "Highly Suitable", "#166534", "#DCFCE7"
    if pct >= 55:
        return "Suitable", "#713f12", "#FEF9C3"
    if pct >= 35:
        return "Moderately Suitable", "#92400E", "#FEF3C7"
    return "Not Suitable", "#991B1B", "#FEE2E2"


def _display_location_name(location_name, lat, lon):
    name = (location_name or "").strip()
    if name and any(ch.isalpha() for ch in name):
        return name
    if lat is not None and lon is not None:
        return f"Selected Site ({lat:.4f}, {lon:.4f})"
    return "Selected Site"


def _interp(v0, v1, t):
    return int(round(v0 + (v1 - v0) * t))


def _score_color_rgb(score):
    score = float(max(0.0, min(1.0, score)))
    anchors = [
        (0.00, (231, 76, 60)),
        (0.35, (244, 176, 64)),
        (0.55, (241, 196, 15)),
        (0.75, (127, 204, 80)),
        (1.00, (34, 197, 94)),
    ]
    for i in range(len(anchors) - 1):
        s0, c0 = anchors[i]
        s1, c1 = anchors[i + 1]
        if s0 <= score <= s1:
            t = 0.0 if s1 == s0 else (score - s0) / (s1 - s0)
            return (
                _interp(c0[0], c1[0], t),
                _interp(c0[1], c1[1], t),
                _interp(c0[2], c1[2], t),
            )
    return anchors[-1][1]


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _aoi_bounds_polygon(aoi):
    lon_min, lat_min, lon_max, lat_max = aoi
    return [
        [lat_min, lon_min],
        [lat_min, lon_max],
        [lat_max, lon_max],
        [lat_max, lon_min],
        [lat_min, lon_min],
    ]


def _mean_valid_suitability_score(suitability) -> float | None:
    if suitability is None or getattr(suitability, "data", None) is None:
        return None
    data = np.asarray(suitability.data, dtype=np.float32)
    nodata = getattr(suitability, "nodata", -9999.0)
    valid = data[np.isfinite(data)]
    valid = valid[valid != nodata]
    if valid.size == 0:
        return None
    return float(valid.mean())


def _resolve_site_score(run, selected_site):
    candidate_keys = ["overall_score", "site_score", "final_score", "score"]
    if isinstance(selected_site, dict):
        for key in candidate_keys:
            value = selected_site.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    if run is not None:
        for key in candidate_keys:
            value = getattr(run, key, None)
            if isinstance(value, (int, float)):
                return float(value)
    suitability = getattr(run, "suitability", None) if run is not None else None
    return _mean_valid_suitability_score(suitability)


def _resolve_selected_site(run, location, aoi, selected_site):
    selected_site = dict(selected_site or {})
    if selected_site.get("score") is not None and selected_site.get("label"):
        return selected_site

    lat = selected_site.get("latitude", location.get("latitude"))
    lon = selected_site.get("longitude", location.get("longitude"))
    if lat is None or lon is None:
        return selected_site

    score = _resolve_site_score(run, selected_site)
    if score is None:
        return selected_site

    label, _, _ = _selected_site_badge(score)
    selected_site.setdefault("site_display_name", _display_location_name(location.get("location_name"), lat, lon))
    selected_site.setdefault("location_name", location.get("location_name"))
    selected_site["latitude"] = lat
    selected_site["longitude"] = lon
    selected_site["score"] = score
    selected_site["score_text"] = f"{score * 100:.1f}%"
    selected_site["label"] = label
    return selected_site


def _build_map_html(aoi, site_info, height=720):
    map_id = f"wahhaj_map_{uuid4().hex}"

    lon_min, lat_min, lon_max, lat_max = aoi
    bounds = [[lat_min, lon_min], [lat_max, lon_max]]
    aoi_outline = _aoi_bounds_polygon(aoi)

    selected_json = json.dumps(site_info, ensure_ascii=False)
    bounds_json = json.dumps(bounds)
    aoi_outline_json = json.dumps(aoi_outline)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; background: transparent; }}
        #{map_id} {{
            width: 100%;
            height: {height}px;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
        }}
        .leaflet-container {{ font-family: Arial, sans-serif; background: #eaeaea; }}
        .leaflet-control-attribution {{ font-size: 10px; }}
        .wahhaj-legend {{
            background: rgba(255,255,255,0.95);
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.12);
            line-height: 1.35;
            min-width: 230px;
        }}
        .wahhaj-legend-title {{
            font-size: 13px;
            font-weight: 700;
            color: #1f3864;
            margin-bottom: 8px;
        }}
        .wahhaj-legend-bar {{
            height: 12px;
            border-radius: 999px;
            background: linear-gradient(90deg, #e74c3c, #f4b040, #f1c40f, #7fcc50, #22c55e);
            margin-bottom: 6px;
        }}
        .wahhaj-legend-scale {{
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: #666;
            margin-bottom: 8px;
        }}
        .wahhaj-legend-note {{
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }}
        .selected-label {{ background: transparent; border: none; }}
        .selected-label div {{
            background: rgba(0,112,255,0.96);
            color: #fff;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            box-shadow: 0 4px 14px rgba(0,0,0,0.18);
        }}
        .wahhaj-popup-title {{
            font-size: 13px;
            font-weight: 700;
            color: #1f3864;
            margin-bottom: 4px;
        }}
        .wahhaj-popup-line {{
            font-size: 12px;
            color: #444;
            margin-bottom: 2px;
        }}
    </style>
</head>
<body>
    <div id="{map_id}"></div>
    <script>
        const selected = {selected_json};
        const bounds = {bounds_json};
        const aoiOutline = {aoi_outline_json};

        const map = L.map("{map_id}", {{ zoomControl: true, scrollWheelZoom: true, preferCanvas: true }});

        const satellite = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
            {{ attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and contributors", maxZoom: 19 }}
        );
        const streets = L.tileLayer(
            "https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",
            {{ attribution: "&copy; OpenStreetMap contributors", maxZoom: 19 }}
        );
        satellite.addTo(map);
        L.control.layers({{"Satellite": satellite, "Streets": streets}}, null, {{ collapsed: true, position: "topright" }}).addTo(map);

        L.polygon(aoiOutline, {{
            color: "#0070FF",
            weight: 2.8,
            fillColor: selected.fillColor,
            fillOpacity: 0.38
        }})
        .bindPopup(`
            <div class="wahhaj-popup-title">${{selected.name}}</div>
            <div class="wahhaj-popup-line">Overall score: ${{selected.score_text}}</div>
            <div class="wahhaj-popup-line">Suitability: ${{selected.suitability}}</div>
        `)
        .addTo(map);

        const selectedIcon = L.divIcon({{
            className: "selected-label",
            html: `<div>${{selected.name}}</div>`,
            iconSize: [130, 26],
            iconAnchor: [65, -6]
        }});

        L.circleMarker([selected.lat, selected.lon], {{
            radius: 8,
            color: "#0070FF",
            weight: 3,
            fillColor: "#ffffff",
            fillOpacity: 0.95
        }})
        .bindPopup(`
            <div class="wahhaj-popup-title">${{selected.name}}</div>
            <div class="wahhaj-popup-line">Overall score: ${{selected.score_text}}</div>
            <div class="wahhaj-popup-line">Suitability: ${{selected.suitability}}</div>
        `)
        .addTo(map);

        L.marker([selected.lat, selected.lon], {{ icon: selectedIcon }}).addTo(map);
        map.fitBounds(bounds, {{ padding: [28, 28] }});

        const legend = L.control({{ position: "bottomleft" }});
        legend.onAdd = function() {{
            const div = L.DomUtil.create("div", "wahhaj-legend");
            div.innerHTML = `
                <div class="wahhaj-legend-title">Site Suitability Scale</div>
                <div class="wahhaj-legend-bar"></div>
                <div class="wahhaj-legend-scale"><span>Low</span><span>High</span></div>
                <div class="wahhaj-legend-note">Blue outline = selected analysis boundary</div>
                <div class="wahhaj-legend-note">Filled area = overall site suitability</div>
                <div class="wahhaj-legend-note">Blue marker = selected site center</div>
            `;
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
"""


# ── guard: need a completed run ────────────────────────────────────────────
run = st.session_state.get("analysis_run")
if run is None:
    st.markdown('<div class="rpt-card">', unsafe_allow_html=True)
    st.warning("No analysis found. Complete the pipeline first.")
    if st.button("Back to Analysis"):

        st.switch_page("pages/5_Analysis.py")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

from Wahhaj.SiteCandidate import SiteCandidate
from Wahhaj.report import Report

loc     = st.session_state.get("selected_location", {})
ranked  = SiteCandidate.rank_all(list(run.candidates)) if run.candidates else []
summary = run.summary()
aoi     = st.session_state.get("aoi", (0, 0, 0, 0))
selected_site = _resolve_selected_site(
    run,
    loc,
    aoi if isinstance(aoi, tuple) and len(aoi) == 4 else None,
    st.session_state.get("selected_site_analysis", {}),
)
st.session_state["selected_site_analysis"] = selected_site
selected_score = selected_site.get("score")
selected_label = selected_site.get("label") or "—"
selected_score_text = selected_site.get("score_text") or (f"{float(selected_score) * 100:.1f}%" if selected_score is not None else "—")
selected_display_name = selected_site.get("site_display_name") or loc.get("location_name") or "Selected Site"
selected_lat = selected_site.get("latitude", loc.get("latitude"))
selected_lon = selected_site.get("longitude", loc.get("longitude"))
selected_coords = (
    f"{selected_lat:.4f}°N, {selected_lon:.4f}°E"
    if selected_lat is not None and selected_lon is not None
    else "—"
)
selected_color = "#1a1a1a"
if selected_score is not None:
    _, selected_color, _ = _selected_site_badge(float(selected_score))
now = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── generate report object (once per run) ─────────────────────────────────
if "report_obj" not in st.session_state or st.session_state["report_obj"] is None:
    rpt = Report()
    rpt.generate(run, ranked, location=loc, selected_site=selected_site)
    st.session_state["report_obj"] = rpt
else:
    rpt = st.session_state["report_obj"]

if selected_score is not None:
    rpt.summary = (
        f"Solar site analysis for {loc.get('location_name', 'the selected site')} completed on "
        f"{datetime.now().strftime('%Y-%m-%d')}. "
        f"The analysed location achieved a suitability score of {selected_score_text} "
        f"and was classified as {selected_label}."
    )

save_analysis_to_history(run, ranked, loc)

lat_val   = loc.get("latitude")
lon_val   = loc.get("longitude")
coord_str = (
    f"{lat_val:.4f}°N, {lon_val:.4f}°E"
    if lat_val is not None and lon_val is not None
    else "—"
)
loc_name = loc.get("location_name", "—")

st.markdown("""
<div class="rpt-page-header">
  <div class="rpt-page-title">Final Report</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="rpt-card">
  <div class="rpt-section-title">{ICON_HASH} &nbsp;Report Details</div>
  <table class="rpt-meta-table">
    <tr>
      <td class="label">{ICON_PIN}&nbsp; Location</td>
      <td class="value">{loc_name}</td>
      <td class="label">{ICON_CLOCK}&nbsp; Generated</td>
      <td class="value">{now}</td>
    </tr>
    <tr>
      <td class="label">Status</td>
      <td class="value done">{summary.get('status','—')}</td>
      <td class="label">Duration</td>
      <td class="value">{summary.get('durationSec','—')} seconds</td>
    </tr>
    <tr>
      <td class="label">Coordinates</td>
      <td class="value mono">{coord_str}</td>
      <td class="label">Selected Site Score</td>
      <td class="value">{selected_score_text}</td>
    </tr>
    <tr>
      <td class="label">Report ID</td>
      <td class="value mono">{str(rpt.report_id)[:16]}…</td>
      <td class="label">Run ID</td>
      <td class="value mono">{run.runId[:16]}…</td>
    </tr>
  </table>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="rpt-card">
  <div class="rpt-section-title">{ICON_SUN} &nbsp;Executive Summary</div>
  <div class="rpt-exec-summary">{rpt.summary}</div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="rpt-top-site">
  <div class="rpt-top-site-icon">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
      <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z"></path>
      <circle cx="12" cy="10" r="3"></circle>
    </svg>
  </div>
  <div style="font-family:'Capriola',sans-serif;">
    <div style="font-size:20px;font-weight:700;color:#1a1a1a;margin-bottom:6px;">
      Selected Site Assessment
    </div>
    <div style="font-size:15px;color:#78716c; line-height:1.7;">
      {selected_display_name} &nbsp;&middot;&nbsp; {selected_coords}
      &nbsp;&middot;&nbsp; Official result for the analysed location
    </div>
  </div>
  <div class="rpt-top-site-score">
    <div class="big" style="color:{selected_color};">{selected_score_text}</div>
    <div class="lbl">{selected_label}</div>
  </div>
</div>
""", unsafe_allow_html=True)

if run.suitability is not None and aoi and len(aoi) == 4 and selected_lat is not None and selected_lon is not None and selected_score is not None:
    fill_color = _rgb_to_hex(_score_color_rgb(float(selected_score)))
    site_info = {
        "name": selected_display_name,
        "score_text": selected_score_text,
        "suitability": selected_label,
        "lat": selected_lat,
        "lon": selected_lon,
        "fillColor": fill_color,
    }

    st.markdown(f"""
    <div class="rpt-card" style="padding-bottom:8px;">
      <div class="rpt-section-title">{ICON_MAP} &nbsp;Suitability Heatmap</div>
    </div>
    """, unsafe_allow_html=True)
    components.html(
        _build_map_html(aoi=aoi, site_info=site_info, height=720),
        height=740,
        scrolling=False,
    )
    st.markdown("<div style='position:relative;z-index:2;font-family:Capriola,sans-serif;color:#64748b;font-size:15px;margin-top:6px;'>This is the same single-site map shown in the Suitability Heatmap page.</div>", unsafe_allow_html=True)

AHP_WEIGHTS = [
    ("Solar Irradiance (GHI)",    0.30, "Higher = Better", "#F59E0B"),
    ("Terrain Slope",             0.22, "Lower = Better",  "#3B82F6"),
    ("Sunshine Hours",            0.18, "Higher = Better", "#EF4444"),
    ("Obstacle Density",          0.13, "Lower = Better",  "#8B5CF6"),
    ("Surface Temperature (LST)", 0.10, "Lower = Better",  "#EC4899"),
    ("Elevation",                 0.07, "Moderate = Best", "#10B981"),
]

rows_html = "".join(
    f"""<div class="ahp-row">
      <div class="ahp-name">{name}</div>
      <div class="ahp-bar-bg">
        <div class="ahp-bar-fill" style="width:{w*100:.0f}%;background:{color};"></div>
      </div>
      <div class="ahp-pct">{w:.0%}</div>
      <div class="ahp-dir">{direction}</div>
    </div>"""
    for name, w, direction, color in AHP_WEIGHTS
)

check_svg = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#166534" '
    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="20 6 9 17 4 12"/></svg>'
)

st.markdown(f"""
<div class="rpt-card">
  <div class="rpt-section-title">{ICON_SCALE} &nbsp;AHP Criteria Weights</div>
  {rows_html}
  <div class="ahp-cr">
    {check_svg} &nbsp;Consistency Ratio (CR) = 0.015 — Consistent (CR &lt; 0.10)
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="rpt-card" style="padding-bottom:10px;">
  <div class="rpt-section-title">{ICON_DOWNLOAD} &nbsp;Export Report</div>
</div>
""", unsafe_allow_html=True)

col_pdf, col_txt = st.columns(2)

with col_pdf:
    pdf_bytes = rpt.build_pdf_bytes(
        run,
        ranked,
        location=loc,
        suitability=run.suitability if run else None,
        aoi=aoi if aoi and len(aoi) == 4 else None,
        selected_site=selected_site,
    )
    if pdf_bytes:
        st.download_button(
            "Download Report (PDF)",
            data=pdf_bytes,
            file_name=f"wahhaj_report_{run.runId[:8]}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    else:
        st.info(
            "PDF export requires `pip install reportlab matplotlib`.  \n"
            "Use the .txt download below in the meantime."
        )

with col_txt:
    report_text = rpt._generate_report_content(run, ranked)
    st.download_button(
        "Download Report (.txt)",
        data=report_text.encode(),
        file_name=f"wahhaj_report_{run.runId[:8]}.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.markdown("<div class='rpt-actions-wrap'>", unsafe_allow_html=True)
st.markdown("---")

col_new, col_back = st.columns(2)
with col_new:
    if st.button("Start New Analysis", use_container_width=True):
        reset_for_new_analysis()
        st.switch_page("pages/3_Choose_Location.py")

with col_back:
    if st.button("Back to Suitability Map", use_container_width=True):
        st.switch_page("pages/6_Suitability_Heatmap.py")

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
render_footer()
