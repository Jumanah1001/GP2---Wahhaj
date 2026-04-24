"""
ui_helpers.py
=============
Shared Streamlit helpers for WAHHAJ.
"""

import sys
import os
import streamlit as st
from pathlib import Path

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from Wahhaj.User import User, UserRole
from Wahhaj.models import AOI
from Wahhaj.FeatureExtractor import Dataset


# ═══════════════════════════════════════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════════════════════════════════════

def init_state() -> None:
    defaults: dict = {
        "logged_in":        False,
        "username":         "",
        "user_email":       "",
        "user_role":        "",
        "user_id":          "",
        "session_id":       "",
        "session_expires":  "",
        "selected_location": {
            "location_name": "",
            "latitude":      None,
            "longitude":     None,
        },
        "location_saved":   False,
        "aoi":              None,
        "dataset":          None,
        "_dataset_cache":   None,
        "dataset_ref": {
            "dataset_id":   None,
            "dataset_uri":  None,
            "name":         None,
            "status":       "empty",
            "source":       None,
            "image_count":  0,
            "aoi":          None,
            "created_at":   None,
            "updated_at":   None,
        },
        "uploaded_image_name":      "",
        "uploaded_image_bytes":     None,
        "uploaded_image_temp_path": "",
        "image_records":            [],
        "_uploaded_image_cache":    [],
        "extractor":              None,
        "ahp_weights_confirmed":  False,
        "analysis_run":           None,
        "_analysis_run_cache":    None,
        "analysis_ref": {
            "analysis_id":   None,
            "dataset_id":    None,
            "status":        "idle",
            "location_name": None,
            "report_uri":    None,
            "heatmap_uri":   None,
            "created_at":    None,
            "updated_at":    None,
        },
        "report_obj":             None,
        "selected_site_analysis": None,
        "uploaded_images":        [],
        "analysis_history": [],
        "history_loaded": False,
        "users": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ═══════════════════════════════════════════════════════════════════════════
# Analysis History
# ═══════════════════════════════════════════════════════════════════════════

def save_analysis_to_history(run, ranked: list, location: dict) -> None:
    from datetime import datetime

    if "analysis_history" not in st.session_state:
        st.session_state["analysis_history"] = []

    st.session_state["analysis_history"] = [
        e for e in st.session_state["analysis_history"]
        if e.get("run_id") != run.runId
    ]

    summary = run.summary()
    suit = summary.get("suitability", {})
    score_mean = float(suit.get("mean", 0.0) or 0.0)
    top_score = float(ranked[0].score) if ranked else 0.0

    selected_site = st.session_state.get("selected_site_analysis") or {}
    selected_score = selected_site.get("score")
    try:
        selected_score = float(selected_score)
    except Exception:
        selected_score = top_score if top_score > 0 else score_mean

    selected_label = str(selected_site.get("label") or "").strip()
    if not selected_label:
        if selected_score >= 0.8:
            selected_label = "Highly Recommended"
        elif selected_score >= 0.6:
            selected_label = "Recommended"
        else:
            selected_label = "Review Required"

    ranked_list = []
    for c in ranked[:10]:
        s10 = round(c.score * 10, 2)
        lat = round(c.centroid.lat, 4) if c.centroid else None
        lon = round(c.centroid.lon, 4) if c.centroid else None
        rec = (
            "Highly Recommended" if c.score >= 0.8 else
            "Recommended" if c.score >= 0.6 else
            "Not Applicable"
        )
        ranked_list.append({
            "rank": c.rank,
            "lat": lat,
            "lon": lon,
            "score": round(c.score, 4),
            "s10": s10,
            "rec": rec,
        })

    entry = {
        "run_id": run.runId,
        "location_name": location.get("location_name", "Unknown"),
        "lat": location.get("latitude"),
        "lon": location.get("longitude"),
        "aoi": st.session_state.get("aoi"),
        "selected_score": round(selected_score, 4),
        "selected_label": selected_label,
        "score_mean": round(score_mean, 4),
        "top_score": round(top_score, 4),
        "candidate_count": len(ranked),
        "recommendation": selected_label,
        "analysed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ranked": ranked_list,
        "state_snapshot": {
            "analysis_run": run,
            "report_obj": st.session_state.get("report_obj"),
            "selected_location": dict(location or {}),
            "location_saved": True,
            "aoi": st.session_state.get("aoi"),
            "selected_site_analysis": dict(selected_site) if isinstance(selected_site, dict) else selected_site,
            "analysis_ref": dict(st.session_state.get("analysis_ref") or {}),
        },
    }

    st.session_state["analysis_history"].insert(0, entry)
    st.session_state["history_loaded"] = True

    # Persist a lightweight copy in Supabase/PostgreSQL.
    # Objects such as analysis_run/report_obj stay only in session_state.
    try:
        from Wahhaj.db_connection import get_db
        import json

        with get_db() as cur:
            cur.execute(
                """INSERT INTO analysis_history
                (run_id, user_email, location_name, lat, lon,
                 top_score, recommendation, candidate_count,
                 analysed_at, ranked_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT (run_id) DO UPDATE SET
                    user_email = EXCLUDED.user_email,
                    location_name = EXCLUDED.location_name,
                    lat = EXCLUDED.lat,
                    lon = EXCLUDED.lon,
                    top_score = EXCLUDED.top_score,
                    recommendation = EXCLUDED.recommendation,
                    candidate_count = EXCLUDED.candidate_count,
                    analysed_at = EXCLUDED.analysed_at,
                    ranked_json = EXCLUDED.ranked_json
                """,
                (
                    entry["run_id"],
                    st.session_state.get("user_email", ""),
                    entry["location_name"],
                    entry["lat"],
                    entry["lon"],
                    entry["top_score"],
                    entry["recommendation"],
                    entry["candidate_count"],
                    entry["analysed_at"],
                    json.dumps(entry["ranked"]),
                ),
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("DB save failed: %s", exc)


def get_analysis_history() -> list:
    if st.session_state.get("history_loaded"):
        return st.session_state.get("analysis_history", [])

    email = st.session_state.get("user_email", "").strip().lower()
    if not email:
        return st.session_state.get("analysis_history", [])

    try:
        from Wahhaj.db_connection import get_db
        import json

        with get_db() as cur:
            cur.execute(
                """SELECT run_id, location_name, lat, lon, top_score,
                          recommendation, candidate_count, analysed_at, ranked_json
                   FROM analysis_history
                   WHERE user_email = %s
                   ORDER BY created_at DESC
                   LIMIT 50""",
                (email,),
            )
            rows = cur.fetchall()

        history = []
        for r in rows:
            ranked = r[8]
            if isinstance(ranked, str):
                ranked = json.loads(ranked) if ranked else []
            elif ranked is None:
                ranked = []

            history.append({
                "run_id": r[0],
                "location_name": r[1],
                "lat": r[2],
                "lon": r[3],
                "top_score": r[4],
                "selected_score": r[4],
                "recommendation": r[5],
                "selected_label": r[5],
                "candidate_count": r[6],
                "analysed_at": r[7],
                "ranked": ranked,
                "state_snapshot": {},
            })

        st.session_state["analysis_history"] = history
        st.session_state["history_loaded"] = True
        return history

    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("DB load failed: %s", exc)
        return st.session_state.get("analysis_history", [])



def _coerce_history_score(value) -> float:
    try:
        score = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, score))


