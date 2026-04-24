"""
pages/2_Home.py
===============
Dashboard home page — redesigned UI only.
Keeps the existing backend/session logic intact:
- login guard
- start analysis reset
- admin/ranked/logout navigation
- analysis history restore
"""

import re
from html import escape

import streamlit as st

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    show_logo,
    logout_user,
    render_footer,
    get_analysis_history,
    restore_analysis_history_entry,
    reset_for_new_analysis,
    ui_icon,
)

st.set_page_config(page_title="Home", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

username = st.session_state.get("username", "—")
user_email = st.session_state.get("user_email", "—")
user_role = st.session_state.get("user_role", "Analyst")
is_admin = user_role == "Admin"
history = get_analysis_history() or []


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _safe_location_name(raw: str, max_len: int = 62) -> str:
    if not raw:
        return "Unknown Location"
    safe = re.sub(r"[^\w\s\u0600-\u06FF\-,.()/\u00B0]", " ", str(raw))
    safe = re.sub(r"\s+", " ", safe).strip()
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip(" ,-") + "…"
    return safe or "Unknown Location"


def _fmt_coord(value, suffix: str) -> str:
    try:
        return f"{float(value):.4f}°{suffix}"
    except Exception:
        return "—"


def _fmt_history_meta(entry: dict) -> str:
    lat = _fmt_coord(entry.get("lat"), "N")
    lon = _fmt_coord(entry.get("lon"), "E")
    analysed = str(entry.get("analysed_at") or "—")
    return f"{lat}, {lon} · Done · {analysed}"


def _member_since() -> str:
    # Keep it flexible in case the backend later stores a real user creation date.
    return (
        st.session_state.get("member_since")
        or st.session_state.get("user_created_at")
        or "2026-04-20"
    )


def _render_history(history_items: list) -> None:
    if not history_items:
        # The title is now inside the card itself.
        st.markdown(
            f"""
            <div class="history-card fixed-width">
                <div class="history-card-head">
                    <div>
                        <div class="section-title">{ui_icon('history', 18, '#1a1a1a')}<span>Analysis History</span></div>
                        <div class="section-subtitle">All previous site analyses</div>
                    </div>
                </div>
                <div class="empty-history-inner">
                    <div class="empty-icon">{ui_icon('history', 34, '#9EC5FE')}</div>
                    <div class="empty-copy">
                        <div class="empty-title">No analysis results yet</div>
                        <div class="empty-text">Start your first solar site suitability analysis to see results and reports here.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="history-card fixed-width history-list-card">
            <div class="history-card-head">
                <div>
                    <div class="section-title">{ui_icon('history', 18, '#1a1a1a')}<span>Analysis History</span></div>
                    <div class="section-subtitle">All previous site analyses</div>
                </div>
                <div class="history-filter">{ui_icon('status', 15, '#334155')}<span>Most Recent</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Real history rows. We use Streamlit bordered containers so the button remains functional.
    for idx, entry in enumerate(history_items):
        loc_label = escape(_safe_location_name(entry.get("location_name", "Unknown")))
        meta = escape(_fmt_history_meta(entry))
        run_id = entry.get("run_id", idx)

        with st.container(border=True):
            row_left, row_btn = st.columns([5.6, 1.35], gap="large")
            with row_left:
                st.markdown(
                    f"""
                    <div class="history-row-content">
                        <div class="pin-bubble">{ui_icon('location', 24, '#0070FF')}</div>
                        <div>
                            <div class="history-location">{loc_label}</div>
                            <div class="history-meta">{meta}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with row_btn:
                st.markdown('<div class="view-report-space"></div>', unsafe_allow_html=True)
                if st.button(
                    ":material/article: View Report",
                    key=f"hist_open_{idx}_{run_id}",
                    use_container_width=True,
                ):
                    ok = restore_analysis_history_entry(entry)
                    if ok:
                        st.switch_page("pages/8_Final_Report.py")
                    else:
                        st.warning("This saved entry cannot be reopened in the current session yet.")


# ─────────────────────────────────────────────────────────────
# Page-specific CSS
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Page spacing */
.home-page-wrap {
    position: relative;
    z-index: 2;
    padding-top: 4px;
}
.fixed-width {
    width: min(1120px, 92vw);
    margin-left: auto;
    margin-right: auto;
}

/* Top navigation */
.nav-spacer { height: 12px; }

/* Hero */
.hero-block {
    text-align: center;
    margin: 18px auto 36px auto;
}
.hero-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(42px, 4vw, 58px);
    line-height: 1.05;
    color: #1a1a1a;
    margin: 4px auto 10px auto;
    letter-spacing: 0.01em;
    text-align: center;
    width: 100%;
}
.hero-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    color: #5E5B5B;
    margin-bottom: 18px;
    text-align: center;
    width: 100%;
}

