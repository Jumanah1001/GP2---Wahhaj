"""
6_Suitability_Heatmap.py — WAHHAJ AOI Suitability Heatmap
=========================================================
Single-site heatmap page:
- Shows suitability distribution ONLY inside the selected AOI
- No "top areas" / no multiple-site comparison
- Selected location is shown as the centre marker
- Ranked comparison between multiple saved sites should be handled
  later in Ranked Results, not here
"""

import json
from pathlib import Path
from uuid import uuid4

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
)

st.set_page_config(page_title="Suitability Heatmap - WAHHAJ", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in"):
    st.switch_page("pages/1_Login.py")


# ── icons ─────────────────────────────────────────────────────
def _i(d, sz=15, c="currentColor", ep=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{sz}" height="{sz}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:middle;flex-shrink:0;">'
        f'<path d="{d}"/>{ep}</svg>'
    )


ICO_MAP = _i(
    "M9 18l-6 3V6l6-3 6 3 6-3v15l-6 3-6-3z",
    c="#0070FF",
    ep='<line x1="9" y1="3" x2="9" y2="18" stroke="#0070FF" stroke-width="2"/><line x1="15" y1="6" x2="15" y2="21" stroke="#0070FF" stroke-width="2"/>',
)
ICO_WARN = _i(
    "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
    c="#E2534A",
    ep='<line x1="12" y1="9" x2="12" y2="13" stroke="#E2534A" stroke-width="2"/><line x1="12" y1="17" x2="12.01" y2="17" stroke="#E2534A" stroke-width="2"/>',
)
ICO_INFO = _i(
    "M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z",
    c="#0070FF",
    ep='<line x1="12" y1="10" x2="12" y2="16" stroke="#0070FF" stroke-width="2"/><line x1="12" y1="7" x2="12.01" y2="7" stroke="#0070FF" stroke-width="2"/>',
)


# ── helpers ───────────────────────────────────────────────────
def suitability_badge(score):
    s = score * 100
    if s >= 75:
        return "Highly Suitable"
    if s >= 55:
        return "Suitable"
    if s >= 35:
        return "Moderately Suitable"
    return "Not Suitable"


def _safe_pct(x):
    return f"{x * 100:.1f}%" if x is not None else "—"


def _display_location_name(location_name, lat, lon):
    name = (location_name or "").strip()
    if name and any(ch.isalpha() for ch in name):
        return name
    return "Selected Site"


def _point_to_grid_cell(lat, lon, aoi, shape):
    lon_min, lat_min, lon_max, lat_max = aoi
    rows, cols = shape[:2]

    if lon_max <= lon_min or lat_max <= lat_min:
        return 0, 0

    x_ratio = (lon - lon_min) / (lon_max - lon_min)
    y_ratio = (lat_max - lat) / (lat_max - lat_min)

    col = int(x_ratio * cols)
    row = int(y_ratio * rows)

    col = max(0, min(cols - 1, col))
    row = max(0, min(rows - 1, row))
    return row, col


def _cell_bounds(aoi, shape, row, col):
    lon_min, lat_min, lon_max, lat_max = aoi
    rows, cols = shape[:2]

    lon_step = (lon_max - lon_min) / cols
    lat_step = (lat_max - lat_min) / rows

    west = lon_min + (col * lon_step)
    east = west + lon_step

    north = lat_max - (row * lat_step)
    south = north - lat_step

    return west, south, east, north


def _cell_polygon_latlng(aoi, shape, row, col):
    west, south, east, north = _cell_bounds(aoi, shape, row, col)
    return [
        [south, west],
        [south, east],
        [north, east],
        [north, west],
        [south, west],
    ]


def _cell_center(aoi, shape, row, col):
    west, south, east, north = _cell_bounds(aoi, shape, row, col)
    return (south + north) / 2.0, (west + east) / 2.0


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


def _darken(rgb, factor=0.78):
    return tuple(max(0, min(255, int(v * factor))) for v in rgb)


def _extract_cells(suitability, aoi, selected_row=None, selected_col=None):
    data = suitability.data.astype(np.float32)
    nodata = getattr(suitability, "nodata", -9999.0)
    rows, cols = data.shape

    cells = []

    for row in range(rows):
        for col in range(cols):
            score = float(data[row, col])
            if not np.isfinite(score) or score == nodata:
                continue

            rgb = _score_color_rgb(score)
            center_lat, center_lon = _cell_center(aoi, data.shape, row, col)
            label = suitability_badge(score)
            is_selected = row == selected_row and col == selected_col

            cells.append(
                {
                    "cell_name": f"Cell ({row+1}, {col+1})",
                    "row": row,
                    "col": col,
                    "score": score,
                    "score_text": _safe_pct(score),
                    "suitability": label,
                    "polygon": _cell_polygon_latlng(aoi, data.shape, row, col),
                    "lat": center_lat,
                    "lon": center_lon,
                    "fill_color": _rgb_to_hex(rgb),
                    "border_color": "#0070FF" if is_selected else _rgb_to_hex(_darken(rgb)),
                    "is_selected": is_selected,
                }
            )

    return cells


def _aoi_bounds_polygon(aoi):
    lon_min, lat_min, lon_max, lat_max = aoi
    return [
        [lat_min, lon_min],
        [lat_min, lon_max],
        [lat_max, lon_max],
        [lat_max, lon_min],
        [lat_min, lon_min],
    ]


def _find_existing_page(candidates=None, contains=None):
    pages_dir = Path("pages")
    if not pages_dir.exists():
        return None

    if candidates:
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate

    if contains:
        tokens = [t.lower() for t in contains]
        for file in sorted(pages_dir.glob("*.py")):
            lower = file.name.lower()
            if all(token in lower for token in tokens):
                return str(file).replace("\\", "/")

    return None


def _build_map_html(aoi, cells, selected_site, selected_cell_info, height=720):
    map_id = f"wahhaj_map_{uuid4().hex}"

    lon_min, lat_min, lon_max, lat_max = aoi
    bounds = [[lat_min, lon_min], [lat_max, lon_max]]

    polygons = [
        {
            "name": c["cell_name"],
            "score_text": c["score_text"],
            "suitability": c["suitability"],
            "fillColor": c["fill_color"],
            "borderColor": c["border_color"],
            "isSelected": c["is_selected"],
            "coords": c["polygon"],
        }
        for c in cells
    ]

    selected = {
        "name": selected_site["name"],
        "score_text": selected_site["score_text"],
        "suitability": selected_site["suitability"],
        "lat": selected_site["lat"],
        "lon": selected_site["lon"],
    }

    aoi_outline = _aoi_bounds_polygon(aoi)

    polygons_json = json.dumps(polygons, ensure_ascii=False)
    selected_json = json.dumps(selected, ensure_ascii=False)
    bounds_json = json.dumps(bounds)
    aoi_outline_json = json.dumps(aoi_outline)
    selected_cell_json = json.dumps(selected_cell_info, ensure_ascii=False)

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <link
        rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
        }}

        #{map_id} {{
            width: 100%;
            height: {height}px;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
        }}

        .leaflet-container {{
            font-family: Arial, sans-serif;
            background: #eaeaea;
        }}

        .leaflet-control-attribution {{
            font-size: 10px;
        }}

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
            height: 10px;
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

        .selected-label {{
            background: transparent;
            border: none;
        }}

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
        const polygons = {polygons_json};
        const selected = {selected_json};
        const bounds = {bounds_json};
        const aoiOutline = {aoi_outline_json};
        const selectedCell = {selected_cell_json};

        const map = L.map("{map_id}", {{
            zoomControl: true,
            scrollWheelZoom: true,
            preferCanvas: true
        }});

        const satellite = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
            {{
                attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and contributors",
                maxZoom: 19
            }}
        );

        const streets = L.tileLayer(
            "https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",
            {{
                attribution: "&copy; OpenStreetMap contributors",
                maxZoom: 19
            }}
        );

        satellite.addTo(map);

        const baseMaps = {{
            "Satellite": satellite,
            "Streets": streets
        }};

        L.control.layers(baseMaps, null, {{
            collapsed: true,
            position: "topright"
        }}).addTo(map);

        polygons.forEach((p) => {{
            const popupHtml = `
                <div class="wahhaj-popup-title">${{p.isSelected ? "Selected internal cell" : "Internal analysis cell"}}</div>
                <div class="wahhaj-popup-line">Score: ${{p.score_text}}</div>
                <div class="wahhaj-popup-line">Suitability: ${{p.suitability}}</div>
            `;

            L.polygon(p.coords, {{
                color: p.borderColor,
                weight: p.isSelected ? 2.6 : 1.2,
                fillColor: p.fillColor,
                fillOpacity: p.isSelected ? 0.58 : 0.48
            }})
            .bindPopup(popupHtml)
            .addTo(map);
        }});

        L.polygon(aoiOutline, {{
            color: "#0070FF",
            weight: 2.8,
            fillOpacity: 0
        }})
        .bindPopup(`
            <div class="wahhaj-popup-title">Selected analysis boundary</div>
            <div class="wahhaj-popup-line">This heatmap represents internal suitability distribution within the chosen AOI.</div>
        `)
        .addTo(map);

        const selectedIcon = L.divIcon({{
            className: "selected-label",
            html: `<div>${{selected.name}}</div>`,
            iconSize: [120, 26],
            iconAnchor: [60, -6]
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
            <div class="wahhaj-popup-line">Selected cell score: ${{selected.score_text}}</div>
            <div class="wahhaj-popup-line">Suitability: ${{selected.suitability}}</div>
        `)
        .addTo(map);

        L.marker([selected.lat, selected.lon], {{ icon: selectedIcon }}).addTo(map);

        map.fitBounds(bounds, {{ padding: [28, 28] }});

        const legend = L.control({{ position: "bottomleft" }});
        legend.onAdd = function() {{
            const div = L.DomUtil.create("div", "wahhaj-legend");
            div.innerHTML = `
                <div class="wahhaj-legend-title">AOI Suitability Scale</div>
                <div class="wahhaj-legend-bar"></div>
                <div class="wahhaj-legend-scale">
                    <span>Low</span>
                    <span>High</span>
                </div>
                <div class="wahhaj-legend-note">Blue outline = selected analysis boundary</div>
                <div class="wahhaj-legend-note">Blue marker = selected location center</div>
                <div class="wahhaj-legend-note">Blue-bordered cell = selected internal cell</div>
            `;
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
"""
    return html


# ── styles ────────────────────────────────────────────────────
st.markdown(
    """
<style>
.wrap{
    position:relative;
    z-index:2;
    padding-top:10px;
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
.map-panel{
    background:rgba(255,255,255,0.90);
    border-radius:24px;
    padding:20px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    margin-bottom:18px;
    border:1px solid rgba(255,255,255,0.6);
}
.map-title{
    font-family:'Capriola',sans-serif;
    font-size:18px;
    font-weight:700;
    color:#2E2E2E;
    margin-bottom:14px;
    display:flex;
    align-items:center;
    gap:8px;
}
.state-panel{
    background:rgba(255,255,255,0.88);
    border-radius:22px;
    padding:24px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    margin-bottom:18px;
    border:1px solid rgba(255,255,255,0.6);
}
.state-msg{
    font-family:'Capriola',sans-serif;
    font-size:14px;
    color:#5A5959;
    line-height:1.6;
}
.state-msg.error{
    color:#B91C1C;
}
.summary-grid{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:14px;
    margin-top:16px;
}
.summary-card{
    background:rgba(255,255,255,0.88);
    border-radius:18px;
    padding:16px 18px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    border:1px solid rgba(255,255,255,0.6);
}
.summary-label{
    font-family:'Capriola',sans-serif;
    font-size:12px;
    color:#7a7a7a;
    margin-bottom:8px;
}
.summary-value{
    font-family:'Capriola',sans-serif;
    font-size:18px;
    color:#1F3864;
    line-height:1.4;
}
.summary-sub{
    font-family:'Capriola',sans-serif;
    font-size:12px;
    color:#666;
    margin-top:6px;
    line-height:1.5;
}
.actions-wrap{
    margin-top:10px;
}
div.stButton>button{
    background:#0070FF;
    color:white;
    border:none;
    border-radius:10px;
    min-height:48px;
    font-family:'Capriola',sans-serif;
    font-size:15px;
    box-shadow:4px 5px 4px rgba(0,0,0,.14);
}
div.stButton>button:hover{
    background:#005fe0;
}
div.stButton>button:disabled{
    opacity:.55;
}
div[data-testid="stVerticalBlock"]{
    gap:.35rem;
}
@media (max-width: 900px){
    .summary-grid{
        grid-template-columns:1fr;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

render_top_home_button("pages/2_Home.py")

st.markdown('<div class="wrap">', unsafe_allow_html=True)
st.markdown('<div class="page-title">Suitability Heatmap</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">This map shows the internal suitability distribution within the single selected analysis boundary</div>',
    unsafe_allow_html=True,
)

# ── state ─────────────────────────────────────────────────────
run = st.session_state.get("analysis_run")
selected_site = st.session_state.get("selected_site_analysis", {})
sel_loc = st.session_state.get("selected_location", {})
aoi = st.session_state.get("aoi")

if run is None or getattr(run, "suitability", None) is None:
    st.markdown(
        "<div class='state-panel'>"
        f"<div class='state-msg error'>{ICO_WARN} No suitability result is available yet. Please run the site analysis first.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Back to Result", use_container_width=False):
        st.switch_page("pages/5_Analysis.py")
    st.stop()

if not aoi:
    st.markdown(
        "<div class='state-panel'>"
        f"<div class='state-msg error'>{ICO_WARN} Area data is missing from the current session.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

lat = selected_site.get("latitude", sel_loc.get("latitude"))
lon = selected_site.get("longitude", sel_loc.get("longitude"))
location_name = selected_site.get("location_name", sel_loc.get("location_name", ""))
site_display_name = selected_site.get(
    "site_display_name",
    _display_location_name(location_name, lat, lon),
)

if lat is None or lon is None:
    st.markdown(
        "<div class='state-panel'>"
        f"<div class='state-msg error'>{ICO_WARN} Selected site coordinates are unavailable.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

suitability = run.suitability
selected_row, selected_col = _point_to_grid_cell(lat, lon, aoi, suitability.data.shape)
cells = _extract_cells(
    suitability=suitability,
    aoi=aoi,
    selected_row=selected_row,
    selected_col=selected_col,
)

if not cells:
    st.markdown(
        "<div class='state-panel'>"
        f"<div class='state-msg error'>{ICO_WARN} No valid suitability cells were found for rendering.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

selected_score = selected_site.get("score")
if selected_score is None:
    selected_score = float(suitability.data[selected_row, selected_col])

selected_info = {
    "name": site_display_name,
    "score_text": _safe_pct(selected_score),
    "suitability": selected_site.get("label", suitability_badge(selected_score)),
    "lat": lat,
    "lon": lon,
}

lon_min, lat_min, lon_max, lat_max = aoi
selected_cell_info = {
    "row": selected_row + 1,
    "col": selected_col + 1,
    "score_text": _safe_pct(selected_score),
    "suitability": selected_info["suitability"],
}

# ── render real map ───────────────────────────────────────────
st.markdown(
    "<div class='map-panel'>"
    f"<div class='map-title'>{ICO_MAP} AOI Suitability Distribution</div>",
    unsafe_allow_html=True,
)

components.html(
    _build_map_html(
        aoi=aoi,
        cells=cells,
        selected_site=selected_info,
        selected_cell_info=selected_cell_info,
        height=720,
    ),
    height=740,
    scrolling=False,
)

st.markdown("</div>", unsafe_allow_html=True)

# ── summary ───────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="summary-grid">
        <div class="summary-card">
            <div class="summary-label">Selected Site</div>
            <div class="summary-value">{site_display_name}</div>
            <div class="summary-sub">The analysis shown on the map belongs to this one selected site boundary only.</div>
        </div>
        <div class="summary-card">
            <div class="summary-label">Selected Internal Cell</div>
            <div class="summary-value">{selected_cell_info["score_text"]}</div>
            <div class="summary-sub">
                Suitability: {selected_cell_info["suitability"]}<br>
                Grid position: row {selected_cell_info["row"]}, col {selected_cell_info["col"]}
            </div>
        </div>
        <div class="summary-card">
            <div class="summary-label">AOI Boundary</div>
            <div class="summary-value">({lat_min:.4f}, {lon_min:.4f}) → ({lat_max:.4f}, {lon_max:.4f})</div>
            <div class="summary-sub">Blue outline on the map represents the exact boundary chosen by the user.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── navigation ────────────────────────────────────────────────
report_page = _find_existing_page(
    candidates=[
        "pages/8_Final_Report.py",
        "pages/7_Final_Report.py",
        "pages/7_Report.py",
        "pages/7_Generate_Report.py",
        "pages/7_Final_Report_Generation.py",
    ],
    contains=["report"],
)

st.markdown("<div class='actions-wrap'></div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    if st.button("Back to Result", use_container_width=True):
        st.switch_page("pages/5_Analysis.py")
with c2:
    if st.button(
        "Generate Final Report",
        use_container_width=True,
        disabled=report_page is None,
    ):
        if report_page:
            st.switch_page(report_page)

st.markdown("</div>", unsafe_allow_html=True)
render_footer()