def _coerce_history_aoi(value):
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            lon_min, lat_min, lon_max, lat_max = [float(v) for v in value]
            if lon_min < lon_max and lat_min < lat_max:
                return (lon_min, lat_min, lon_max, lat_max)
        except Exception:
            return None
    return None


def _clean_ranked_history_entry(entry: dict, fallback_rank: int) -> dict | None:
    if not isinstance(entry, dict):
        return None

    lat = entry.get("lat")
    lon = entry.get("lon")
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except Exception:
        lat, lon = None, None

    aoi = _coerce_history_aoi(entry.get("aoi"))
    if lat is None and lon is None and aoi is None:
        return None

    if (lat is None or lon is None) and aoi is not None:
        lon_min, lat_min, lon_max, lat_max = aoi
        lat = (lat_min + lat_max) / 2
        lon = (lon_min + lon_max) / 2

    score = _coerce_history_score(entry.get("selected_score", entry.get("top_score", 0.0)))
    label = str(entry.get("selected_label") or entry.get("recommendation") or "Review Required").strip()
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
        "recommendation": label,
        "analysed_at": analysed_at,
        "entry": entry,
    }


def get_ranked_history() -> list:
    """Return saved analysed sites sorted by final selected-site score.

    This is the single source of truth for Ranked Results, Final Report, and
    PDF export. It intentionally ranks saved site analyses, not internal
    candidate pixels from the heatmap.
    """
    raw_history = get_analysis_history() or []
    prepared = []
    for idx, entry in enumerate(raw_history, start=1):
        cleaned = _clean_ranked_history_entry(entry, idx)
        if cleaned is not None:
            prepared.append(cleaned)

    prepared.sort(key=lambda item: item["score"], reverse=True)
    for idx, item in enumerate(prepared, start=1):
        item["rank"] = idx
    return prepared


