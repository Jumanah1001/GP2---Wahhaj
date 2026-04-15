"""
ui_helpers.py
=============
Shared Streamlit helpers for WAHHAJ.

Exports
-------
init_state()              — initialise all session_state keys
login_user()              — real auth via User backend
logout_user()             — clear session
save_selected_location()  — persist location + compute AOI + create Dataset
get_aoi()                 — accessor for downstream pages
get_dataset()             — accessor for downstream pages
apply_global_style()      — global CSS
render_bg()               — animated blob background
show_logo()               — logo image
render_top_home_button()  — home 🏠 button
render_footer()           — credits footer
"""

import sys
import os
import streamlit as st
from pathlib import Path

# ── sys.path fix ─────────────────────────────────────────────────────────────
# Ensure the project root is importable regardless of how Streamlit is launched.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from Wahhaj.User import User, UserRole          # noqa: E402
from Wahhaj.models import AOI                   # noqa: E402
from Wahhaj.FeatureExtractor import Dataset     # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Session State
# ═══════════════════════════════════════════════════════════════════════════

def init_state() -> None:
    """
    Initialise every session_state key used across the app.
    Only sets a key when it does not yet exist, so navigation never resets
    live data.
    """
    defaults: dict = {
        # ── Auth ──────────────────────────────────────────────────────────
        "logged_in":        False,
        "username":         "",          # display name (e.g. "Danah Alhamdi")
        "user_email":       "",
        "user_role":        "",          # "Admin" or "Analyst"
        "user_id":          "",
        "session_id":       "",
        "session_expires":  "",          # ISO-8601

        # ── Location / AOI ────────────────────────────────────────────────
        "selected_location": {
            "location_name": "",
            "latitude":      None,
            "longitude":     None,
        },
        "location_saved":   False,
        "aoi":              None,        # (lon_min, lat_min, lon_max, lat_max)
        "dataset":          None,        # FeatureExtractor.Dataset — pipeline carrier

        # ── Upload ────────────────────────────────────────────────────────
        "uploaded_image_name":      "",
        "uploaded_image_bytes":     None,
        "uploaded_image_temp_path": "",

        # ── Pipeline ──────────────────────────────────────────────────────
        "extractor":              None,  # FeatureExtractor instance after env fetch
        "ahp_weights_confirmed":  False,
        "analysis_run":           None,  # AnalysisRun instance after execution
        "report_obj":             None,  # Report instance

        # ── Admin (in-memory user list) ────────────────────────────────────
        "users": None,                   # populated lazily by admin page
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ═══════════════════════════════════════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════════════════════════════════════

def login_user(email: str, password: str) -> bool:
    """
    Validate credentials against the User backend and populate
    st.session_state on success.

    Flow
    ----
    1. Seed dev users into User._user_registry if it is empty.
    2. Find the User object by email (find_by_email classmethod).
    3. Call user.login(email, password) — raises ValueError on mismatch.
    4. Write all session fields on success.

    Returns True on success, False on any failure.
    Never leaks which field (email vs password) was wrong.
    """
    if not email or not email.strip():
        return False
    if not password:
        return False

    # Ensure at least the dev seed users exist
    User.seed_default_users()

    user = User.find_by_email(email)
    if user is None:
        return False

    try:
        session = user.login(email, password)
    except ValueError:
        return False

    # ── populate session ───────────────────────────────────────────────────
    st.session_state["logged_in"]       = True
    st.session_state["username"]        = user.name
    st.session_state["user_email"]      = user._email
    st.session_state["user_role"]       = user.role.value
    st.session_state["user_id"]         = user.userId
    st.session_state["session_id"]      = session.session_id
    st.session_state["session_expires"] = session.expires_at.isoformat()

    return True


def logout_user() -> None:
    """Clear all auth + pipeline session keys."""
    for key in ("logged_in", "username", "user_email", "user_role",
                "user_id", "session_id", "session_expires"):
        st.session_state[key] = False if key == "logged_in" else ""

    st.session_state["selected_location"] = {
        "location_name": "", "latitude": None, "longitude": None
    }
    for key in ("location_saved", "aoi", "dataset", "uploaded_image_name",
                "uploaded_image_bytes", "uploaded_image_temp_path",
                "extractor", "ahp_weights_confirmed", "analysis_run", "report_obj"):
        st.session_state[key] = False if key == "location_saved" else None


# ═══════════════════════════════════════════════════════════════════════════
# Location / AOI helpers
# ═══════════════════════════════════════════════════════════════════════════

# Half-size of the AOI bounding box around the chosen point (degrees).
# 0.1° ≈ 11 km at Saudi latitudes — reasonable UAV survey footprint.
_AOI_HALF_DEGREE: float = 0.1


def save_selected_location(
    location_name: str,
    latitude: float,
    longitude: float,
    aoi_half_deg: float = _AOI_HALF_DEGREE,
) -> dict:
    """
    Persist the chosen location and create the two backend objects the
    pipeline depends on.

    Side-effects
    ------------
    st.session_state["selected_location"]  — human-readable dict
    st.session_state["location_saved"]     — True
    st.session_state["aoi"]                — (lon_min, lat_min, lon_max, lat_max)
        consumed by ExternalDataSourceAdapter.fetchGHI / fetchLST / …
        and by AnalysisRun._extract_candidates
    st.session_state["dataset"]            — FeatureExtractor.Dataset
        the single data carrier; upload page appends UAVImages to it;
        run-analysis page passes it to AnalysisRun.execute(dataset)

    Returns the saved location dict (for UI confirmation).
    """
    location_dict = {
        "location_name": location_name.strip(),
        "latitude":      latitude,
        "longitude":     longitude,
    }
    st.session_state["selected_location"] = location_dict
    st.session_state["location_saved"]    = True

    # AOI = (lon_min, lat_min, lon_max, lat_max)
    aoi: AOI = (
        longitude - aoi_half_deg,
        latitude  - aoi_half_deg,
        longitude + aoi_half_deg,
        latitude  + aoi_half_deg,
    )
    st.session_state["aoi"] = aoi

    # Dataset — recreated whenever location changes so AOI stays in sync
    dataset = Dataset(
        name   = location_name.strip(),
        aoi    = aoi,
        images = [],
    )
    st.session_state["dataset"] = dataset

    return location_dict


def get_aoi() -> "AOI | None":
    """
    Return the current AOI tuple or None if no location has been saved.

    Usage in pages 4_Environmental_Data.py, 6_Run_Analysis.py:
        aoi = get_aoi()
        if aoi is None:
            st.warning("Please choose a location first.")
            st.stop()
    """
    return st.session_state.get("aoi")


def get_dataset() -> "Dataset | None":
    """
    Return the current Dataset (pipeline data carrier) or None.

    Usage:
        dataset = get_dataset()
        # upload page:
        dataset.images.append(uav_image)
        # run-analysis page:
        run.execute(get_dataset())
    """
    return st.session_state.get("dataset")


# ═══════════════════════════════════════════════════════════════════════════
# Page layout helpers
# ═══════════════════════════════════════════════════════════════════════════

def require_login(redirect: str = "pages/1_Login.py") -> None:
    """
    Guard helper — call at the top of any protected page.
    Redirects to login if session is not authenticated.
    """
    if not st.session_state.get("logged_in", False):
        st.switch_page(redirect)


def render_top_home_button(target_page: str = "pages/2_Home.py") -> None:
    """Render a small 🏠 button aligned to the top-right."""
    left, center, right = st.columns([10.2, 0.8, 1.0])
    with right:
        if st.button("🏠", use_container_width=True,
                     key=f"home_btn_{target_page}"):
            st.switch_page(target_page)


def render_footer() -> None:
    """Credits footer."""
    st.markdown(
        """
        <div style="
            font-family: 'Capriola', sans-serif;
            font-size: 13px;
            color: #666666;
            text-align: center;
            margin-top: 20px;
            line-height: 1.6;
        ">
            Danah Alhamdi - Walah Alshwair - Ruba Aletri - Jumanah Alharbi
            <br>
            © 2025 By PNU's CS Students
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


def apply_global_style() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Capriola&family=Inter:wght@400;500;600;700&display=swap');

        [data-testid="stSidebar"] { display: none; }
        [data-testid="stHeader"]  { background: transparent; }
        [data-testid="stToolbar"] { right: 14px; top: 10px; }

        .stApp { background: #f7f7f5; }

        .main .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 1.2rem;
        }

        .page-bg {
            position: fixed; inset: 0; z-index: 0;
            pointer-events: none; overflow: hidden; background: #f7f7f5;
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

        .credits {
            text-align: center; font-family:'Capriola',sans-serif;
            color:#5A5959; font-size:clamp(20px,2vw,32px); line-height:1.8; margin-top:70px;
        }

        .login-title {
            font-family:'Capriola',sans-serif;
            font-size:clamp(58px,5vw,72px); color:#5A5959; line-height:1; margin-bottom:10px;
        }
        .login-subtitle {
            font-family:'Capriola',sans-serif; font-size:15px; color:#5E5B5B; margin-bottom:34px;
        }
        .field-label {
            font-family:'Capriola',sans-serif;
            font-size:clamp(22px,1.9vw,26px); color:#333333; margin-bottom:8px; margin-top:8px;
        }
        .login-card-box {
            background:rgba(255,255,255,0.68); border-radius:24px;
            backdrop-filter:blur(10px); padding:54px 50px;
            box-shadow:0 10px 34px rgba(0,0,0,0.04); min-height:560px;
        }

        div[data-testid="stTextInput"] input {
            background:#F0EEEE !important; color:#6f6f6f !important;
            border:none !important; border-radius:4px !important;
            min-height:42px !important; font-family:'Capriola',sans-serif !important;
            font-size:13px !important; padding-left:14px !important; box-shadow:none !important;
        }
        div[data-testid="stTextInput"] label { display:none !important; }

        div.stButton > button {
            background:#0070FF; color:white; border:none; border-radius:4px;
            min-height:52px; font-family:'Capriola',sans-serif; font-size:18px;
            box-shadow:5px 6px 4px rgba(0,0,0,0.18);
        }
        div.stButton > button:hover { background:#005fe0; color:white; }

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

        .top-home-btn { width:84px; margin-left:auto; }
        .top-home-btn div.stButton > button { min-height:44px; font-size:20px; border-radius:12px; box-shadow:none; }

        @media(max-width:900px){
            .sun-wrap-fixed{display:none}
            .login-card-box{min-height:auto;padding:40px 28px}
            .credits{margin-top:50px}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )