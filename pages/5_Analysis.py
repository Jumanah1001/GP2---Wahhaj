"""
5_Analysis.py — WAHHAJ Selected Site Result
===========================================
User-facing result page:
- Shows only what matters to the user
- Analyses the selected site
- Hides backend / technical layer details
- Stores selected-site result for later map/report pages

Fixes applied in this version
------------------------------
1. top_k_sites=0, min_site_score=1.0  ->  top_k_sites=10, min_site_score=0.0
   The original values guaranteed zero candidates would ever be found
   because no score can exceed 1.0 in a [0,1] range. This made
   7_Ranked_Results.py always show "No ranked results found."
   Now up to 10 candidates are extracted at any score >= 0.0.

2. _find_existing_page() candidate list updated:
   Added "pages/8_Final_Report.py" as the first candidate.
   The old list only contained names like "pages/7_Final_Report.py"
   which do not exist, permanently disabling the Generate Report button.

3. AOI half-degree fixed:
   _aoi_from_selected_location() used ±0.5° (55 km square).
   Changed to ±0.1° to match ui_helpers.save_selected_location().
   This ensures the heatmap AOI is consistent with the chosen location.
"""

import time
from datetime import datetime
from pathlib import Path
from html import escape

import streamlit as st
from ui_helpers import (
    get_image_records,
    get_uploaded_image_cache,
    init_state,
    apply_global_style,
    render_bg,
    render_footer,
    render_top_home_button,
    set_analysis_state,
    set_dataset_state,
)