def get_global_rank_for_run(run_id) -> tuple[int | None, int]:
    ranked = get_ranked_history()
    run_id = str(run_id) if run_id is not None else None
    for item in ranked:
        if str(item.get("run_id")) == run_id:
            return item.get("rank"), len(ranked)
    return None, len(ranked)

def restore_analysis_history_entry(entry: dict) -> bool:
    if not isinstance(entry, dict):
        return False

    snapshot = entry.get("state_snapshot") or {}
    run = snapshot.get("analysis_run")
    if run is None:
        return False

    st.session_state["analysis_run"] = run
    st.session_state["_analysis_run_cache"] = run

    report_obj = snapshot.get("report_obj")
    if report_obj is not None:
        st.session_state["report_obj"] = report_obj

    location = snapshot.get("selected_location") or {
        "location_name": entry.get("location_name", "Unknown"),
        "latitude": entry.get("lat"),
        "longitude": entry.get("lon"),
    }
    st.session_state["selected_location"] = dict(location)
    st.session_state["location_saved"] = bool(snapshot.get("location_saved", True))
    st.session_state["aoi"] = snapshot.get("aoi", entry.get("aoi"))

    selected_site = snapshot.get("selected_site_analysis")
    if selected_site is not None:
        st.session_state["selected_site_analysis"] = dict(selected_site) if isinstance(selected_site, dict) else selected_site

    analysis_ref = snapshot.get("analysis_ref")
    if analysis_ref:
        st.session_state["analysis_ref"] = dict(analysis_ref)

    return True


def _blank_dataset_ref() -> dict:
    return {
        "dataset_id": None,
        "dataset_uri": None,
        "name": None,
        "status": "empty",
        "source": None,
        "image_count": 0,
        "aoi": None,
        "created_at": None,
        "updated_at": None,
    }


def _blank_analysis_ref() -> dict:
    return {
        "analysis_id": None,
        "dataset_id": None,
        "status": "idle",
        "location_name": None,
        "report_uri": None,
        "heatmap_uri": None,
        "created_at": None,
        "updated_at": None,
    }


def _timestamp_or_none(value):
    if value is None:
        return None
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def build_image_record(
    *,
    name: str,
    size_bytes: int,
    storage_path: str | None = None,
    temp_path: str | None = None,
    mime_type: str | None = None,
    db=None,
    job=None,
) -> dict:
    image_id = None
    dataset_id = None
    created_at = None

    images = getattr(db, "images", None) or []
    if images:
        first_image = images[0]
        image_id = str(getattr(first_image, "imageId", "") or "") or None
        created_at = _timestamp_or_none(getattr(first_image, "timestamp", None))

    dataset_id = str(getattr(db, "dataset_id", "") or "") or None
    job_id = str(getattr(job, "jobId", "") or "") or None

    return {
        "image_id": image_id,
        "dataset_id": dataset_id,
        "job_id": job_id,
        "name": name,
        "size_bytes": int(size_bytes or 0),
        "storage_path": storage_path,
        "temp_path": temp_path,
        "mime_type": mime_type,
        "status": "uploaded",
        "created_at": created_at,
    }


def set_image_records(records: list, *, cache_items: list | None = None) -> None:
    st.session_state["image_records"] = records or []
    if cache_items is not None:
        st.session_state["_uploaded_image_cache"] = cache_items
        st.session_state["uploaded_images"] = cache_items


def get_image_records() -> list:
    return st.session_state.get("image_records", [])


def get_uploaded_image_cache() -> list:
    cache_items = st.session_state.get("_uploaded_image_cache") or []
    if cache_items:
        return cache_items
    return st.session_state.get("uploaded_images", []) or []