/* Keep the main start button large but not huge */
div[data-testid="stHorizontalBlock"] div.stButton > button {
    white-space: normal !important;
}

/* Account card — real HTML card, not floating text */
.account-card {
    background: rgba(255,255,255,0.88);
    border: 1px solid rgba(220,226,235,0.95);
    border-radius: 24px;
    box-shadow: 0 10px 28px rgba(15,23,42,0.07);
    padding: 24px 28px;
    margin-top: 10px;
    margin-bottom: 28px;
    backdrop-filter: blur(12px);
}
.account-heading {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Capriola', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: #1a1a1a;
    margin-bottom: 20px;
}
.account-grid {
    display: grid;
    grid-template-columns: 1.25fr 1fr 1fr;
    gap: 22px;
    align-items: center;
}
.account-item {
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 72px;
}
.account-icon {
    width: 58px;
    height: 58px;
    border-radius: 18px;
    background: #EEF5FF;
    color: #0070FF;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}
.account-label {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    font-weight: 700;
    color: #75829B;
    margin-bottom: 5px;
}
.account-value {
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    font-weight: 800;
    color: #172033;
}
.account-muted {
    font-size: 13px;
    font-weight: 600;
    color: #536078;
    margin-top: 4px;
}
.role-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #FFEDD5;
    color: #C2410C;
    border-radius: 999px;
    padding: 5px 13px;
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
    font-weight: 800;
}
.role-pill.user {
    background: #E8F3FF;
    color: #0070FF;
}