st.set_page_config(page_title="Selected Site Result - WAHHAJ", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in"):
    st.switch_page("pages/1_Login.py")


# ── inline SVG icons ──────────────────────────────────────────
def _i(d, sz=15, c="currentColor", ep=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{sz}" height="{sz}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:middle;flex-shrink:0;">'
        f'<path d="{d}"/>{ep}</svg>'
    )


ICO_LOC = _i(
    "M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z", c="#0070FF"
) + _i("M12 10a1 1 0 1 0 0-2 1 1 0 1 0 0 2", c="#0070FF")

ICO_IMG = _i(
    "M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z",
    c="#0070FF",
    ep='<circle cx="12" cy="13" r="4" stroke="#0070FF" stroke-width="2"/>',
)
ICO_OK = _i("M20 6L9 17l-5-5", c="#22C55E", sz=14)
ICO_WARN = _i(
    "M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
    c="#E2534A",
    ep='<line x1="12" y1="9" x2="12" y2="13" stroke="#E2534A" stroke-width="2"/><line x1="12" y1="17" x2="12.01" y2="17" stroke="#E2534A" stroke-width="2"/>',
)
ICO_SUN = _i(
    "M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42",
    c="#F9B233",
    ep='<circle cx="12" cy="12" r="5" stroke="#F9B233" stroke-width="2"/>',
)
ICO_SLOPE = _i("M3 20l7-10 4 5 3-4 4 9", c="#22C55E")
ICO_TEMP = _i(
    "M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z",
    c="#E2534A",
)
ICO_TIME = _i(
    "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z",
    c="#4FC3F7",
    ep='<polyline points="12 6 12 12 16 14" stroke="#4FC3F7" stroke-width="2"/>',
)
ICO_DATA = _i(
    "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
    c="#0070FF",
)
ICO_AI = _i(
    "M12 2l1.8 3.65L18 7.1l-3 2.92.71 4.13L12 12.3l-3.71 1.85.71-4.13-3-2.92 4.2-1.45L12 2z",
    c="#0070FF",
)


WEIGHTS = {
    "ghi": 0.30,
    "slope": 0.22,
    "sunshine": 0.18,
    "obstacle": 0.13,
    "lst": 0.10,
    "elevation": 0.07,
}

INVERTED = {"slope", "lst", "obstacle"}

LAYER_META = {
    "ghi": {"icon": ICO_SUN, "title": "Solar Radiation"},
    "sunshine": {"icon": ICO_TIME, "title": "Sunlight Hours"},
    "slope": {"icon": ICO_SLOPE, "title": "Terrain Slope"},
    "elevation": {"icon": ICO_DATA, "title": "Elevation"},
    "lst": {"icon": ICO_TEMP, "title": "Surface Temperature"},
    "obstacle": {"icon": ICO_DATA, "title": "Obstacle Conditions"},
}


def suitability_badge(score):
    s = score * 100
    if s >= 75:
        return "Highly Suitable", "b-high"
    if s >= 55:
        return "Suitable", "b-suit"
    if s >= 35:
        return "Moderately Suitable", "b-mod"
    return "Not Suitable", "b-low"


def _safe_pct(score):
    return f"{score * 100:.1f}%" if score is not None else "—"


def _aoi_from_selected_location(lat, lon):
    # Fallback only: use a small square around the selected point when no
    # explicit AOI was saved from the location-selection page.
    half = 0.1
    return (
        round(lon - half, 4),
        round(lat - half, 4),
        round(lon + half, 4),
        round(lat + half, 4),
    )


def _is_valid_aoi(aoi):
    return isinstance(aoi, (list, tuple)) and len(aoi) == 4


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


def _denormalize_value(norm_val, meta):
    n_min = meta.get("norm_min")
    n_max = meta.get("norm_max")
    if n_min is None or n_max is None:
        return norm_val
    return (norm_val * (n_max - n_min)) + n_min


def _format_raw_value(layer_name, raw_value, unit):
    if raw_value is None:
        return "No data"

    if layer_name == "obstacle":
        return f"{raw_value * 100:.1f}%"
    if layer_name == "slope":
        return f"{raw_value:.1f}°"
    if layer_name == "sunshine":
        return f"{raw_value:.1f} {unit or 'hours/day'}"
    if layer_name == "ghi":
        return f"{raw_value:.1f} {unit or 'MJ/m²/day'}"
    if layer_name == "lst":
        return f"{raw_value:.1f} {unit or '°C'}"
    if layer_name == "elevation":
        return f"{raw_value:.1f} {unit or 'm'}"
    return f"{raw_value:.2f} {unit}".strip()


def _get_backend_image_ready():
    uploaded_items = get_uploaded_image_cache()
    if not uploaded_items:
        uploaded_items = st.session_state.get("uploaded_images", [])
    if not uploaded_items:
        return False
    for item in uploaded_items:
        if isinstance(item, dict) and item.get("db") is not None:
            return True
    return False


def _get_backend_images():
    uploaded_items = get_uploaded_image_cache()
    if not uploaded_items:
        uploaded_items = st.session_state.get("uploaded_images", [])
    db_list = [
        item.get("db")
        for item in uploaded_items
        if isinstance(item, dict) and item.get("db") is not None
    ]
    return [
        img
        for db in db_list
        for img in (getattr(db, "images", None) or [])
    ]


def _uploaded_image_count() -> int:
    records = get_image_records()
    if records:
        return len(records)
    uploaded_items = get_uploaded_image_cache()
    return len(uploaded_items or [])


def _build_selected_site_breakdown(extractor, row, col):
    items = []
    order = ["ghi", "sunshine", "slope", "obstacle", "lst", "elevation"]

    for name in order:
        raster = extractor.layers.get(name)
        if raster is None:
            continue

        meta = raster.metadata or {}
        unit = meta.get("unit", "")
        norm_val = float(raster.data[row, col])

        if norm_val == raster.nodata:
            continue

        suitability_component = 1.0 - norm_val if name in INVERTED else norm_val
        suitability_component = max(0.0, min(1.0, suitability_component))
        contribution_pct = suitability_component * WEIGHTS[name] * 100.0

        raw_value = _denormalize_value(norm_val, meta)
        raw_label = _format_raw_value(name, raw_value, unit)

        items.append(
            {
                "name": name,
                "title": LAYER_META[name]["title"],
                "icon": LAYER_META[name]["icon"],
                "weight": WEIGHTS[name],
                "raw_label": raw_label,
                "suitability_component": suitability_component,
                "contribution_pct": contribution_pct,
            }
        )

    return items


def _reason_text(item):
    score = item["suitability_component"]
    name = item["name"]

    if name == "ghi":
        if score >= 0.75:
            return "Strong solar radiation levels"
        if score >= 0.55:
            return "Good solar radiation conditions"
        return "Moderate solar radiation conditions"

    if name == "sunshine":
        if score >= 0.75:
            return "Extended daily sunlight hours"
        if score >= 0.55:
            return "Good daily sunlight hours"
        return "Moderate daily sunlight hours"

    if name == "slope":
        if score >= 0.75:
            return "Flat terrain conditions"
        if score >= 0.55:
            return "Generally manageable terrain"
        return "Moderate terrain slope"

    if name == "obstacle":
        if score >= 0.75:
            return "Relatively open site conditions"
        if score >= 0.55:
            return "Moderate site constraints"
        return "Visible site constraints"

    if name == "lst":
        if score >= 0.75:
            return "Suitable surface temperature conditions"
        if score >= 0.55:
            return "Generally suitable temperature conditions"
        return "Moderate temperature conditions"

    if name == "elevation":
        if score >= 0.75:
            return "Favorable elevation profile"
        if score >= 0.55:
            return "Acceptable elevation profile"
        return "Moderate elevation profile"

    return item["title"]


def _top_reason_items(factor_items, k=3):
    ranked = sorted(
        factor_items,
        key=lambda x: x["contribution_pct"],
        reverse=True,
    )
    return ranked[:k]


def _display_location_name(location_name, lat, lon):
    name = (location_name or "").strip()
    if name:
        return name
    return "Selected Site"


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


def _get_ai_image_assessment(extractor, row, col):
    if not extractor or not getattr(extractor, "layers", None):
        return "Pending AI model result"

    obstacle = extractor.layers.get("obstacle")
    if obstacle is None:
        return "Pending AI model result"

    meta = obstacle.metadata or {}
    if str(meta.get("source", "")).lower() != "aimodel":
        return "Pending AI model result"

    norm_val = float(obstacle.data[row, col])
    if norm_val == obstacle.nodata:
        return "Pending AI model result"

    raw_val = _denormalize_value(norm_val, meta)
    raw_val = max(0.0, min(1.0, float(raw_val)))

    if raw_val <= 0.20:
        return "Open Site Conditions"
    if raw_val <= 0.45:
        return "Moderate Site Constraints"
    return "High Obstacle Presence"


def _save_selected_site_analysis(
    site_display_name,
    location_name,
    lat,
    lon,
    img_name,
    score,
    label,
    ai_assessment,
    factor_items,
    reason_items,
    run_id=None,
    analysis_id=None,
):
    st.session_state["selected_site_analysis"] = {
        "site_display_name": site_display_name,
        "location_name": location_name,
        "latitude": lat,
        "longitude": lon,
        "image_name": img_name,
        "score": score,
        "score_text": _safe_pct(score),
        "label": label,
        "run_id": run_id,
        "analysis_id": analysis_id,
        "ai_assessment": ai_assessment,
        "analysed_at": datetime.now().isoformat(),
        "reasons": [
            {
                "name": item["name"],
                "title": item["title"],
                "reason": _reason_text(item),
            }
            for item in reason_items
        ],
        "factors": [
            {
                "name": item["name"],
                "title": item["title"],
                "raw_label": item["raw_label"],
                "contribution_pct": round(item["contribution_pct"], 2),
            }
            for item in factor_items
        ],
    }


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
    margin-bottom:24px;
    text-align:center;
}