def set_dataset_state(
    dataset=None,
    *,
    status: str = "draft",
    dataset_id: str | None = None,
    dataset_uri: str | None = None,
    source: str | None = "session",
    image_count: int | None = None,
    aoi=None,
    name: str | None = None,
    created_at=None,
    updated_at=None,
) -> dict:
    current = dict(st.session_state.get("dataset_ref") or _blank_dataset_ref())

    resolved_dataset_id = dataset_id
    if resolved_dataset_id is None and dataset is not None:
        resolved_dataset_id = str(getattr(dataset, "dataset_id", "") or "") or None

    resolved_name = name
    if resolved_name is None and dataset is not None:
        resolved_name = getattr(dataset, "name", None)

    resolved_aoi = aoi if aoi is not None else current.get("aoi")
    if resolved_aoi is None and dataset is not None:
        resolved_aoi = getattr(dataset, "aoi", None)

    resolved_image_count = image_count
    if resolved_image_count is None and dataset is not None:
        resolved_image_count = len(getattr(dataset, "images", []) or [])

    if created_at is None:
        created_at = current.get("created_at")
    created_at = _timestamp_or_none(created_at)

    if updated_at is None:
        updated_at = getattr(dataset, "updated_at", None) if dataset is not None else None
    updated_at = _timestamp_or_none(updated_at)

    new_ref = {
        "dataset_id": resolved_dataset_id,
        "dataset_uri": dataset_uri if dataset_uri is not None else current.get("dataset_uri"),
        "name": resolved_name,
        "status": status,
        "source": source if source is not None else current.get("source"),
        "image_count": int(resolved_image_count or 0),
        "aoi": tuple(resolved_aoi) if isinstance(resolved_aoi, (list, tuple)) else resolved_aoi,
        "created_at": created_at,
        "updated_at": updated_at,
    }

    st.session_state["dataset"] = dataset
    st.session_state["_dataset_cache"] = dataset
    st.session_state["dataset_ref"] = new_ref
    return new_ref


def set_analysis_state(
    run=None,
    *,
    status: str = "idle",
    analysis_id: str | None = None,
    dataset_id: str | None = None,
    location_name: str | None = None,
    report_uri: str | None = None,
    heatmap_uri: str | None = None,
    created_at=None,
    updated_at=None,
) -> dict:
    current = dict(st.session_state.get("analysis_ref") or _blank_analysis_ref())

    resolved_analysis_id = analysis_id
    if resolved_analysis_id is None and run is not None:
        resolved_analysis_id = getattr(run, "runId", None)

    if dataset_id is None:
        dataset_id = (st.session_state.get("dataset_ref") or {}).get("dataset_id")

    if location_name is None:
        location_name = (st.session_state.get("selected_location") or {}).get("location_name")

    if created_at is None:
        created_at = current.get("created_at")
    created_at = _timestamp_or_none(created_at)

    if updated_at is None:
        updated_at = getattr(run, "endedAt", None) or getattr(run, "startedAt", None) or current.get("updated_at")
    updated_at = _timestamp_or_none(updated_at)

    new_ref = {
        "analysis_id": resolved_analysis_id,
        "dataset_id": dataset_id,
        "status": status,
        "location_name": location_name,
        "report_uri": report_uri if report_uri is not None else current.get("report_uri"),
        "heatmap_uri": heatmap_uri if heatmap_uri is not None else current.get("heatmap_uri"),
        "created_at": created_at,
        "updated_at": updated_at,
    }

    st.session_state["analysis_run"] = run
    st.session_state["_analysis_run_cache"] = run
    st.session_state["analysis_ref"] = new_ref
    return new_ref


# ═══════════════════════════════════════════════════════════════════════════
# Reset helpers
# ═══════════════════════════════════════════════════════════════════════════

_LOCATION_UI_DEFAULTS = {
    "loc_candidate_lat": None,
    "loc_candidate_lon": None,
    "loc_candidate_name": "",
    "loc_search_input": "",
    "loc_map_lat": 24.7136,
    "loc_map_lon": 46.6753,
    "loc_candidate_aoi": None,
    "loc_rectangle_drawn": False,
    "manual_lat": 24.7136,
    "manual_lon": 46.6753,
    "manual_name": "",
}

# Widget keys that Streamlit owns — must be deleted, not assigned
_LOCATION_WIDGET_KEYS = (
    "loc_search_txt",
    "loc_main_map",
    "loc_search_btn",
    "use_manual_btn",
    "save_loc_btn",
    "clear_loc_btn",
    "next_loc_btn",
)


