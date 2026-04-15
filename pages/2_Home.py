"""
pages/2_Home.py
===============
Dashboard home page shown after login.

Fixes applied
-------------
- Account card now shows real username, email, and role from session_state
- Logout button wired to logout_user() + redirects to login
- Admin link shown only when user_role == "Admin"
- Saved analyses count reads from real session_state keys
- "View Saved Results" navigates to 8_Ranked_Results.py if analysis exists,
  otherwise shows an informative message
- "Start Analysis" still goes to 3_Choose_Location.py (correct)
"""
import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    show_logo,
    logout_user,
)

st.set_page_config(page_title="Home", layout="wide")
init_state()
apply_global_style()
render_bg()

# ── auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

# ── read real session values ──────────────────────────────────────────────────
username     = st.session_state.get("username", "—")
user_email   = st.session_state.get("user_email", "—")
user_role    = st.session_state.get("user_role", "Analyst")
is_admin     = user_role == "Admin"

# Count saved analyses (1 if analysis_run exists, 0 otherwise)
has_run      = st.session_state.get("analysis_run") is not None
has_location = st.session_state.get("location_saved", False)
has_image    = bool(st.session_state.get("uploaded_image_name", ""))
saved_count  = 1 if has_run else 0

# ── styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.home-page { position:relative; z-index:2; padding-top:8px; }
.page-title {
    font-family:'Capriola',sans-serif; font-size:clamp(34px,3vw,44px);
    color:#5A5959; text-align:center; margin-bottom:8px; line-height:1.1;
}
.page-subtitle {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#5E5B5B; text-align:center; margin-bottom:18px;
}
.card-box {
    background:rgba(255,255,255,0.60); border-radius:18px;
    backdrop-filter:blur(8px); box-shadow:0 8px 24px rgba(0,0,0,0.04);
    padding:20px 22px; min-height:175px;
}
.card-title { font-family:'Capriola',sans-serif; font-size:20px; color:#4f4f4f; margin-bottom:14px; }
.card-text  { font-family:'Capriola',sans-serif; font-size:15px; color:#666666; line-height:1.9; }
.badge-role {
    display:inline-block; padding:2px 10px; border-radius:12px;
    font-size:12px; font-weight:700; font-family:'Capriola',sans-serif;
    background:#e6f9ee; color:#1a9e52;
}
.badge-admin { background:#fff0e6; color:#c8601a; }
.footer-note {
    font-family:'Capriola',sans-serif; font-size:13px; color:#666666;
    text-align:center; margin-top:28px; line-height:1.6;
}
div.stButton > button {
    background:#0070FF; color:white; border:none; border-radius:6px;
    min-height:46px; font-family:'Capriola',sans-serif; font-size:16px;
    box-shadow:4px 5px 4px rgba(0,0,0,0.16);
}
div.stButton > button:hover { background:#005fe0; color:white; }
div.stButton > button.logout-btn { background:#e74c3c !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="home-page">', unsafe_allow_html=True)

# ── top bar: logout + admin ───────────────────────────────────────────────────
top_l, top_mid, top_r = st.columns([5, 3, 2])
with top_r:
    logout_cols = st.columns([1, 1]) if is_admin else [None, st.columns([1])[0]]
    if is_admin:
        with logout_cols[0]:
            if st.button("👥 Admin", use_container_width=True):
                st.switch_page("pages/10_Add_New_User.py")
        with logout_cols[1]:
            if st.button("🚪 Logout", use_container_width=True):
                logout_user()
                st.switch_page("pages/1_Login.py")
    else:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.switch_page("pages/1_Login.py")

# ── logo ──────────────────────────────────────────────────────────────────────
_, logo_col, _ = st.columns([2.5, 1.0, 2.5])
with logo_col:
    show_logo(width=175)

# ── title ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Welcome to Wahhaj</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Start your journey toward smarter solar site selection.</div>',
    unsafe_allow_html=True,
)

# ── start analysis button ─────────────────────────────────────────────────────
_, start_col, _ = st.columns([2.8, 1.8, 2.8])
with start_col:
    if st.button("Start Analysis", use_container_width=True):
        st.switch_page("pages/3_Choose_Location.py")

st.write("")
st.write("")

# ── info cards ────────────────────────────────────────────────────────────────
left_space, account_col, gap, saved_col, right_space = st.columns(
    [0.9, 2.9, 0.35, 2.9, 0.9]
)

with account_col:
    badge_cls   = "badge-role badge-admin" if is_admin else "badge-role"
    loc_name    = st.session_state.get("selected_location", {}).get("location_name", "—")
    loc_display = f"Last location: {loc_name}" if loc_name else "No location selected yet"

    st.markdown(
        f"""
        <div class="card-box">
            <div class="card-title">👤 Account Details</div>
            <div class="card-text">
                Name: {username}<br>
                Email: {user_email}<br>
                Role: <span class="{badge_cls}">{user_role}</span><br>
                Status: Active ✅<br>
                <span style='font-size:13px;color:#aaa;'>{loc_display}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with saved_col:
    # Show pipeline progress as "saved analyses"
    pipeline_items = []
    if has_location:
        pipeline_items.append("✅ Location saved")
    if has_image:
        pipeline_items.append("✅ Image uploaded")
    if st.session_state.get("extractor"):
        pipeline_items.append("✅ Env. data fetched")
    if has_run:
        pipeline_items.append("✅ Analysis complete")

    progress_html = "<br>".join(pipeline_items) if pipeline_items else "No active analysis"

    st.markdown(
        f"""
        <div class="card-box">
            <div class="card-title">📄 Analysis Progress</div>
            <div class="card-text">{progress_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # View Results button (only active when analysis exists)
    st.write("")
    if has_run:
        if st.button("View Analysis Results →", use_container_width=True):
            st.switch_page("pages/8_Ranked_Results.py")
    elif has_location or has_image:
        if st.button("Continue Pipeline →", use_container_width=True):
            # Resume from the furthest completed step
            if st.session_state.get("extractor"):
                st.switch_page("pages/6_Run_Analysis.py")
            elif has_image:
                st.switch_page("pages/4_Environmental_Data.py")
            else:
                st.switch_page("pages/4_Upload_Image.py")

# ── footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="footer-note">
        Danah Alhamdi - Walah Alshwaier - Ruba Aletri - Jumanah Alharbi
        <br>
        © 2025 By PNU's CS Students
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)