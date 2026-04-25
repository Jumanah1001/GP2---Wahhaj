"""
pages/7_Ranked_Results.py
==========================
Ranked Sites overview for all previously analysed user locations.

This page intentionally uses analysis_history as the source of truth,
not the latest run's candidate list.
"""

from __future__ import annotations

import json
from html import escape
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
    get_ranked_history,
    restore_analysis_history_entry,
)


st.set_page_config(page_title="Ranked Sites", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in"):
    st.switch_page("pages/1_Login.py")


def _coerce_score(value) -> float:
    try:
        score = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, score))


def _coerce_aoi(value):
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            lon_min, lat_min, lon_max, lat_max = [float(v) for v in value]
            if lon_min < lon_max and lat_min < lat_max:
                return (lon_min, lat_min, lon_max, lat_max)
        except Exception:
            return None
    return None


def _clean_entry(entry: dict, fallback_rank: int) -> dict | None:
    if not isinstance(entry, dict):
        return None

    lat = entry.get("lat")
    lon = entry.get("lon")
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except Exception:
        lat, lon = None, None

    score = _coerce_score(entry.get("selected_score", entry.get("top_score", 0.0)))
    label = str(entry.get("selected_label") or entry.get("recommendation") or "Review Required").strip()
    aoi = _coerce_aoi(entry.get("aoi"))

    if lat is None and lon is None and aoi is None:
        return None

    if (lat is None or lon is None) and aoi is not None:
        lon_min, lat_min, lon_max, lat_max = aoi
        lat = (lat_min + lat_max) / 2
        lon = (lon_min + lon_max) / 2

    location_name = str(entry.get("location_name") or "Unnamed Site").strip() or "Unnamed Site"
    analysed_at = str(entry.get("analysed_at") or "—")

    return {
        "rank": fallback_rank,
        "run_id": entry.get("run_id"),
        "location_name": location_name,
        "lat": lat,
        "lon": lon,
        "aoi": aoi,
        "score": score,
        "score_pct": f"{score * 100:.1f}%",
        "label": label,
        "analysed_at": analysed_at,
        "entry": entry,
    }


def _label_style(label: str) -> tuple[str, str]:
    # Ranked cards stay visually uniform; suitability color is already shown on the map.
    return "rgba(255,255,255,0.78)", "#4b5563"


def _score_color(score: float) -> str:
    # Keep card typography consistent instead of colouring each card differently.
    return "#1b5fcf"


def _score_fill(score: float) -> str:
    score = _coerce_score(score)
    if score >= 0.80:
        return "rgba(47, 158, 68, 0.18)"
    if score >= 0.60:
        return "rgba(240, 173, 0, 0.18)"
    if score >= 0.40:
        return "rgba(240, 140, 0, 0.18)"
    return "rgba(226, 83, 74, 0.18)"


def _aoi_polygon(aoi):
    lon_min, lat_min, lon_max, lat_max = aoi
    return [
        [lat_min, lon_min],
        [lat_min, lon_max],
        [lat_max, lon_max],
        [lat_max, lon_min],
        [lat_min, lon_min],
    ]


def _build_ranked_map_html(entries: list[dict], height: int = 760) -> str:
    map_id = f"wahhaj_ranked_map_{uuid4().hex}"

    serialised = []
    bounds = []
    for item in entries:
        aoi = item.get("aoi")
        if aoi is not None:
            bounds.extend([
                [aoi[1], aoi[0]],
                [aoi[3], aoi[2]],
            ])
            polygon = _aoi_polygon(aoi)
        else:
            polygon = None
            if item.get("lat") is not None and item.get("lon") is not None:
                bounds.append([item["lat"], item["lon"]])

        serialised.append(
            {
                "rank": item["rank"],
                "name": item["location_name"],
                "score": item["score"],
                "score_pct": item["score_pct"],
                "label": item["label"],
                "analysed_at": item["analysed_at"],
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "polygon": polygon,
                "stroke": _score_color(item["score"]),
                "fill": _score_fill(item["score"]),
            }
        )

    if not bounds:
        bounds = [[24.7136, 46.6753]]

    entries_json = json.dumps(serialised, ensure_ascii=False)
    bounds_json = json.dumps(bounds)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ margin:0; padding:0; background:transparent; }}
        #{map_id} {{
            width:100%;
            height:{height}px;
            border-radius:24px;
            overflow:hidden;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.4);
        }}
        .leaflet-container {{
            font-family: Arial, sans-serif;
            background:#edf1f4;
        }}
        .leaflet-control-attribution {{ font-size:10px; }}
        .wahhaj-popup {{ min-width: 180px; }}
        .wahhaj-popup .name {{
            font-size:15px;
            font-weight:700;
            color:#1f2937;
            margin-bottom:6px;
        }}
        .wahhaj-popup .meta {{
            font-size:12px;
            color:#5b6472;
            line-height:1.5;
        }}
        .wahhaj-popup .score {{
            font-size:22px;
            font-weight:800;
            margin:4px 0 6px;
        }}
        .wahhaj-legend {{
            background: rgba(255,255,255,0.96);
            border-radius: 16px;
            padding: 12px 14px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            line-height:1.35;
            min-width: 190px;
        }}
        .wahhaj-legend-title {{
            font-size: 13px;
            font-weight: 700;
            color: #15396b;
            margin-bottom: 8px;
        }}
        .wahhaj-legend-row {{
            display:flex;
            align-items:center;
            gap:8px;
            font-size:12px;
            color:#374151;
            margin-top:7px;
        }}
        .wahhaj-legend-dot {{
            width: 11px;
            height: 11px;
            border-radius: 999px;
            display:inline-block;
            border:1px solid rgba(0,0,0,0.16);
        }}
    </style>