def reset_location_ui_state() -> None:
    for key, value in _LOCATION_UI_DEFAULTS.items():
        st.session_state[key] = value

    for widget_key in _LOCATION_WIDGET_KEYS:
        st.session_state.pop(widget_key, None)


def reset_active_analysis_state(*, clear_location: bool = True) -> None:
    if clear_location:
        st.session_state["selected_location"] = {
            "location_name": "",
            "latitude": None,
            "longitude": None,
        }
        st.session_state["location_saved"] = False
        st.session_state["aoi"] = None
        st.session_state["dataset"] = None
        st.session_state["_dataset_cache"] = None
        st.session_state["dataset_ref"] = _blank_dataset_ref()

    st.session_state["uploaded_image_name"] = ""
    st.session_state["uploaded_image_bytes"] = None
    st.session_state["uploaded_image_temp_path"] = ""
    st.session_state["uploaded_images"] = []
    st.session_state["image_records"] = []
    st.session_state["_uploaded_image_cache"] = []
    st.session_state["extractor"] = None
    st.session_state["ahp_weights_confirmed"] = False
    st.session_state["analysis_run"] = None
    st.session_state["_analysis_run_cache"] = None
    st.session_state["analysis_ref"] = _blank_analysis_ref()
    st.session_state["report_obj"] = None
    st.session_state["selected_site_analysis"] = None
    st.session_state.pop("analysis_start_date", None)
    st.session_state.pop("analysis_end_date", None)


def reset_for_new_analysis() -> None:
    reset_active_analysis_state(clear_location=True)
    reset_location_ui_state()


def clear_analysis_state(clear_dataset: bool = True) -> None:
    keys_to_none = [
        "extractor", "analysis_run", "_analysis_run_cache",
        "report_obj", "selected_site_analysis",
        "analysis_start_date", "analysis_end_date",
    ]
    if clear_dataset:
        keys_to_none.extend(["dataset", "_dataset_cache"])

    for key in keys_to_none:
        st.session_state[key] = None

    if clear_dataset:
        st.session_state["dataset_ref"] = _blank_dataset_ref()

    st.session_state["analysis_ref"] = _blank_analysis_ref()
    st.session_state["ahp_weights_confirmed"] = False


def clear_uploaded_image_state() -> None:
    st.session_state["uploaded_image_name"] = ""
    st.session_state["uploaded_image_bytes"] = None
    st.session_state["uploaded_image_temp_path"] = ""
    st.session_state["uploaded_images"] = []
    st.session_state["image_records"] = []
    st.session_state["_uploaded_image_cache"] = []


def reset_pipeline_for_new_location(clear_uploaded: bool = True) -> None:
    clear_analysis_state(clear_dataset=True)
    if clear_uploaded:
        clear_uploaded_image_state()


def reset_full_pipeline() -> None:
    reset_for_new_analysis()


def logout_user() -> None:
    for key in ("logged_in", "username", "user_email", "user_role",
                "user_id", "session_id", "session_expires"):
        st.session_state[key] = False if key == "logged_in" else ""
    reset_for_new_analysis()


# ═══════════════════════════════════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════════════════════════════════

def login_user(email: str, password: str) -> bool:
    if not email or not email.strip():
        return False
    if not password:
        return False

    normalized_email = email.strip().lower()

    # Primary path: Supabase/PostgreSQL users table.
    try:
        from Wahhaj.db_connection import get_db

        with get_db() as cur:
            cur.execute(
                """SELECT user_id, name, role
                   FROM users
                   WHERE email = %s
                     AND pwd_hash = %s
                     AND is_active = TRUE""",
                (normalized_email, password),
            )
            row = cur.fetchone()

        if not row:
            return False

        st.session_state.update({
            "logged_in": True,
            "user_id": row[0],
            "username": row[1],
            "user_role": row[2],
            "user_email": normalized_email,
            "session_id": "db-session",
            "session_expires": "",
            "history_loaded": False,
        })
        return True

    except Exception as exc:
        # Local fallback keeps the app usable before secrets/Supabase are configured.
        import logging
        logging.getLogger(__name__).warning("DB login failed; using local registry fallback: %s", exc)

    User.seed_default_users()
    user = User.find_by_email(normalized_email)
    if user is None:
        return False

    try:
        session = user.login(normalized_email, password)
    except ValueError:
        return False

    st.session_state["logged_in"]       = True
    st.session_state["username"]        = user.name
    st.session_state["user_email"]      = user._email
    st.session_state["user_role"]       = user.role.value
    st.session_state["user_id"]         = user.userId
    st.session_state["session_id"]      = session.session_id
    st.session_state["session_expires"] = session.expires_at.isoformat()
    st.session_state["history_loaded"]  = False
    return True