/* History card */
.history-card {
    background: rgba(255,255,255,0.84);
    border: 1px solid rgba(220,226,235,0.95);
    border-radius: 24px;
    box-shadow: 0 10px 28px rgba(15,23,42,0.06);
    padding: 24px 28px 28px 28px;
    margin-top: 16px;
    margin-bottom: 14px;
    backdrop-filter: blur(12px);
}
.history-card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 22px;
}
.section-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Capriola', sans-serif;
    font-size: 24px;
    font-weight: 800;
    color: #1a1a1a;
    line-height: 1.2;
}
.section-subtitle {
    font-family: 'Capriola', sans-serif;
    color: #5E5B5B;
    font-size: 14px;
    margin-top: 5px;
}
.history-filter {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 42px;
    padding: 0 18px;
    border-radius: 13px;
    border: 1px solid #D7E1EF;
    background: rgba(255,255,255,0.9);
    color: #334155;
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    font-weight: 800;
}
.empty-history-inner {
    min-height: 150px;
    border: 1px dashed rgba(196,207,222,0.95);
    border-radius: 20px;
    background: rgba(255,255,255,0.58);
    padding: 26px 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 34px;
}
.empty-icon {
    width: 92px;
    height: 92px;
    border-radius: 24px;
    background: #F1F7FF;
    border: 1px solid #D9E9FF;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}
.empty-copy { max-width: 460px; }
.empty-title {
    font-family: 'Capriola', sans-serif;
    font-size: 24px;
    font-weight: 800;
    color: #172033;
    margin-bottom: 10px;
}
.empty-text {
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    line-height: 1.7;
    color: #637083;
}

/* Streamlit bordered containers used as history cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    width: min(1120px, 92vw) !important;
    margin: 0 auto 14px auto !important;
    background: rgba(255,255,255,0.86) !important;
    border: 1px solid rgba(220,226,235,0.95) !important;
    border-radius: 22px !important;
    box-shadow: 0 7px 20px rgba(15,23,42,0.055) !important;
    padding: 0 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 18px 24px !important;
}
.history-row-content {
    display: flex;
    align-items: center;
    gap: 18px;
    min-height: 76px;
}
.pin-bubble {
    width: 58px;
    height: 58px;
    border-radius: 19px;
    background: #EEF5FF;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}
.history-location {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    font-weight: 800;
    color: #172033;
    margin-bottom: 8px;
}
.history-meta {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #64748B;
}
.view-report-space {
    height: 13px;
}

/* Make history buttons compact so they don't stretch the cards */
div[data-testid="stVerticalBlockBorderWrapper"] div.stButton > button {
    min-height: 48px !important;
    padding: 12px 18px !important;
    border-radius: 13px !important;
    font-size: 14px !important;
    box-shadow: none !important;
    background: white !important;
    color: #0070FF !important;
    border: 2px solid #0070FF !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] div.stButton > button p,
div[data-testid="stVerticalBlockBorderWrapper"] div.stButton > button > div {
    font-size: 14px !important;
    color: #0070FF !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] div.stButton > button:hover {
    background: #EEF6FF !important;
    transform: translateY(-1px) !important;
}

@media (max-width: 900px) {
    .account-grid { grid-template-columns: 1fr; gap: 14px; }
    .empty-history-card { flex-direction: column; text-align: center; padding: 28px 22px; }
    .hero-title { font-size: 38px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────
st.markdown('<div class="home-page-wrap">', unsafe_allow_html=True)

# Top navigation buttons
nav_left, nav_mid, nav_right = st.columns([4.8, 1.1, 2.15], gap="medium")
with nav_right:
    if is_admin:
        btn_a, btn_b, btn_c = st.columns([1, 1, 1], gap="small")
        with btn_a:
            if st.button(":material/group: Admin", use_container_width=True):
                st.switch_page("pages/9_Add_New_User.py")
        with btn_b:
            if st.button(":material/bar_chart: Ranked", use_container_width=True):
                st.switch_page("pages/7_Ranked_Results.py")
        with btn_c:
            if st.button(":material/logout: Logout", use_container_width=True):
                logout_user()
                st.switch_page("pages/1_Login.py")
    else:
        btn_a, btn_b = st.columns([1, 1], gap="small")
        with btn_a:
            if st.button(":material/bar_chart: Ranked", use_container_width=True):
                st.switch_page("pages/7_Ranked_Results.py")
        with btn_b:
            if st.button(":material/logout: Logout", use_container_width=True):
                logout_user()
                st.switch_page("pages/1_Login.py")

# Hero
st.markdown('<div class="hero-block">', unsafe_allow_html=True)
logo_l, logo_c, logo_r = st.columns([2.6, 1.0, 2.6])
with logo_c:
    show_logo(width=170)
st.markdown('<div class="hero-title">Welcome to WAHHAJ</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Start your journey toward smarter solar site selection</div>',
    unsafe_allow_html=True,
)
start_l, start_c, start_r = st.columns([2.65, 1.7, 2.65])
with start_c:
    if st.button(":material/wb_sunny: Start New Analysis", use_container_width=True):
        reset_for_new_analysis()
        st.switch_page("pages/3_Choose_Location.py")
st.markdown('</div>', unsafe_allow_html=True)

# Account card appears in both states
role_class = "role-pill" if is_admin else "role-pill user"
st.markdown(
    f"""
    <div class="account-card fixed-width">
        <div class="account-heading">{ui_icon('account', 19, '#1a1a1a')}<span>Account</span></div>
        <div class="account-grid">
            <div class="account-item">
                <div class="account-icon">{ui_icon('account', 26, '#0070FF')}</div>
                <div>
                    <div class="account-value">{escape(username)}</div>
                    <div class="account-muted">{escape(user_email)}</div>
                </div>
            </div>
            <div class="account-item">
                <div class="account-icon">{ui_icon('status', 24, '#0070FF')}</div>
                <div>
                    <div class="account-label">Role</div>
                    <span class="{role_class}">{escape(user_role)}</span>
                </div>
            </div>
            <div class="account-item">
                <div class="account-icon">{ui_icon('history', 24, '#0070FF')}</div>
                <div>
                    <div class="account-label">Member Since</div>
                    <div class="account-value">{escape(str(_member_since()))}</div>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

_render_history(history)

st.markdown('</div>', unsafe_allow_html=True)
render_footer()