</head>
<body>
    <div id="{map_id}"></div>
    <script>
        const rankedSites = {entries_json};
        const boundsData = {bounds_json};

        const map = L.map('{map_id}', {{ zoomControl: true, scrollWheelZoom: false }});
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }}).addTo(map);

        const bounds = L.latLngBounds(boundsData);
        map.fitBounds(bounds.pad(0.18));

        rankedSites.forEach((site) => {{
            const popup = `
                <div class="wahhaj-popup">
                    <div class="name">#${{site.rank}} · ${{site.name}}</div>
                    <div class="score" style="color:${{site.stroke}};">${{site.score_pct}}</div>
                    <div class="meta">${{site.label}}</div>
                    <div class="meta">${{site.analysed_at}}</div>
                </div>`;

            if (site.polygon && site.polygon.length) {{
                L.polygon(site.polygon, {{
                    color: site.stroke,
                    weight: 2,
                    opacity: 0.95,
                    dashArray: '6,6',
                    fillColor: site.fill,
                    fillOpacity: 0.55,
                }}).addTo(map).bindPopup(popup);
            }}

            if (site.lat !== null && site.lon !== null) {{
                L.circleMarker([site.lat, site.lon], {{
                    radius: 7,
                    color: '#ffffff',
                    weight: 2,
                    fillColor: site.stroke,
                    fillOpacity: 1,
                }}).addTo(map).bindPopup(popup);
            }}
        }});

        const legend = L.control({{ position: 'bottomleft' }});
        legend.onAdd = function () {{
            const div = L.DomUtil.create('div', 'wahhaj-legend');
            div.innerHTML = `
                <div class="wahhaj-legend-title">Suitability Levels</div>
                <div class="wahhaj-legend-row"><span class="wahhaj-legend-dot" style="background:#2f9e44"></span> High</div>
                <div class="wahhaj-legend-row"><span class="wahhaj-legend-dot" style="background:#f0ad00"></span> Medium</div>
                <div class="wahhaj-legend-row"><span class="wahhaj-legend-dot" style="background:#e2534a"></span> Low</div>
                <div class="wahhaj-legend-row" style="margin-top:10px;color:#667085;">AOI areas show each analysed site coverage.</div>
            `;
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
"""


prepared = get_ranked_history()
site_count = len(prepared)
latest_location = prepared[0]["location_name"] if prepared else "—"

st.markdown(
    """
    <style>
    .ranked-wrap {
        position: relative;
        z-index: 2;
        padding-top: 8px;
    }
    .ranked-title {
        font-family: 'Capriola', sans-serif;
        font-size: clamp(34px, 3vw, 44px);
        color: #1a1a1a;
        text-align: center;
        margin-bottom: 8px;
        line-height: 1.1;
    }
    .ranked-subtitle {
        font-family: 'Capriola', sans-serif;
        font-size: 14px;
        color: #5E5B5B;
        text-align: center;
        margin-bottom: 18px;
    }
    div[class*="st-key-ranked_shell"] {
        background: rgba(255,255,255,0.56);
        border: 1px solid rgba(232,236,241,0.85);
        border-radius: 26px;
        backdrop-filter: blur(14px);
        box-shadow: 0 10px 32px rgba(15,23,42,0.05);
        padding: 22px 22px 18px 22px;
        margin-top: 8px;
    }
    .ranked-shell-head {
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:16px;
        margin-bottom: 14px;
    }
    .ranked-shell-title {
        font-family:'Capriola',sans-serif;
        font-size: 24px;
        color:#1a1a1a;
        line-height:1.1;
        margin-bottom: 6px;
    }
    .ranked-shell-sub {
        font-size: 13px;
        color:#5e5b5b;
        line-height:1.6;
    }
    .ranked-chip-row {
        display:flex;
        gap:10px;
        flex-wrap:wrap;
        margin-top:8px;
    }
    .ranked-chip {
        display:inline-flex;
        align-items:center;
        gap:8px;
        background:#f4f6f8;
        border:1px solid #e6eaee;
        border-radius:999px;
        padding:7px 12px;
        font-size:12px;
        color:#425466;
        font-weight:700;
    }
    .panel-title {
        font-family:'Capriola',sans-serif;
        font-size:18px;
        color:#1a1a1a;
        margin-bottom:8px;
    }
    .panel-sub {
        font-size:12px;
        color:#6b7280;
        margin-bottom:10px;
    }
    .map-panel {
        background: rgba(255,255,255,0.34);
        border: 1px solid rgba(232,236,241,0.85);
        backdrop-filter: blur(10px);
        border-radius: 24px;
        padding: 14px;
        min-height: 100%;
    }
    div[class*="st-key-ranked_list_shell"] {
        background: rgba(255,255,255,0.34);
        border: 1px solid rgba(232,236,241,0.85);
        backdrop-filter: blur(10px);
        border-radius: 24px;
        padding: 14px 14px 8px 14px;
        height: 100%;
    }
    .empty-state {
        background: rgba(255,255,255,0.52);
        border: 1px solid rgba(232,236,241,0.85);
        border-radius: 24px;
        padding: 28px;
        text-align: center;
        color:#475467;
        line-height:1.8;
        box-shadow: 0 6px 22px rgba(0,0,0,0.06);
    }
    div[class*="st-key-site_card_"] {
        background: rgba(255,255,255,0.82);
        border: 1px solid rgba(232,236,241,0.95);
        border-radius: 20px;
        padding: 14px 14px 12px 14px;
        box-shadow: 0 4px 14px rgba(15,23,42,0.04);
        margin-bottom: 12px;
    }
    div[class*="st-key-site_card_0"] {
        border-color: rgba(232,236,241,0.95);
        box-shadow: 0 4px 14px rgba(15,23,42,0.04);
    }
    .site-rank-row {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        margin-bottom:8px;
    }
    .site-rank {
        font-size:14px;
        font-weight:800;
        color:#0f172a;
        letter-spacing:0.02em;
    }
    .site-name {
        font-family:'Capriola',sans-serif;
        font-size:18px;
        color:#1a1a1a;
        margin-bottom:8px;
        line-height:1.35;
    }
    .site-score {
        font-size:28px;
        font-weight:800;
        line-height:1;
        margin-bottom:10px;
    }
    .site-meta {
        font-size:12px;
        color:#667085;
        line-height:1.65;
    }
    .site-badge {
        display:inline-flex;
        align-items:center;
        justify-content:center;
        padding:6px 10px;
        border-radius:999px;
        font-size:11px;
        font-weight:800;
        white-space:nowrap;
    }
    div[class*="st-key-site_card_"] .stButton > button {
        border-radius: 14px !important;
        min-height: 38px !important;
        font-size: 13px !important;
        font-weight: 700 !important;
    }
    .foot-nav-space { margin-top: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


render_top_home_button()

st.markdown('<div class="ranked-wrap">', unsafe_allow_html=True)
st.markdown('<div class="ranked-title">Ranked Sites</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ranked-subtitle">Compare all previously analysed locations in one unified suitability view.</div>',
    unsafe_allow_html=True,
)

if not prepared:
    st.markdown(
        """
        <div class="empty-state">
            <div style="font-family:'Capriola',sans-serif;font-size:22px;color:#1a1a1a;margin-bottom:8px;">No saved sites yet</div>
            <div>Your ranked sites page will appear here after you complete and save at least one site analysis.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        if st.button("← Back to Heatmap", use_container_width=True):
            st.switch_page("pages/6_Suitability_Heatmap.py")
    with bottom_right:
        if st.button("＋ Add New Site", type="primary", use_container_width=True):
            st.switch_page("pages/3_Choose_Location.py")
    render_footer()
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()


with st.container(key="ranked_shell"):
    head_left, head_right = st.columns([5.2, 1.5], gap="large")
    with head_left:
        st.markdown(
            f"""
            <div class="ranked-shell-head">
                <div>
                    <div class="ranked-shell-title">Aggregated Suitability Map & Rankings</div>
                    <div class="ranked-shell-sub">Every saved analysis for this user is collected here, ranked by the final site suitability score and shown together on one shared map.</div>
                    <div class="ranked-chip-row">
                        <span class="ranked-chip">{site_count} saved site{'s' if site_count != 1 else ''}</span>
                        <span class="ranked-chip">Top ranked: {escape(latest_location)}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with head_right:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        if st.button("＋ Add New Site", key="add_new_site_top", use_container_width=True):
            st.switch_page("pages/3_Choose_Location.py")

    left_col, right_col = st.columns([1.18, 0.82], gap="large")

    with left_col:
        st.markdown('<div class="map-panel">', unsafe_allow_html=True)
        st.markdown('<div class="panel-title">Aggregated Suitability Map</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="panel-sub">Colored AOI areas show the coverage of each analysed site. The small center marker indicates the selected location.</div>',
            unsafe_allow_html=True,
        )
        components.html(_build_ranked_map_html(prepared, height=760), height=760)
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        with st.container(key="ranked_list_shell"):
            st.markdown('<div class="panel-title">Ranked Sites</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="panel-sub">Sorted by the saved final suitability score of each analysed location.</div>',
                unsafe_allow_html=True,
            )

            for idx, item in enumerate(prepared):
                badge_bg, badge_fg = _label_style(item["label"])
                score_color = _score_color(item["score"])
                lat_txt = f'{item["lat"]:.4f}°N' if item.get("lat") is not None else '—'
                lon_txt = f'{item["lon"]:.4f}°E' if item.get("lon") is not None else '—'

                with st.container(key=f"site_card_{idx}"):
                    st.markdown(
                        f"""
                        <div class="site-rank-row">
                            <div class="site-rank">#{item['rank']}</div>
                            <span class="site-badge" style="background:{badge_bg};color:{badge_fg};">{escape(item['label'])}</span>
                        </div>
                        <div class="site-name">{escape(item['location_name'])}</div>
                        <div class="site-score" style="color:{score_color};">{item['score_pct']}</div>
                        <div class="site-meta">
                            <div><b>Coordinates:</b> {lat_txt}, {lon_txt}</div>
                            <div><b>Analysed:</b> {escape(item['analysed_at'])}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        "Open Final Report",
                        key=f"open_saved_report_{item.get('run_id', idx)}",
                        use_container_width=True,
                    ):
                        ok = restore_analysis_history_entry(item["entry"])
                        if ok:
                            st.switch_page("pages/8_Final_Report.py")
                        else:
                            st.warning("This saved entry cannot be reopened in the current session yet.")

st.markdown('<div class="foot-nav-space"></div>', unsafe_allow_html=True)
nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("Back to Heatmap", use_container_width=True):
        st.switch_page("pages/6_Suitability_Heatmap.py")
with nav_right:
    if st.button("Open Current Final Report", type="primary", use_container_width=True):
        st.switch_page("pages/8_Final_Report.py")

render_footer()
st.markdown('</div>', unsafe_allow_html=True)