# ═══════════════════════════════════════════════════════════════════════════
# Location / AOI helpers
# ═══════════════════════════════════════════════════════════════════════════

_AOI_HALF_DEGREE: float = 0.1


def save_selected_location(
    location_name: str,
    latitude: float,
    longitude: float,
    aoi_half_deg: float = _AOI_HALF_DEGREE,
    explicit_aoi: "AOI | None" = None,
) -> dict:
    location_dict = {
        "location_name": location_name.strip(),
        "latitude": latitude,
        "longitude": longitude,
    }
    st.session_state["selected_location"] = location_dict
    st.session_state["location_saved"] = True

    if explicit_aoi is not None:
        aoi: AOI = explicit_aoi
    else:
        aoi: AOI = (
            longitude - aoi_half_deg,
            latitude - aoi_half_deg,
            longitude + aoi_half_deg,
            latitude + aoi_half_deg,
        )

    st.session_state["aoi"] = aoi

    dataset = Dataset(
        name=location_name.strip(),
        aoi=aoi,
        images=[],
    )
    set_dataset_state(
        dataset,
        status="location_selected",
        source="session",
        image_count=0,
        aoi=aoi,
        name=location_name.strip(),
    )
    return location_dict


def get_aoi() -> "AOI | None":
    return st.session_state.get("aoi")


def get_dataset() -> "Dataset | None":
    return st.session_state.get("_dataset_cache") or st.session_state.get("dataset")


# ═══════════════════════════════════════════════════════════════════════════
# Page layout helpers
# ═══════════════════════════════════════════════════════════════════════════

def require_login(redirect: str = "pages/1_Login.py") -> None:
    if not st.session_state.get("logged_in", False):
        st.switch_page(redirect)


def render_top_home_button(target_page: str = "pages/2_Home.py") -> None:
    left, center, right = st.columns([9.6, 0.6, 1.4])
    with right:
        st.markdown('<div class="top-home-btn">', unsafe_allow_html=True)
        if st.button("Home", use_container_width=True, key=f"home_btn_{target_page}"):
            st.switch_page(target_page)
        st.markdown('</div>', unsafe_allow_html=True)


