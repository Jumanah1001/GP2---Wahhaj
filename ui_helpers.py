import sys
import os
import streamlit as st
from pathlib import Path

# ── Backend import ────────────────────────────────────────────────────────────
# Wahhaj/ is a sibling directory of ui_helpers.py (both live at project root).
# We add the project root to sys.path so "from Wahhaj.User import ..." works
# regardless of how Streamlit is launched.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from Wahhaj.User import User, UserRole  # noqa: E402  (import after path fix)


# ── Session state ─────────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "logged_in":        False,
        "username":         "",       # display name (e.g. "Danah Alhamdi")
        "user_email":       "",
        "user_role":        "",       # "Admin" or "Analyst"
        "user_id":          "",
        "session_id":       "",
        "session_expires":  "",       # ISO-8601 string
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ── Authentication ────────────────────────────────────────────────────────────

def login_user(email: str, password: str) -> bool:
    """
    Validates credentials against the User backend and populates
    st.session_state on success.

    Returns True on successful login, False on any failure.
    Error details are NOT exposed to the caller — the UI should show a
    generic "incorrect email or password" message to prevent enumeration.

    Flow:
        1. Ensure at least one user exists in the registry (dev seed).
        2. Find the User object by email.
        3. Call user.login(email, password) — raises ValueError on mismatch.
        4. On success, write all session fields to st.session_state.
    """
    # Guard: empty fields
    if not email or not email.strip():
        return False
    if not password:
        return False

    # Step 1 — seed dev users if registry is empty
    User.seed_default_users()

    # Step 2 — find user by email
    user = User.find_by_email(email)
    if user is None:
        return False  # email not found

    # Step 3 — delegate to the real login() method on User
    try:
        session = user.login(email, password)
    except ValueError:
        return False  # wrong password or inactive account

    # Step 4 — write session data to Streamlit session state
    st.session_state["logged_in"]       = True
    st.session_state["username"]        = user.name
    st.session_state["user_email"]      = user._email
    st.session_state["user_role"]       = user.role.value
    st.session_state["user_id"]         = user.userId
    st.session_state["session_id"]      = session.session_id
    st.session_state["session_expires"] = session.expires_at.isoformat()

    return True


def logout_user() -> None:
    """Clears all session state keys set by login_user()."""
    for key in ("logged_in", "username", "user_email", "user_role",
                "user_id", "session_id", "session_expires"):
        st.session_state[key] = "" if key != "logged_in" else False


# ── Styles & Layout ───────────────────────────────────────────────────────────

def apply_global_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Capriola&family=Inter:wght@400;500;600;700&display=swap');

        [data-testid="stSidebar"] { display: none; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { right: 14px; top: 10px; }

        .stApp {
            background: #f7f7f5;
        }

        .main .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 1.2rem;
        }

        .page-bg {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
            background: #f7f7f5;
        }

        .blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(120px);
            opacity: 0.82;
        }

        .blob.tl1 { width: 420px; height: 420px; left: -120px; top: -80px; background: #91D895; }
        .blob.tl2 { width: 430px; height: 430px; left: 120px; top: -170px; background: #4FC3F7; }
        .blob.tl3 { width: 420px; height: 420px; left: -160px; top: 120px; background: #F9B233; }

        .blob.br1 { width: 430px; height: 430px; right: -120px; bottom: -40px; background: #FE753F; }
        .blob.br2 { width: 430px; height: 430px; right: -220px; bottom: 120px; background: #0066FF; }
        .blob.br3 { width: 410px; height: 410px; right: 80px; bottom: -130px; background: #F9B233; opacity: 0.46; }

        .section-layer {
            position: relative;
            z-index: 2;
        }

        .home-title-space {
            height: 30px;
        }

        .credits {
            text-align: center;
            font-family: 'Capriola', sans-serif;
            color: #5A5959;
            font-size: clamp(20px, 2vw, 32px);
            line-height: 1.8;
            margin-top: 70px;
        }

        .login-title {
            font-family: 'Capriola', sans-serif;
            font-size: clamp(58px, 5vw, 72px);
            color: #5A5959;
            line-height: 1;
            margin-bottom: 10px;
        }

        .login-subtitle {
            font-family: 'Capriola', sans-serif;
            font-size: 15px;
            color: #5E5B5B;
            margin-bottom: 34px;
        }

        .field-label {
            font-family: 'Capriola', sans-serif;
            font-size: clamp(22px, 1.9vw, 26px);
            color: #333333;
            margin-bottom: 8px;
            margin-top: 8px;
        }

        .login-card-box {
            background: rgba(255,255,255,0.68);
            border-radius: 24px;
            backdrop-filter: blur(10px);
            padding: 54px 50px;
            box-shadow: 0 10px 34px rgba(0,0,0,0.04);
            min-height: 560px;
        }

        div[data-testid="stTextInput"] input {
            background: #F0EEEE !important;
            color: #6f6f6f !important;
            border: none !important;
            border-radius: 4px !important;
            min-height: 42px !important;
            font-family: 'Capriola', sans-serif !important;
            font-size: 13px !important;
            padding-left: 14px !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] label {
            display: none !important;
        }

        div.stButton > button {
            background: #0070FF;
            color: white;
            border: none;
            border-radius: 4px;
            min-height: 52px;
            font-family: 'Capriola', sans-serif;
            font-size: 18px;
            box-shadow: 5px 6px 4px rgba(0,0,0,0.18);
        }

        div.stButton > button:hover {
            background: #005fe0;
            color: white;
        }

        .sun-wrap-fixed {
            position: relative;
            width: 390px;
            height: 390px;
            margin: 90px auto 0 auto;
        }

        .sun-glow {
            position: absolute;
            width: 240px;
            height: 240px;
            left: 75px;
            top: 75px;
            background: #FFA800;
            filter: blur(72px);
            border-radius: 50%;
            opacity: 0.58;
        }

        .sun-core {
            position: absolute;
            width: 250px;
            height: 250px;
            left: 70px;
            top: 70px;
            border-radius: 50%;
            background: linear-gradient(38.87deg, #EE9D3E 37.22%, rgba(236, 161, 74, 0) 78.02%), #FFE600;
            box-shadow: inset 0 1px 16px rgba(255,255,255,0.77);
        }

        .ray {
            position: absolute;
            width: 22px;
            height: 78px;
            border-radius: 16px;
            background: linear-gradient(180deg, #FFE66A 0%, #F0B64A 100%);
            box-shadow: inset 0 2px 8px rgba(255,255,255,0.35);
        }

        .ray.r1 { left: 184px; top: 0px; }
        .ray.r2 { right: 42px; top: 48px; transform: rotate(45deg); }
        .ray.r3 { right: 0px; top: 156px; transform: rotate(90deg); }
        .ray.r4 { right: 42px; bottom: 48px; transform: rotate(135deg); }
        .ray.r5 { left: 184px; bottom: 0px; }
        .ray.r6 { left: 42px; bottom: 48px; transform: rotate(-135deg); }
        .ray.r7 { left: 0px; top: 156px; transform: rotate(90deg); }
        .ray.r8 { left: 42px; top: 48px; transform: rotate(-45deg); }

        .top-home-btn {
            width: 84px;
            margin-left: auto;
        }

        .top-home-btn div.stButton > button {
            min-height: 44px;
            font-size: 20px;
            border-radius: 12px;
            box-shadow: none;
        }

        @media (max-width: 900px) {
            .sun-wrap-fixed { display: none; }
            .login-card-box { min-height: auto; padding: 40px 28px; }
            .credits { margin-top: 50px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_bg():
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


def show_logo(image_path="assets/wahhaj_logo.png", width=520):
    path = Path(image_path)
    if path.exists():
        st.image(str(path), width=width)


def save_selected_location(location_name, latitude, longitude):
    st.session_state["selected_location"] = {
        "location_name": location_name,
        "latitude":      latitude,
        "longitude":     longitude,
    }
    return st.session_state["selected_location"]


def render_top_home_button(target_page: str = "pages/2_Home.py"):
    left, center, right = st.columns([10.2, 0.8, 1.0])
    with right:
        if st.button("🏠", use_container_width=True, key=f"home_btn_{target_page}"):
            st.switch_page(target_page)


def render_footer():
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
            Danah Alhamdi - Walah Alshwaier - Ruba Aletri - Jumanah Alharbi
            <br>
            © 2025 By PNU's CS Students
        </div>
        """,
        unsafe_allow_html=True,
    )