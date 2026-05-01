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
import numpy as np

import streamlit as st
from ui_helpers import (
    get_image_records,
    get_uploaded_image_cache,
    init_state,
    apply_global_style,
    apply_ui_consistency_patch,
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


def _build_selected_site_breakdown(feature_extractor, row, col):
    items = []
    order = ["ghi", "sunshine", "slope", "obstacle", "lst", "elevation"]

    for name in order:
        raster = feature_extractor.layers.get(name)
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




def _get_ai_valid_area_mask(feature_extractor, shape):
    """
    Return the cells that remain valid after AI land-cover screening.

    Root fix:
    The old page used only the marker cell for the overall score. If the marker
    happened to fall on vegetation/building/water, the score became 0.0% even
    when most of the AOI was still valid. This mask lets the final score
    represent the valid part of the selected AOI instead of one rejected cell.
    """
    base_mask = np.ones(shape, dtype=bool)

    if not feature_extractor or not getattr(feature_extractor, "layers", None):
        return base_mask

    obstacle = feature_extractor.layers.get("obstacle")
    if obstacle is None:
        return base_mask

    meta = obstacle.metadata or {}
    if str(meta.get("source", "")).lower() != "aimodel":
        return base_mask

    obstacle_density = obstacle.data.astype(np.float32)
    valid = obstacle_density != obstacle.nodata

    building_density = np.array(
        meta.get("building_density", np.zeros_like(obstacle_density)),
        dtype=np.float32,
    )
    vegetation_density = np.array(
        meta.get("vegetation_density", np.zeros_like(obstacle_density)),
        dtype=np.float32,
    )
    water_density = np.array(
        meta.get("water_density", np.zeros_like(obstacle_density)),
        dtype=np.float32,
    )

    building_threshold = float(meta.get("building_threshold", 0.05))
    water_threshold = float(meta.get("water_threshold", 0.20))
    vegetation_threshold = float(meta.get("vegetation_threshold", 0.25))

    hard_exclusion = (
        (building_density > building_threshold)
        | (water_density > water_threshold)
        | (vegetation_density > vegetation_threshold)
    )

    return valid & ~hard_exclusion


def _build_selected_site_breakdown_area(feature_extractor, score_mask=None, ai_valid_mask=None):
    """
    Build the AHP breakdown for the selected AOI after AI screening.

    Root fix:
    - The old logic could show 0.0% for climate/terrain factors when the
      selected marker cell was rejected by AI.
    - This version evaluates the whole selected AOI.
    - AI-rejected cells are treated as zero contribution, while valid cells
      still contribute normally.

    This makes the factor cards consistent with the final score:
    final score = average suitability across the selected AOI after AI gate.
    """
    items = []
    order = ["ghi", "sunshine", "slope", "obstacle", "lst", "elevation"]

    if not feature_extractor or not getattr(feature_extractor, "layers", None):
        return items

    score_mask = np.asarray(score_mask, dtype=bool) if score_mask is not None else None
    ai_valid_mask = np.asarray(ai_valid_mask, dtype=bool) if ai_valid_mask is not None else None

    for name in order:
        raster = feature_extractor.layers.get(name)
        if raster is None:
            continue

        data = raster.data.astype(np.float32)
        meta = raster.metadata or {}
        unit = meta.get("unit", "")

        valid_mask = data != raster.nodata

        if score_mask is not None and score_mask.shape == data.shape:
            valid_mask = valid_mask & score_mask

        if not valid_mask.any():
            continue

        norm_vals = np.clip(data[valid_mask], 0.0, 1.0)

        if name in INVERTED:
            suitability_vals = 1.0 - norm_vals
        else:
            suitability_vals = norm_vals

        # Apply the same AI gate used by AHPModel: rejected cells remain in the
        # selected AOI, but their effective contribution is zero.
        if ai_valid_mask is not None and ai_valid_mask.shape == data.shape:
            gate_vals = ai_valid_mask[valid_mask].astype(np.float32)
            effective_vals = suitability_vals * gate_vals
        else:
            effective_vals = suitability_vals

        suitability_component = float(np.clip(np.mean(effective_vals), 0.0, 1.0))
        contribution_pct = suitability_component * WEIGHTS[name] * 100.0

        # Raw labels should describe the actual layer value across the selected AOI,
        # not become zero just because AI rejected some cells.
        raw_norm_mean = float(np.mean(norm_vals))
        raw_value = _denormalize_value(raw_norm_mean, meta)
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


def _area_level_score_from_suitability(suitability_raster, feature_extractor=None):
    """
    Compute the displayed overall score from the whole selected AOI.

    AHPModel already sets AI-rejected cells to 0.0 in the suitability raster.
    Therefore the fair site-level score is the mean of all valid AOI cells,
    including rejected cells as zero.
    """
    score_data = suitability_raster.data.astype(np.float32)
    score_mask = (score_data != suitability_raster.nodata) & np.isfinite(score_data)

    if score_mask.any():
        return float(np.mean(score_data[score_mask])), score_mask

    return 0.0, score_mask

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
        if score >= 0.99:
            return "AI confirmed no excluded land-cover obstacles"
        return "AI exclusion triggered by building, vegetation, or water"

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

def _get_ai_image_details(feature_extractor, row, col):
    def empty_details(summary="Pending AI model result", status="Pending"):
        return {
            "summary": summary,
            "status": status,
            "detected_classes": [],
            "main_message": summary,
            "supporting_message": "Detailed AI class breakdown is not available for this report.",
            "building_cells": 0,
            "water_cells": 0,
            "vegetation_cells": 0,
            "bare_land_cells": 0,
            "total_excluded_cells": 0,
            "valid_cells": 0,
            "total_cells": 0,
            "valid_pct": 0.0,
            "excluded_pct": 0.0,
            "building_pct": 0.0,
            "water_pct": 0.0,
            "vegetation_pct": 0.0,
            "bare_land_pct": 0.0,
            "main_obstacle": "none",
            "selected_cell": {},
        }

    if not feature_extractor or not getattr(feature_extractor, "layers", None):
        return empty_details()

    obstacle = feature_extractor.layers.get("obstacle")
    if obstacle is None:
        return empty_details()

    meta = obstacle.metadata or {}

    if str(meta.get("source", "")).lower() != "aimodel":
        return empty_details(
            summary="AI model unavailable - site not validated",
            status="Unavailable",
        )

    obstacle_density = obstacle.data.astype(np.float32)
    valid = obstacle_density != obstacle.nodata

    building_density = np.array(
        meta.get("building_density", np.zeros_like(obstacle_density)),
        dtype=np.float32,
    )
    vegetation_density = np.array(
        meta.get("vegetation_density", np.zeros_like(obstacle_density)),
        dtype=np.float32,
    )
    water_density = np.array(
        meta.get("water_density", np.zeros_like(obstacle_density)),
        dtype=np.float32,
    )
    bare_land_density = np.array(
    meta.get("bare_land_density", np.zeros_like(obstacle_density)),
    dtype=np.float32,
    )

    building_threshold = float(meta.get("building_threshold", 0.05))
    water_threshold = float(meta.get("water_threshold", 0.05))
    vegetation_threshold = float(meta.get("vegetation_threshold", 0.25))

    building_exclusion = valid & (building_density > building_threshold)
    water_exclusion = valid & (water_density > water_threshold)
    vegetation_exclusion = valid & (vegetation_density > vegetation_threshold)

    hard_exclusion = building_exclusion | water_exclusion | vegetation_exclusion

    total_cells = int(valid.sum())
    total_excluded_cells = int(hard_exclusion.sum())
    valid_cells = max(total_cells - total_excluded_cells, 0)

    building_cells = int(building_exclusion.sum())
    water_cells = int(water_exclusion.sum())
    vegetation_cells = int(vegetation_exclusion.sum())

    # Bare land is counted when class 3 covers a meaningful part of the cell.
    bare_land_mask = (bare_land_density > 0.25) & valid
    bare_land_cells = int(bare_land_mask.sum())

    def pct(value):
        return round((float(value) / total_cells) * 100.0, 1) if total_cells else 0.0

    valid_pct = pct(valid_cells)
    excluded_pct = pct(total_excluded_cells)
    building_pct = pct(building_cells)
    water_pct = pct(water_cells)
    vegetation_pct = pct(vegetation_cells)
    bare_land_pct = pct(bare_land_cells)
    print("AI DETAILS BARE LAND CELLS =", bare_land_cells)
    print("AI DETAILS BARE LAND PCT =", bare_land_pct)

    detected_classes = []
    if building_cells > 0:
        detected_classes.append("buildings")
    if water_cells > 0:
        detected_classes.append("water")
    if vegetation_cells > 0:
        detected_classes.append("vegetation")
    if bare_land_cells > 0:
        detected_classes.append("bare land")

    obstacle_counts = {
        "buildings": building_cells,
        "water": water_cells,
        "vegetation": vegetation_cells,
    }
    main_obstacle = max(obstacle_counts, key=obstacle_counts.get)
    if obstacle_counts[main_obstacle] == 0:
        main_obstacle = "none"

    obstacle_parts = []
    if vegetation_cells > 0:
        obstacle_parts.append(f"vegetation ({vegetation_pct:.1f}%)")
    if water_cells > 0:
        obstacle_parts.append(f"water ({water_pct:.1f}%)")
    if building_cells > 0:
        obstacle_parts.append(f"buildings ({building_pct:.1f}%)")

    if obstacle_parts:
        obstacle_text = ", ".join(obstacle_parts)
    else:
        obstacle_text = "no major excluded obstacles"

    selected_building = float(building_density[row, col])
    selected_water = float(water_density[row, col])
    selected_vegetation = float(vegetation_density[row, col])
    selected_bare_land = float(bare_land_density[row, col])
    selected_obstacle = float(obstacle_density[row, col])

    selected_blocking = []
    if selected_building > building_threshold:
        selected_blocking.append("buildings")
    if selected_water > water_threshold:
        selected_blocking.append("water")
    if selected_vegetation > vegetation_threshold:
        selected_blocking.append("vegetation")

    selected_is_excluded = len(selected_blocking) > 0

    if total_excluded_cells > 0:
        summary = f"AI screening result: {valid_pct:.1f}% valid, {excluded_pct:.1f}% rejected."
        main_message = (
            f"AI screening result: {valid_pct:.1f}% of the selected area remains valid "
            f"for suitability evaluation, while {excluded_pct:.1f}% was rejected mainly "
            f"because of {main_obstacle if main_obstacle != 'none' else 'detected obstacles'}."
        )
        supporting_message = (
            f"The AI model detected {obstacle_text}. Rejected cells are removed before "
            f"AHP scoring, so good climate or terrain conditions cannot override unsuitable "
            f"land-cover areas."
        )
        status = "Excluded" if selected_is_excluded else "Partially Valid"
    else:
        summary = "AI screening result: selected area is valid for suitability evaluation."
        main_message = (
            f"AI screening result: {valid_pct:.1f}% of the selected area remains valid "
            "for suitability evaluation."
        )
        supporting_message = (
            "The AI model did not detect excluded land-cover obstacles above the rejection "
            "thresholds. The area can continue to AHP-based suitability scoring."
        )
        status = "Passed"

    if selected_is_excluded:
        summary = "Excluded by AI: " + ", ".join(selected_blocking) + " detected in the selected cell"
    else:
        if selected_bare_land > 0.25:
            summary = "AI validated: selected cell contains open bare-land conditions"
        else:
            summary = "AI validated: selected cell has no excluded obstacle above threshold"

    return {
        "summary": summary,
        "status": status,
        "detected_classes": detected_classes,
        "main_message": main_message,
        "supporting_message": supporting_message,
        "building_cells": building_cells,
        "water_cells": water_cells,
        "vegetation_cells": vegetation_cells,
        "bare_land_cells": bare_land_cells,
        "total_excluded_cells": total_excluded_cells,
        "valid_cells": valid_cells,
        "total_cells": total_cells,
        "valid_pct": valid_pct,
        "excluded_pct": excluded_pct,
        "building_pct": building_pct,
        "water_pct": water_pct,
        "vegetation_pct": vegetation_pct,
        "bare_land_pct": bare_land_pct,
        "main_obstacle": main_obstacle,
        "selected_cell": {
            "building_density_pct": round(selected_building * 100, 1),
            "water_density_pct": round(selected_water * 100, 1),
            "vegetation_density_pct": round(selected_vegetation * 100, 1),
            "bare_land_density_pct": round(selected_bare_land * 100, 1),
            "obstacle_density_pct": round(selected_obstacle * 100, 1),
            "is_excluded": selected_is_excluded,
            "blocking_classes": selected_blocking,
        },
    }


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
    ai_details=None,
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
        "ai_details": ai_details or {},
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
                "weight_pct": round(item["weight"] * 100, 2),
                "suitability_component": round(item["suitability_component"], 4),
            }
            for item in factor_items
        ],
    }


# ── redesigned transition-page styles ─────────────────────────
st.markdown(
    """
<style>
.analysis-wrap{
    position:relative;
    z-index:2;
    padding-top:18px;
    padding-bottom:10px;
}
.analysis-title{
    font-family:'Capriola',sans-serif;
    font-size:clamp(36px,3.1vw,54px);
    color:#1F3864;
    line-height:1.08;
    text-align:center;
    margin:8px 0 10px;
}
.analysis-subtitle{
    font-family:'Capriola',sans-serif;
    font-size:15px;
    color:#64748B;
    line-height:1.6;
    text-align:center;
    max-width:900px;
    margin:0 auto 18px;
}
.ac-card{
    background:rgba(255,255,255,0.94);
    border:1px solid rgba(214,227,243,0.95);
    border-radius:30px;
    box-shadow:0 12px 34px rgba(15,23,42,0.08);
    padding:28px 30px 28px;
    margin:0 auto;
}
.ac-card.processing{ padding:30px 30px 26px; }
.ac-card.warning{ padding:28px 30px 24px; }
.ac-icon-shell{
    width:112px;
    height:112px;
    margin:0 auto 18px;
    border-radius:50%;
    background:linear-gradient(180deg,#F0FAF4 0%, #E5F6EC 100%);
    display:flex;
    align-items:center;
    justify-content:center;
    box-shadow:inset 0 0 0 1px #D9F1E2;
}
.ac-icon-ring{
    width:76px;
    height:76px;
    border-radius:50%;
    border:4px solid #16A34A;
    display:flex;
    align-items:center;
    justify-content:center;
    color:#16A34A;
}
.ac-loader-shell{
    width:104px;
    height:104px;
    margin:0 auto 16px;
    border-radius:50%;
    background:linear-gradient(180deg,#EEF5FF 0%, #E0EEFF 100%);
    display:flex;
    align-items:center;
    justify-content:center;
    box-shadow:inset 0 0 0 1px #D6E6FF;
}
.ac-loader-ring{
    width:72px;
    height:72px;
    border-radius:50%;
    border:4px solid rgba(0,112,255,0.15);
    border-top-color:#0070FF;
    animation:acSpin 1.1s linear infinite;
}
@keyframes acSpin { from{transform:rotate(0deg);} to{transform:rotate(360deg);} }
.ac-card-title{
    font-family:'Capriola',sans-serif;
    font-size:clamp(28px,2.4vw,40px);
    color:#1F3864;
    line-height:1.18;
    text-align:center;
    margin:0 0 10px;
}
.ac-card-copy{
    font-family:'Capriola',sans-serif;
    font-size:15px;
    color:#667085;
    line-height:1.75;
    text-align:center;
    max-width:760px;
    margin:0 auto 20px;
}
.ac-summary-grid{
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:14px;
    margin:16px 0 18px;
}
.ac-summary-grid.processing{
    grid-template-columns:repeat(2,minmax(0,1fr));
    max-width:640px;
    margin-left:auto;
    margin-right:auto;
}
.ac-chip{
    background:#FBFDFF;
    border:1px solid #E5EEF8;
    border-radius:18px;
    padding:16px 16px 14px;
    display:flex;
    align-items:center;
    gap:14px;
    min-height:96px;
}
.ac-chip-icon{
    width:60px;
    height:60px;
    border-radius:50%;
    display:flex;
    align-items:center;
    justify-content:center;
    flex-shrink:0;
}
.ac-chip-icon.loc{ background:#EAF2FF; color:#1D6FFF; }
.ac-chip-icon.img{ background:#EEF1FF; color:#4361EE; }
.ac-chip-icon.score{ background:#ECF5FF; color:#0070FF; }
.ac-chip-icon.result{ background:#EAF8EF; color:#16A34A; }
.ac-chip-meta{ min-width:0; }
.ac-chip-label{
    font-family:'Capriola',sans-serif;
    font-size:11px;
    color:#7A7A7A;
    text-transform:uppercase;
    letter-spacing:.07em;
    margin-bottom:5px;
}
.ac-chip-value{
    font-family:'Capriola',sans-serif;
    font-size:18px;
    color:#183B74;
    font-weight:700;
    line-height:1.3;
    word-break:break-word;
}
.ac-chip-value.score{ color:#0070FF; }
.ac-chip-value.result{ color:#16A34A; }
.ac-note{
    display:flex;
    align-items:center;
    justify-content:center;
    gap:10px;
    font-family:'Capriola',sans-serif;
    font-size:14px;
    color:#6B7280;
    line-height:1.5;
    margin:2px 0 18px;
    text-align:center;
}
.ac-note .icon{ color:#36A3FF; display:flex; align-items:center; }
.ac-progress-wrap{
    max-width:760px;
    margin:10px auto 0;
}
.ac-progress-label{
    font-family:'Capriola',sans-serif;
    font-size:14px;
    font-weight:600;
    color:#53627C;
    text-align:center;
    margin:0 0 9px;
}
.ac-progress-track{
    width:100%;
    height:22px;
    background:rgba(0,0,0,0.07);
    border-radius:999px;
    overflow:hidden;
    box-shadow: inset 0 2px 6px rgba(0,0,0,0.10);
}
.ac-progress-fill{
    height:100%;
    border-radius:999px;
    background:linear-gradient(90deg,#003caa 0%,#0070FF 25%,#38b6ff 50%,#0070FF 75%,#003caa 100%);
    background-size:400% 100%;
    animation:wShimmer 2s linear infinite;
    box-shadow:0 0 20px rgba(0,112,255,0.50),0 3px 10px rgba(0,112,255,0.24);
    transition: width .7s cubic-bezier(.4,0,.2,1);
}
@keyframes wShimmer { 0% { background-position: 200% center; } 100% { background-position: -200% center; } }
.ac-status-pill{
    width:fit-content;
    margin:12px auto 0;
    padding:8px 14px;
    border-radius:999px;
    background:#EEF5FF;
    border:1px solid #DCEAFD;
    font-family:'Capriola',sans-serif;
    font-size:13px;
    color:#365277;
}
.ac-action-row{
    margin-top:10px;
}
.ac-warning-list{
    font-family:'Capriola',sans-serif;
    font-size:15px;
    color:#7A2630;
    line-height:1.7;
    text-align:center;
    max-width:620px;
    margin:0 auto 12px;
}
.ac-warning-icon{
    width:104px;
    height:104px;
    margin:0 auto 16px;
    border-radius:50%;
    background:linear-gradient(180deg,#FFF2F2 0%,#FFE7E7 100%);
    display:flex;
    align-items:center;
    justify-content:center;
    color:#E2534A;
    box-shadow:inset 0 0 0 1px #FBD3D3;
}
.ac-warning-icon svg{ width:44px;height:44px; }
.ac-center-col > div[data-testid="stVerticalBlock"]{ gap:0.65rem; }

@media (max-width: 1100px){
    .ac-summary-grid{ grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (max-width: 760px){
    .analysis-title{ font-size:30px; }
    .ac-card{ padding:22px 18px; border-radius:24px; }
    .ac-summary-grid,
    .ac-summary-grid.processing{ grid-template-columns:1fr; }
    .ac-chip{ min-height:88px; }
}
</style>
""",
    unsafe_allow_html=True,
)
apply_ui_consistency_patch()