def render_footer() -> None:
    st.markdown(
        """
        <div style="
            font-family: 'Capriola', sans-serif;
            font-size: 16px;
            color: #555;
            text-align: center;
            margin-top: 20px;
            line-height: 1.6;
        ">
            Danah Alhamdi - Walah Alshwaier - Ruba Aletri - Jumanah Alharbi
            <br>
            © 2026 By PNU's CS Students
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_logo(image_path: str = "assets/wahhaj_logo.png", width: int = 520) -> None:
    path = Path(image_path)
    if path.exists():
        st.image(str(path), width=width)


def render_bg() -> None:
    st.markdown(
        """
        <div class="page-bg">
            <div class="blob tl1"></div>
            <div class="blob tl2"></div>
            <div class="blob tl3"></div>
            <div class="blob br1"></div>
            <div class="blob br2"></div>
            <div class="blob br3"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ui_icon(name: str, sz: int = 16, color: str = "currentColor") -> str:
    icons = {
        "home": (
            '<path d="M3 10.5L12 3l9 7.5"/>'
            '<path d="M5 9.5V21h14V9.5"/>'
        ),
        "logout": (
            '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>'
            '<path d="M16 17l5-5-5-5"/>'
            '<path d="M21 12H9"/>'
        ),
        "users": (
            '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
            '<circle cx="9" cy="7" r="4"/>'
            '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/>'
            '<path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
        ),
        "account": (
            '<circle cx="12" cy="8" r="4"/>'
            '<path d="M4 21a8 8 0 0 1 16 0"/>'
        ),
        "status": (
            '<path d="M4 19h16"/>'
            '<path d="M7 16V8"/>'
            '<path d="M12 16V5"/>'
            '<path d="M17 16v-4"/>'
        ),
        "history": (
            '<path d="M3 12a9 9 0 1 0 3-6.7"/>'
            '<path d="M3 3v6h6"/>'
            '<path d="M12 7v5l3 3"/>'
        ),
        "location": (
            '<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/>'
            '<circle cx="12" cy="10" r="2.5"/>'
        ),
        "delete": (
            '<path d="M3 6h18"/>'
            '<path d="M8 6V4h8v2"/>'
            '<path d="M19 6l-1 14H6L5 6"/>'
        ),
        "warning": (
            '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
            '<path d="M12 9v4"/>'
            '<path d="M12 17h.01"/>'
        ),
        "check": (
            '<path d="M20 6L9 17l-5-5"/>'
        ),
    }

    body = icons.get(name, icons["check"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{sz}" height="{sz}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" '
        f'style="display:inline-block;vertical-align:middle;flex-shrink:0;">'
        f"{body}</svg>"
    )


def apply_global_style() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Capriola&family=Inter:wght@400;500;600;700&display=swap');

        [data-testid="stSidebar"] { display: none; }
        [data-testid="stHeader"]  { background: transparent; }
        [data-testid="stToolbar"] { right: 14px; top: 10px; }

        /* ── التغيير الرئيسي: شفاف بدل #f7f7f5 ── */
        .stApp { background: #f0f2f5; }

        .main .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 1.2rem;
        }

       .page-bg {
        position: fixed; inset: 0; z-index: 0;
        pointer-events: none; overflow: hidden; background: #f0f2f5;
        }
        .blob {
            position: absolute; border-radius: 50%;
            filter: blur(120px); opacity: 0.82;
        }
        .blob.tl1 { width:420px; height:420px; left:-120px; top:-80px;  background:#91D895; }
        .blob.tl2 { width:430px; height:430px; left:120px;  top:-170px; background:#4FC3F7; }
        .blob.tl3 { width:420px; height:420px; left:-160px; top:120px;  background:#F9B233; }
        .blob.br1 { width:430px; height:430px; right:-120px; bottom:-40px;  background:#FE753F; }
        .blob.br2 { width:430px; height:430px; right:-220px; bottom:120px;  background:#0066FF; }
        .blob.br3 { width:410px; height:410px; right:80px;   bottom:-130px; background:#F9B233; opacity:0.46; }

        .section-layer { position:relative; z-index:2; }
        .home-title-space { height:30px; }

        html, body, p, li, label, span, div {
            font-size: 18px;
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        .stMarkdown p,
        .stMarkdown li {
            font-size: 18px !important;
            line-height: 1.7;
        }

        h1 { font-size: clamp(34px, 2.8vw, 46px) !important; color: #1a1a1a !important; }
        h2 { font-size: clamp(28px, 2.2vw, 38px) !important; color: #1a1a1a !important; }
        h3 { font-size: clamp(22px, 1.8vw, 30px) !important; color: #1a1a1a !important; }

        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            font-family:'Capriola',sans-serif !important;
            font-size:18px !important;
            min-height:52px !important;
        }
        div[data-testid="stSelectbox"] label,
        div[data-testid="stNumberInput"] label,
        div[data-testid="stTextArea"] label,
        div[data-testid="stRadio"] label,
        div[data-testid="stCheckbox"] label {
            font-size:18px !important;
        }

        .credits {
            text-align: center; font-family:'Capriola',sans-serif;
            color:#5A5959; font-size:clamp(24px,2.3vw,38px); line-height:1.8; margin-top:70px;
        }

        .login-title {
            font-family:'Capriola',sans-serif;
            font-size:clamp(74px,5.8vw,92px); color:#1a1a1a; line-height:1; margin-bottom:10px;
        }
        .login-subtitle {
            font-family:'Capriola',sans-serif; font-size:18px; color:#2c2c2c; margin-bottom:34px;
        }
        .field-label {
            font-family:'Capriola',sans-serif;
            font-size:clamp(28px,2.4vw,34px); color:#1a1a1a; margin-bottom:8px; margin-top:8px;
        }
        .login-card-box {
            background:rgba(255,255,255,0.68); border-radius:24px;
            backdrop-filter:blur(10px); padding:54px 50px;
            box-shadow:0 10px 34px rgba(0,0,0,0.04); min-height:560px;
        }

        div[data-testid="stTextInput"] input {
            background:#F0EEEE !important;
            color:#1a1a1a !important;
            border:1px solid #d8d4d4 !important;
            border-radius:4px !important;
            min-height:52px !important;
            font-family:'Capriola',sans-serif !important;
            font-size:18px !important;
            padding-left:14px !important;
            box-shadow:none !important;
        }
        div[data-testid="stTextInput"] input::placeholder {
            color:#999 !important;
        }
        div[data-testid="stTextInput"] label { display:none !important; }


        /* ══════ WAHHAJ BUTTONS — FORCED LARGE ══════ */
        div.stButton > button,
        div.stButton > button:focus,
        section[data-testid="stSidebar"] div.stButton > button,
        .main div.stButton > button {
            background:#0070FF !important;
            color:white !important;
            border:none !important;
            border-radius:14px !important;
            min-height:62px !important;
            height:auto !important;
            padding-top:18px !important;
            padding-bottom:18px !important;
            padding-left:32px !important;
            padding-right:32px !important;
            font-family:'Capriola',sans-serif !important;
            font-size:17px !important;
            font-weight:700 !important;
            letter-spacing:0.03em !important;
            box-shadow: 0 4px 16px rgba(0,112,255,0.38), 0 2px 6px rgba(0,0,0,0.10) !important;
            transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.12s ease !important;
            line-height: 1.4 !important;
            white-space: normal !important;
        }
        div.stButton > button > div,
        div.stButton > button p {
            font-weight:700 !important;
            font-size:17px !important;
            padding:0 !important;
            margin:0 !important;
            line-height:1.4 !important;
        }
        div.stButton > button:hover {
            background:#005fe0 !important;
            color:white !important;
            box-shadow: 0 6px 22px rgba(0,112,255,0.50), 0 2px 8px rgba(0,0,0,0.12) !important;
            transform: translateY(-1px) !important;
        }
        div.stButton > button:active {
            transform: translateY(0px) !important;
            box-shadow: 0 2px 8px rgba(0,112,255,0.30) !important;
        }
        div.stButton > button:disabled,
        div.stButton > button[disabled] {
            background:#d0d0d0 !important;
            color:#888 !important;
            border:1px solid #bbb !important;
            box-shadow:none !important;
            cursor:not-allowed !important;
            opacity:1 !important;
            transform:none !important;
        }

        div[data-testid="stDownloadButton"] button {
            font-weight:700 !important;
            letter-spacing:0.03em !important;
            padding-top:18px !important;
            padding-bottom:18px !important;
            padding-left:32px !important;
            padding-right:32px !important;
            border-radius:14px !important;
            min-height:62px !important;
            height:auto !important;
            font-size:17px !important;
        }
        div[data-testid="stDownloadButton"] button p {
            font-weight:700 !important;
            font-size:17px !important;
        }



        .sun-wrap-fixed { position:relative; width:390px; height:390px; margin:90px auto 0 auto; }
        .sun-glow {
            position:absolute; width:240px; height:240px; left:75px; top:75px;
            background:#FFA800; filter:blur(72px); border-radius:50%; opacity:0.58;
        }
        .sun-core {
            position:absolute; width:250px; height:250px; left:70px; top:70px;
            border-radius:50%;
            background:linear-gradient(38.87deg,#EE9D3E 37.22%,rgba(236,161,74,0) 78.02%),#FFE600;
            box-shadow:inset 0 1px 16px rgba(255,255,255,0.77);
        }
        .ray {
            position:absolute; width:22px; height:78px; border-radius:16px;
            background:linear-gradient(180deg,#FFE66A 0%,#F0B64A 100%);
            box-shadow:inset 0 2px 8px rgba(255,255,255,0.35);
        }
        .ray.r1{left:184px;top:0px}
        .ray.r2{right:42px;top:48px;transform:rotate(45deg)}
        .ray.r3{right:0px;top:156px;transform:rotate(90deg)}
        .ray.r4{right:42px;bottom:48px;transform:rotate(135deg)}
        .ray.r5{left:184px;bottom:0px}
        .ray.r6{left:42px;bottom:48px;transform:rotate(-135deg)}
        .ray.r7{left:0px;top:156px;transform:rotate(90deg)}
        .ray.r8{left:42px;top:48px;transform:rotate(-45deg)}

        .top-home-btn { width:120px; margin-left:auto; }
        .top-home-btn div.stButton > button {
            min-height:50px; font-size:18px; border-radius:12px;
            box-shadow: 0 4px 14px rgba(0,112,255,0.30);
            padding: 12px 18px !important;
        }

        @media(max-width:900px){
            .sun-wrap-fixed{display:none}
            .login-card-box{min-height:auto;padding:40px 28px}
            .credits{margin-top:50px}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