.summary-row{
    display:flex;
    gap:16px;
    flex-wrap:wrap;
    margin-bottom:18px;
}
.summary-card{
    flex:1;
    min-width:240px;
    background:rgba(255,255,255,0.92);
    border-radius:22px;
    padding:20px 22px 18px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    border:1px solid rgba(220,220,220,0.6);
}
.summary-label{
    font-family:'Capriola',sans-serif;
    font-size:11px;
    color:#666;
    text-transform:uppercase;
    letter-spacing:.06em;
    display:flex;
    align-items:center;
    gap:7px;
    margin-bottom:10px;
}
.summary-main{
    font-family:'Capriola',sans-serif;
    font-size:20px;
    color:#1F3864;
    font-weight:700;
    line-height:1.45;
    margin-bottom:6px;
    word-break:break-word;
}
.summary-sub{
    font-family:'Capriola',sans-serif;
    font-size:12px;
    color:#555;
    line-height:1.45;
}

.result-panel{
    background:rgba(255,255,255,0.92);
    border-radius:24px;
    padding:28px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    margin-bottom:18px;
    border:1px solid rgba(220,220,220,0.6);
}
.result-grid{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:28px;
    align-items:stretch;
}
.result-col{
    min-width:0;
}
.result-col.right{
    border-left:1px solid #E0E0E0;
    padding-left:28px;
}
.result-label{
    font-family:'Capriola',sans-serif;
    font-size:12px;
    color:#666;
    text-transform:uppercase;
    letter-spacing:.06em;
    margin-bottom:12px;
}
.score-value{
    font-family:'Capriola',sans-serif;
    font-size:74px;
    color:#0070FF;
    font-weight:700;
    line-height:1;
    margin-bottom:14px;
}
.score-sub{
    font-family:'Capriola',sans-serif;
    font-size:12px;
    color:#666;
    text-transform:uppercase;
    letter-spacing:.06em;
}
.badge{
    font-family:'Capriola',sans-serif;
    font-size:12px;
    padding:7px 14px;
    border-radius:999px;
    display:inline-block;
    width:fit-content;
    margin-top:16px;
    font-weight:700;
}
.b-high{background:#DCFCE7;color:#166534;}
.b-suit{background:#FEF9C3;color:#713f12;}
.b-mod{background:#FEF3C7;color:#92400E;}
.b-low{background:#FEE2E2;color:#991B1B;}

.ai-label{
    font-family:'Capriola',sans-serif;
    font-size:11px;
    color:#666;
    text-transform:uppercase;
    letter-spacing:.05em;
    display:flex;
    align-items:center;
    gap:6px;
    margin-bottom:12px;
}
.ai-value{
    font-family:'Capriola',sans-serif;
    font-size:28px;
    color:#1F3864;
    font-weight:700;
    line-height:1.35;
    word-break:break-word;
}

.factors-panel{
    background:rgba(255,255,255,0.92);
    border-radius:24px;
    padding:24px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    margin-bottom:18px;
    border:1px solid rgba(220,220,220,0.6);
}
.panel-title{
    font-family:'Capriola',sans-serif;
    font-size:18px;
    font-weight:700;
    color:#1a1a1a;
    margin-bottom:10px;
}
.reason-list{
    display:flex;
    flex-direction:column;
}
.reason-row{
    display:flex;
    align-items:flex-start;
    gap:12px;
    padding:14px 0;
    border-bottom:1px solid #EFEFEF;
}
.reason-row:last-child{
    border-bottom:none;
    padding-bottom:0;
}
.reason-icon{
    width:22px;
    min-width:22px;
    margin-top:1px;
}
.reason-content{
    min-width:0;
}
.reason-factor{
    font-family:'Capriola',sans-serif;
    font-size:11px;
    color:#666;
    text-transform:uppercase;
    letter-spacing:.05em;
    margin-bottom:4px;
}
.reason-text{
    font-family:'Capriola',sans-serif;
    font-size:17px;
    color:#1F3864;
    font-weight:700;
    line-height:1.35;
}

.cta-wrap{
    margin-top:14px;
}
.state-panel{
    background:rgba(255,255,255,0.92);
    border-radius:22px;
    padding:24px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    margin-bottom:18px;
    border:1px solid rgba(220,220,220,0.6);
}
.state-msg{
    font-family:'Capriola',sans-serif;
    font-size:14px;
    color:#333;
    line-height:1.6;
}
.state-msg.error{
    color:#991B1B;
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
    .result-grid{
        grid-template-columns:1fr;
        gap:18px;
    }
    .result-col.right{
        border-left:none;
        border-top:1px solid #E0E0E0;
        padding-left:0;
        padding-top:18px;
    }
    .score-value{
        font-size:56px;
    }
    .ai-value{
        font-size:22px;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ═══════════════════════════════════════════════════════════════
render_top_home_button("pages/2_Home.py")

st.markdown('<div class="wrap">', unsafe_allow_html=True)
st.markdown('<div class="page-title">Selected Site Result</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Review the suitability result for your selected site</div>',
    unsafe_allow_html=True,
)

# ── session state ─────────────────────────────────────────────
sel_loc = st.session_state.get("selected_location", {})
lat = sel_loc.get("latitude")
lon = sel_loc.get("longitude")
location_name = sel_loc.get("location_name", "")
img_name = st.session_state.get("uploaded_image_name", "")

has_loc = lat is not None and lon is not None
has_img = _get_backend_image_ready()

saved_aoi = st.session_state.get("aoi")
if _is_valid_aoi(saved_aoi):
    aoi = tuple(saved_aoi)
elif has_loc:
    aoi = _aoi_from_selected_location(lat, lon)
    st.session_state["aoi"] = aoi
else:
    aoi = None

site_display_name = _display_location_name(location_name, lat, lon)
coords_text = f"{lat:.4f}N, {lon:.4f}E" if has_loc else "Coordinates unavailable"

image_count = _uploaded_image_count()
img_main = f"{image_count} image uploaded" if image_count == 1 else (
    f"{image_count} images uploaded" if has_img else "No image uploaded"
)
img_sub  = img_name if img_name else "Upload a site image to continue"

# ── top summary ───────────────────────────────────────────────
st.markdown(
    "<div class='summary-row'>"
    f"<div class='summary-card'>"
    f"<div class='summary-label'>{ICO_LOC} Selected Location</div>"
    f"<div class='summary-main'>{escape(site_display_name)}</div>"
    f"<div class='summary-sub'>{escape(coords_text)}</div>"
    "</div>"
    f"<div class='summary-card'>"
    f"<div class='summary-label'>{ICO_IMG} Uploaded Image</div>"
    f"<div class='summary-main'>{escape(img_main)}</div>"
    f"<div class='summary-sub'>{escape(img_sub)}</div>"
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)

# ── run / results ─────────────────────────────────────────────
run_result = st.session_state.get("analysis_run")
all_ready = has_loc and has_img

if run_result is None:
    if not all_ready:
        missing = []
        if not has_loc:
            missing.append("selected location")
        if not has_img:
            missing.append("uploaded image")

        st.markdown(
            "<div class='state-panel'>"
            f"<div class='state-msg error'>{ICO_WARN} Please provide the {' and '.join(missing)} before continuing.</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            if st.button("Back to Location", use_container_width=True):
                st.switch_page("pages/3_Choose_Location.py")
        with c2:
            if st.button("Back to Upload", use_container_width=True):
                st.switch_page("pages/4_Upload_Image.py")
    else:
        st.markdown(
            "<div class='state-panel'>"
            f"<div class='state-msg'>{ICO_OK} Preparing your site result...</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        progress = st.progress(0)
        try:
            progress.progress(8, "Initialising analysis...")
            from Wahhaj.ExternalDataSourceAdapter import ExternalDataSourceAdapter
            from Wahhaj.FeatureExtractor import FeatureExtractor, Dataset
            from Wahhaj.AHPModel import AHPModel
            from Wahhaj.AnalysisRun import AnalysisRun

            now = datetime.now()

            progress.progress(22, "Preparing site data...")
            backend_images = _get_backend_images()

            dataset = Dataset(
                name="wahhaj_selected_site_analysis",
                aoi=aoi,
                images=backend_images,
                start_date=st.session_state.get("analysis_start_date", now),
                end_date=st.session_state.get("analysis_end_date", now),
            )
            dataset_ref = set_dataset_state(
                dataset,
                status="processing",
                source="session",
                image_count=len(backend_images),
                aoi=aoi,
                name=dataset.name,
                created_at=now,
                updated_at=now,
            )

            progress.progress(40, "Loading analysis pipeline...")
            adapter   = ExternalDataSourceAdapter()
            extractor = FeatureExtractor(adapter=adapter)
            ahp       = AHPModel()

            # FIX: was top_k_sites=0, min_site_score=1.0 — guaranteed zero candidates.
            # Scores are in [0, 1]; min_site_score=1.0 means nothing qualifies.
            # Now uses top_k_sites=10, min_site_score=0.0 to collect all top candidates.
            run = AnalysisRun(
                ahp_model         = ahp,
                feature_extractor = extractor,
                top_k_sites       = 10,
                min_site_score    = 0.0,
            )
            set_analysis_state(
                run,
                status="running",
                dataset_id=dataset_ref.get("dataset_id"),
                location_name=location_name,
                created_at=now,
                updated_at=now,
            )

            progress.progress(68, "Running site analysis...")
            run.execute(dataset)

            progress.progress(92, "Saving result...")
            completed_at = datetime.now()
            set_dataset_state(
                dataset,
                status="ready",
                source="session",
                image_count=len(backend_images),
                aoi=aoi,
                name=dataset.name,
                created_at=dataset_ref.get("created_at"),
                updated_at=completed_at,
            )
            st.session_state["extractor"] = extractor
            set_analysis_state(
                run,
                status="completed",
                dataset_id=(st.session_state.get("dataset_ref") or {}).get("dataset_id"),
                location_name=location_name,
                created_at=now,
                updated_at=completed_at,
            )

            progress.progress(100, "Done")
            time.sleep(0.35)
            st.rerun()

        except Exception as exc:
            progress.empty()
            failed_at = datetime.now()
            set_analysis_state(
                st.session_state.get("_analysis_run_cache"),
                status="failed",
                dataset_id=(st.session_state.get("dataset_ref") or {}).get("dataset_id"),
                location_name=location_name,
                created_at=(st.session_state.get("analysis_ref") or {}).get("created_at"),
                updated_at=failed_at,
            )
            st.markdown(
                "<div class='state-panel'>"
                f"<div class='state-msg error'>{ICO_WARN} Analysis failed. Please try again.</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            with st.expander("Error details"):
                st.exception(exc)

else:
    run       = run_result
    extractor = st.session_state.get("extractor")

    selected_score  = None
    selected_label  = "—"
    badge_class     = ""
    ai_assessment   = "Pending AI model result"
    factor_items    = []
    reason_items    = []

    if run and getattr(run, "suitability", None) is not None and has_loc:
        suit = run.suitability
        row, col = _point_to_grid_cell(lat, lon, aoi, suit.data.shape)
        selected_score = float(suit.data[row, col])
        selected_label, badge_class = suitability_badge(selected_score)

        if extractor and getattr(extractor, "layers", None):
            factor_items  = _build_selected_site_breakdown(extractor, row, col)
            reason_items  = _top_reason_items(factor_items, k=3)
            ai_assessment = _get_ai_image_assessment(extractor, row, col)

        _save_selected_site_analysis(
            site_display_name = site_display_name,
            location_name     = location_name,
            lat               = lat,
            lon               = lon,
            img_name          = img_name,
            score             = selected_score,
            label             = selected_label,
            ai_assessment     = ai_assessment,
            factor_items      = factor_items,
            reason_items      = reason_items,
            run_id            = getattr(run, "runId", None),
            analysis_id       = (st.session_state.get("analysis_ref") or {}).get("analysis_id"),
        )

    # main result panel
    result_html = (
        "<div class='result-panel'>"
        "<div class='result-grid'>"
        "<div class='result-col left'>"
        "<div class='result-label'>Final Result</div>"
        f"<div class='score-value'>{escape(_safe_pct(selected_score))}</div>"
        "<div class='score-sub'>Final Score</div>"
        f"<span class='badge {badge_class}'>{escape(selected_label)}</span>"
        "</div>"
        "<div class='result-col right'>"
        f"<div class='ai-label'>{ICO_AI} AI Image Assessment</div>"
        f"<div class='ai-value'>{escape(ai_assessment)}</div>"
        "</div>"
        "</div>"
        "</div>"
    )
    st.markdown(result_html, unsafe_allow_html=True)

    # factors panel
    if reason_items:
        rows_html = ""
        for item in reason_items:
            rows_html += (
                "<div class='reason-row'>"
                f"<div class='reason-icon'>{item['icon']}</div>"
                "<div class='reason-content'>"
                f"<div class='reason-factor'>{escape(item['title'])}</div>"
                f"<div class='reason-text'>{escape(_reason_text(item))}</div>"
                "</div>"
                "</div>"
            )
        factors_html = (
            "<div class='factors-panel'>"
            "<div class='panel-title'>Main Factors Behind This Score</div>"
            f"<div class='reason-list'>{rows_html}</div>"
            "</div>"
        )
        st.markdown(factors_html, unsafe_allow_html=True)

    # ── actions ───────────────────────────────────────────────
    # FIX: candidate list now includes pages/8_Final_Report.py as first entry.
    # Old list only contained pages/7_Final_Report.py etc. — none of which exist.
    # The fallback contains=["report"] also finds it if path lookup fails.
    report_page = _find_existing_page(
        candidates=[
            "pages/8_Final_Report.py",
            "pages/7_Final_Report.py",
            "pages/7_Report.py",
            "pages/7_Generate_Report.py",
        ],
        contains=["report"],
    )

    st.markdown("<div class='cta-wrap'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        if st.button("View Suitability Map", use_container_width=True):
            st.switch_page("pages/6_Suitability_Heatmap.py")

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