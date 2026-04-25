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
    return (
        st.session_state.get("member_since")
        or st.session_state.get("user_created_at")
        or "2026-04-20"
    )


def _render_history(history_items: list) -> None:
    """
    Renders Analysis History as one real Streamlit keyed card.
    This keeps the title, filter, rows, and buttons inside the same visual card.
    """

    with st.container(key="home_history_shell"):
        head_left, head_right = st.columns([5.2, 1.35], gap="large")

        with head_left:
            history_head_html = f"""
<div class="history-head-copy">
<div class="section-title">
{ui_icon('history', 18, '#1a1a1a')}
<span>Analysis History</span>
</div>
<div class="section-subtitle">All previous site analyses</div>
</div>
""".strip()
            st.markdown(history_head_html, unsafe_allow_html=True)

        with head_right:
            if history_items:
                history_filter_html = f"""
<div class="history-filter-wrap">
<div class="history-filter">
{ui_icon('status', 15, '#334155')}
<span>Most Recent</span>
</div>
</div>
""".strip()
                st.markdown(history_filter_html, unsafe_allow_html=True)

        if not history_items:
            empty_history_html = f"""
<div class="empty-history-inner">
<div class="empty-icon">{ui_icon('history', 34, '#9EC5FE')}</div>
<div class="empty-copy">
<div class="empty-title">No analysis results yet</div>
<div class="empty-text">Start your first solar site suitability analysis to see results and reports here.</div>
</div>
</div>
""".strip()
            st.markdown(empty_history_html, unsafe_allow_html=True)
            return

        st.markdown('<div class="history-list-gap"></div>', unsafe_allow_html=True)

        for idx, entry in enumerate(history_items):
            loc_label = escape(_safe_location_name(entry.get("location_name", "Unknown")))
            meta = escape(_fmt_history_meta(entry))
            run_id = entry.get("run_id", idx)

            with st.container(key=f"home_history_row_{idx}"):
                row_left, row_btn = st.columns([5.4, 1.45], gap="large")

                with row_left:
                    row_html = f"""
<div class="history-row-content">
<div class="pin-bubble">{ui_icon('location', 24, '#0070FF')}</div>
<div class="history-row-text">
<div class="history-location">{loc_label}</div>
<div class="history-meta">{meta}</div>
</div>
</div>
""".strip()
                    st.markdown(row_html, unsafe_allow_html=True)

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

div[data-testid="stHorizontalBlock"] div.stButton > button {
    white-space: normal !important;
}

/* Account card */
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

/* Analysis History main card */
div[class*="st-key-home_history_shell"] {
    width: min(1120px, 92vw) !important;
    margin: 16px auto 14px auto !important;
    background: rgba(255,255,255,0.84) !important;
    border: 1px solid rgba(220,226,235,0.95) !important;
    border-radius: 24px !important;
    box-shadow: 0 10px 28px rgba(15,23,42,0.06) !important;
    padding: 24px 28px 26px 28px !important;
    backdrop-filter: blur(12px);
}

.history-head-copy {
    padding-top: 2px;
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

.history-filter-wrap {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    padding-top: 3px;
}

.history-filter {
    display: inline-flex;
    align-items: center;
    justify-content: center;
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
    white-space: nowrap;
}

.history-list-gap {
    height: 16px;
}

/* Empty history */
.empty-history-inner {
    min-height: 150px;
    margin-top: 20px;
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

.empty-copy {
    max-width: 460px;
}

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

/* Real history rows */
div[class*="st-key-home_history_row_"] {
    background: rgba(255,255,255,0.78) !important;
    border: 1px solid rgba(220,226,235,0.95) !important;
    border-radius: 20px !important;
    box-shadow: 0 5px 16px rgba(15,23,42,0.045) !important;
    padding: 16px 20px !important;
    margin: 0 0 12px 0 !important;
}

.history-row-content {
    display: flex;
    align-items: center;
    gap: 18px;
    min-height: 60px;
}

.pin-bubble {
    width: 56px;
    height: 56px;
    border-radius: 18px;
    background: #EEF5FF;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}

.history-row-text {
    min-width: 0;
}

.history-location {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    font-weight: 800;
    color: #172033;
    margin-bottom: 8px;
    line-height: 1.2;
}

.history-meta {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    font-weight: 600;
    color: #64748B;
    line-height: 1.35;
}

.view-report-space {
    height: 6px;
}

/* View Report buttons only */
div[class*="st-key-hist_open_"] button {
    min-height: 46px !important;
    padding: 10px 16px !important;
    border-radius: 14px !important;
    font-size: 14px !important;
    font-weight: 800 !important;
    box-shadow: 0 6px 16px rgba(0,112,255,0.18) !important;
    background: #0070FF !important;
    color: white !important;
    border: 1px solid #0070FF !important;
}

div[class*="st-key-hist_open_"] button p,
div[class*="st-key-hist_open_"] button > div {
    font-size: 14px !important;
    font-weight: 800 !important;
    color: white !important;
}

div[class*="st-key-hist_open_"] button:hover {
    background: #0065E6 !important;
    border-color: #0065E6 !important;
    transform: translateY(-1px) !important;
}

@media (max-width: 900px) {
    .account-grid {
        grid-template-columns: 1fr;
        gap: 14px;
    }

    .empty-history-inner {
        flex-direction: column;
        text-align: center;
        padding: 28px 22px;
    }

    .hero-title {
        font-size: 38px;
    }

    div[class*="st-key-home_history_shell"] {
        padding: 22px 20px 24px 20px !important;
    }

    .history-filter-wrap {
        justify-content: flex-start;
        padding-top: 12px;
    }

    div[class*="st-key-home_history_row_"] {
        padding: 16px !important;
    }

    .history-location {
        font-size: 16px;
    }

    .history-meta {
        font-size: 12px;
    }
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

st.markdown("</div>", unsafe_allow_html=True)


# Account card
role_class = "role-pill" if is_admin else "role-pill user"

account_html = f"""
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
""".strip()

st.markdown(account_html, unsafe_allow_html=True)


# Analysis History card
_render_history(history)

st.markdown("</div>", unsafe_allow_html=True)
render_footer()