def _summary_chip(icon_svg: str, icon_class: str, label: str, value: str, value_class: str = "") -> str:
    extra = f" {value_class}" if value_class else ""
    return (
        f"<div class='ac-chip'>"
        f"<div class='ac-chip-icon {icon_class}'>{icon_svg}</div>"
        f"<div class='ac-chip-meta'>"
        f"<div class='ac-chip-label'>{escape(label)}</div>"
        f"<div class='ac-chip-value{extra}'>{escape(value)}</div>"
        f"</div></div>"
    )


def _render_page_heading(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='analysis-title'>{escape(title)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='analysis-subtitle'>{escape(subtitle)}</div>", unsafe_allow_html=True)


def _render_processing_card(site_name: str, image_text: str, progress_pct: int, progress_msg: str) -> None:
    chips = "".join([
        _summary_chip(ICO_LOC, "loc", "Selected Location", site_name),
        _summary_chip(ICO_IMG, "img", "Uploaded Image", image_text),
    ])
    st.markdown(
        f"""
        <div class='ac-card processing'>
            <div class='ac-loader-shell'><div class='ac-loader-ring'></div></div>
            <div class='ac-card-title'>Analyzing Your Selected Site</div>
            <div class='ac-card-copy'>We are processing the selected location and preparing the final result. This may take a few moments.</div>
            <div class='ac-summary-grid processing'>{chips}</div>
            <div class='ac-progress-wrap'>
                <div class='ac-progress-label'>{escape(progress_msg)}</div>
                <div class='ac-progress-track'><div class='ac-progress-fill' style='width:{progress_pct}%;'></div></div>
                <div class='ac-status-pill'>Analysis in progress...</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_missing_card(missing: list[str]) -> None:
    missing_text = " and ".join(missing)
    st.markdown(
        f"""
        <div class='ac-card warning'>
            <div class='ac-warning-icon'>{ICO_WARN}</div>
            <div class='ac-card-title'>We Need a Little More to Continue</div>
            <div class='ac-warning-list'>Please provide the {escape(missing_text)} before starting the analysis.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_success_card(site_name: str, image_text: str, score_text: str, result_text: str) -> None:
    chips = "".join([
        _summary_chip(ICO_LOC, "loc", "Selected Location", site_name),
        _summary_chip(ICO_IMG, "img", "Uploaded Image", image_text),
        _summary_chip("%", "score", "Final Score", score_text, "score"),
        _summary_chip(ICO_OK, "result", "Result", result_text, "result"),
    ])
    st.markdown(
        f"""
        <div class='ac-card'>
            <div class='ac-icon-shell'><div class='ac-icon-ring'>{ICO_OK}</div></div>
            <div class='ac-card-title'>Analysis Completed Successfully</div>
            <div class='ac-card-copy'>Your selected site has been analysed successfully. You can now review the detailed final report or inspect the suitability heatmap.</div>
            <div class='ac-summary-grid'>{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════
# PAGE LAYOUT
# ═══════════════════════════════════════════════════════════════
render_top_home_button("pages/2_Home.py")

st.markdown('<div class="analysis-wrap">', unsafe_allow_html=True)

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
else:
    aoi = None

site_display_name = _display_location_name(location_name, lat, lon)
coords_text = f"{lat:.4f}N, {lon:.4f}E" if has_loc else "Coordinates unavailable"

image_count = _uploaded_image_count()
img_main = (
    f"{image_count} image" if image_count == 1 else f"{image_count} images"
) if has_img else "No image"
img_sub = img_name if img_name else "Upload a site image to continue"

run_result = st.session_state.get("analysis_run")
has_aoi = aoi is not None
all_ready = has_loc and has_img and has_aoi

left_spacer, card_col, right_spacer = st.columns([1.05, 1.7, 1.05], gap="small")

with card_col:
    st.markdown('<div class="ac-center-col">', unsafe_allow_html=True)

    if run_result is None:
        if not all_ready:
            _render_page_heading(
                "Site Analysis",
                "Complete the required inputs to start analysing your selected site.",
            )
            missing = []
            if not has_loc:
                missing.append("selected location")
            if not has_aoi:
                missing.append("drawn analysis boundary")
            if not has_img:
                missing.append("uploaded image")
                
            _render_missing_card(missing)
            btn1, btn2 = st.columns(2, gap="small")
            with btn1:
                if st.button("Back to Location", use_container_width=True):
                    st.switch_page("pages/3_Choose_Location.py")
            with btn2:
                if st.button("Back to Upload", use_container_width=True):
                    st.switch_page("pages/4_Upload_Image.py")
        else:
            _render_page_heading(
                "Site Analysis",
                "We are preparing the suitability result for your selected site.",
            )

            card_slot = st.empty()
            def _update_progress(pct: int, msg: str) -> None:
                with card_slot.container():
                    _render_processing_card(site_display_name, img_main, pct, msg)

            _update_progress(5, "Initialising analysis...")
            try:
                from Wahhaj.ExternalDataSourceAdapter import ExternalDataSourceAdapter
                from Wahhaj.FeatureExtractor import FeatureExtractor, Dataset
                from Wahhaj.AHPModel import AHPModel
                from Wahhaj.AnalysisRun import AnalysisRun

                now = datetime.now()

                _update_progress(20, "Preparing site data...")
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

                _update_progress(40, "Loading analysis pipeline...")
                # Match the external data grid to FeatureExtractor.TARGET_SHAPE from the start.
                # This prevents 5x5 -> 10x10 resampling artifacts and keeps
                # the AHP layers aligned with the suitability raster.
                adapter = ExternalDataSourceAdapter(
                    grid_rows=FeatureExtractor.TARGET_SHAPE[0],
                    grid_cols=FeatureExtractor.TARGET_SHAPE[1],
                )

                gee_ready = adapter.initialize_earth_engine()
                st.session_state["gee_ready"] = gee_ready

                feature_extractor = FeatureExtractor(adapter=adapter)
                ahp = AHPModel()

                run = AnalysisRun(
                    ahp_model=ahp,
                    feature_extractor=feature_extractor,
                    top_k_sites=10,
                    min_site_score=0.0,
                )

                set_analysis_state(
                    run,
                    status="running",
                    dataset_id=dataset_ref.get("dataset_id"),
                    location_name=location_name,
                    created_at=now,
                    updated_at=now,
                )

                _update_progress(65, "Running site analysis...")
                run.execute(dataset)
                obstacle_layer = None

                try:
                    obstacle_layer = feature_extractor.layers.get("obstacle")
                except Exception:
                    obstacle_layer = None

                obstacle_meta = obstacle_layer.metadata if obstacle_layer is not None and obstacle_layer.metadata else {}

                st.session_state["ai_obstacle_source"] = obstacle_meta.get("source", "missing")
                st.session_state["ai_obstacle_metadata"] = obstacle_meta

                if obstacle_meta.get("source") != "AIModel":
                    st.warning(
                        "AI obstacle layer was not generated by the real model. "
                        f"Source: {obstacle_meta.get('source', 'missing')}. "
                        f"Reason/Error: {obstacle_meta.get('reason') or obstacle_meta.get('error') or 'No details'}"
                    )

                st.session_state["suitability_raster"] = run.suitability
                st.session_state["analysis_aoi"] = dataset.aoi

                fallback_layers = []

                for layer_name, raster in feature_extractor.layers.items():
                    metadata = raster.metadata or {}
                    source = str(metadata.get("source", "")).lower()
                    data_quality = str(metadata.get("data_quality", "")).lower()

                    if source in ["synthetic", "mock", "fallback"] or data_quality == "fallback":
                        fallback_layers.append(layer_name)

                st.session_state["fallback_layers"] = fallback_layers
                st.session_state["used_fallback_data"] = len(fallback_layers) > 0

                _update_progress(88, "Saving result...")
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
                st.session_state["extractor"] = feature_extractor
                set_analysis_state(
                    run,
                    status="completed",
                    dataset_id=(st.session_state.get("dataset_ref") or {}).get("dataset_id"),
                    location_name=location_name,
                    created_at=now,
                    updated_at=completed_at,
                )

                _update_progress(100, "✓ Analysis complete — preparing your next step...")
                time.sleep(1.0)
                st.rerun()

            except Exception as exc:
                failed_at = datetime.now()
                set_analysis_state(
                    st.session_state.get("_analysis_run_cache"),
                    status="failed",
                    dataset_id=(st.session_state.get("dataset_ref") or {}).get("dataset_id"),
                    location_name=location_name,
                    created_at=(st.session_state.get("analysis_ref") or {}).get("created_at"),
                    updated_at=failed_at,
                )
                _render_page_heading("Site Analysis", "The analysis could not be completed.")
                st.markdown(
                    f"<div class='ac-card warning'><div class='ac-warning-icon'>{ICO_WARN}</div><div class='ac-card-title'>Analysis Failed</div><div class='ac-warning-list'>Please try again. You can review the error details below if needed.</div></div>",
                    unsafe_allow_html=True,
                )
                with st.expander("Error details"):
                    st.exception(exc)

    else:
        run = run_result
        feature_extractor = st.session_state.get("extractor")

        selected_score = None
        selected_label = "—"
        ai_assessment = "Pending AI model result"
        factor_items = []
        reason_items = []

        if run and getattr(run, "suitability", None) is not None and has_loc:
            suit = run.suitability
            row, col = _point_to_grid_cell(lat, lon, aoi, suit.data.shape)

            # Root fix for the top-left Overall Suitability Score:
            # Use the valid evaluated AOI area, not only the marker cell.
            # If the marker cell is rejected by AI, the AI panel will still explain it,
            # but the saved score will summarize the usable part of the selected AOI.
            selected_score, score_mask = _area_level_score_from_suitability(
                suit,
                feature_extractor=feature_extractor,
            )
            selected_label, _badge_class = suitability_badge(selected_score)

            ai_details = {}

            if feature_extractor and getattr(feature_extractor, "layers", None):
                ai_details = _get_ai_image_details(feature_extractor, row, col)
                ai_assessment = ai_details["summary"]

                # Build AHP contribution cards from the whole selected AOI.
                # AI-rejected cells stay in the AOI as zero contribution, so the
                # cards explain the actual displayed site-level result.
                ai_valid_mask = _get_ai_valid_area_mask(feature_extractor, suit.data.shape)
                factor_items = _build_selected_site_breakdown_area(
                    feature_extractor,
                    score_mask,
                    ai_valid_mask,
                )

                if ai_details.get("valid_cells", 1) == 0:
                    # Only if the whole AOI is rejected do we treat it as a full
                    # AI exclusion decision and suppress normal AHP explanation.
                    for item in factor_items:
                        if item["name"] != "obstacle":
                            item["contribution_pct"] = 0.0

                    reason_items = [
                        item for item in factor_items
                        if item["name"] == "obstacle"
                    ]
                else:
                    reason_items = _top_reason_items(factor_items, k=3)

            _save_selected_site_analysis(
                site_display_name=site_display_name,
                location_name=location_name,
                lat=lat,
                lon=lon,
                img_name=img_name,
                score=selected_score,
                label=selected_label,
                ai_assessment=ai_assessment,
                factor_items=factor_items,
                reason_items=reason_items,
                run_id=getattr(run, "runId", None),
                analysis_id=(st.session_state.get("analysis_ref") or {}).get("analysis_id"),
                ai_details=ai_details,
            )

        _render_page_heading(
            "Analysis Completed",
            "Your selected site has been analysed successfully and is ready for review.",
        )
        _render_success_card(
            site_display_name,
            img_main,
            _safe_pct(selected_score),
            selected_label,
        )

        if st.session_state.get("used_fallback_data") and feature_extractor:
            with st.expander("Fallback details"):
                for layer_name, raster in feature_extractor.layers.items():
                    metadata = raster.metadata or {}
                    if (
                        str(metadata.get("data_quality", "")).lower() == "fallback"
                        or str(metadata.get("source", "")).lower() in ["synthetic", "mock", "fallback"]
                    ):
                        st.write(f"**{layer_name}**")
                        st.write(
                            "Reason:",
                            metadata.get("fallback_reason")
                            or metadata.get("reason")
                            or metadata.get("error")
                            or "Unknown"
                    )
        elif not st.session_state.get("used_fallback_data"):
            st.success("Analysis used real environmental data sources.")

        report_page = _find_existing_page(
            candidates=[
                "pages/8_Final_Report.py",
                "pages/7_Final_Report.py",
                "pages/7_Report.py",
                "pages/7_Generate_Report.py",
            ],
            contains=["report"],
        )

        btn1, btn2 = st.columns(2, gap="small")

        with btn1:
            if st.button(
                "View Final Report",
                use_container_width=True,
                disabled=report_page is None,
                key="view_final_report_btn",
            ):
                if report_page:
                    st.switch_page(report_page)

        with btn2:
            if st.button(
                "Open Suitability Heatmap",
                use_container_width=True,
                key="open_suitability_heatmap_btn",
            ):
                st.switch_page("pages/6_Suitability_Heatmap.py")

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
