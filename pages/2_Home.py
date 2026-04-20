"""
pages/2_Home.py
===============
Dashboard home page — shown after login.
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

analysis_ref = st.session_state.get("analysis_ref") or {}
image_records = st.session_state.get("image_records") or []

has_run = (
    st.session_state.get("analysis_run") is not None
    or analysis_ref.get("status") == "completed"
)
has_location = st.session_state.get("location_saved", False)
has_image = bool(st.session_state.get("uploaded_image_name", "")) or bool(image_records)
history = get_analysis_history()


def _safe_location_name(raw: str, max_len: int = 70) -> str:
    if not raw:
        return "Unknown Location"
    safe = re.sub(r"[^\w\s؀-ۿ\-,.()/°]", " ", raw)
    safe = re.sub(r"\s+", " ", safe).strip()
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip(" ,-") + "…"
    return safe or "Unknown Location"


def _history_badge(label: str) -> tuple[str, str]:
    label = str(label or "").strip()
    low = label.lower()
    if "high" in low:
        return "hb-high", "Highly Recommended"
    if "recommend" in low:
        return "hb-rec", "Recommended"
    if "suitable" in low:
        return "hb-suitable", "Suitable"
    return "hb-review", (label or "Review Required")


def _render_history_section(history_items) -> None:
    history_icon = ui_icon("history", 18, "#1a1a1a")

    # ── الكارد الخارجية ── st.container(border=True) هي الطريقة المضمونة
    with st.container(border=True):

        st.markdown(
            f"""
            <div class='section-title'>{history_icon} &nbsp;Analysis History</div>
            <div class='section-sub'>All previous site analyses</div>
            """,
            unsafe_allow_html=True,
        )

        if not history_items:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style='text-align:center; padding:20px 0;'>
                        <div style='margin-bottom:10px;'>{ui_icon('history', 26, '#8a8a8a')}</div>
                        <div style='font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:8px;font-family:Capriola,sans-serif;'>
                            No analysis results yet
                        </div>
                        <div style='color:#5b5b5b;font-family:Capriola,sans-serif;font-size:14px;'>
                            Run your first solar site analysis to see results here.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            return

        for idx, entry in enumerate(history_items):
            loc_label = escape(_safe_location_name(entry.get("location_name", "Unknown")))
            analysed = escape(str(entry.get("analysed_at", "—")))

            score_val = entry.get("selected_score", entry.get("top_score", 0.0))
            try:
                score_val = float(score_val or 0.0)
            except Exception:
                score_val = 0.0
            score_pct = escape(f"{score_val * 100:.1f}%")

            badge_cls, badge_label = _history_badge(
                entry.get("selected_label", entry.get("recommendation", ""))
            )

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                row_left, row_right = st.columns(
                    [4.4, 1.35], gap="large", vertical_alignment="center"
                )
                with row_left:
                    st.markdown(
                        f"""
                        <div class='hist-location'>{ui_icon('location', 16, '#0070FF')} &nbsp;{loc_label}</div>
                        <div class='hist-simple-meta'>{analysed}</div>
                        <div class='hist-simple-row'>
                            <span class='hist-score'>{score_pct}</span>
                            <span class='hist-badge {badge_cls}'>{escape(badge_label)}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with row_right:
                    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
                    if st.button(
                        "Open Final Report",
                        key=f"hist_open_{idx}_{entry.get('run_id', idx)}",
                        use_container_width=True,
                    ):
                        ok = restore_analysis_history_entry(entry)
                        if ok:
                            st.switch_page("pages/8_Final_Report.py")
                        else:
                            st.warning(
                                "This saved entry cannot be reopened in the current session yet."
                            )


st.markdown(
    """
<style>
.home-page {
    position: relative;
    z-index: 2;
    padding-top: 8px;
}

.page-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(34px, 3vw, 44px);
    color: #1a1a1a;
    text-align: center;
    margin-bottom: 8px;
    line-height: 1.1;
}

.page-subtitle {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #5E5B5B;
    text-align: center;
    margin-bottom: 18px;
}

.card-box {
    background: rgba(255,255,255,0.92);
    border-radius: 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 20px 22px;
    min-height: 130px;
    border: 1px solid rgba(220,220,220,0.6);
}

.card-title {
    font-family: 'Capriola', sans-serif;
    font-size: 18px;
    color: #1a1a1a;
    margin-bottom: 12px;
    font-weight: 700;
}

.card-text {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #222;
    line-height: 1.9;
}

.badge-role {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Capriola', sans-serif;
    background: #dcfce7;
    color: #166534;
}

.badge-admin {
    background: #ffedd5;
    color: #9a3412;
}

.section-title {
    font-family: 'Capriola', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 3px;
}

.section-sub {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    color: #5E5B5B;
    margin-bottom: 2px;
}

.hist-location {
    font-family: 'Capriola', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: #1F3864;
    margin-bottom: 4px;
}

.hist-simple-meta {
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
    color: #777;
    margin-bottom: 12px;
}

.hist-simple-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.hist-score {
    font-family: 'Capriola', sans-serif;
    font-size: 28px;
    font-weight: 800;
    color: #0070FF;
    line-height: 1;
}

.hist-badge {
    display: inline-block;
    padding: 5px 13px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    font-family: 'Capriola', sans-serif;
}

.hb-high      { background: #DCFCE7; color: #166534; }
.hb-rec       { background: #DBEAFE; color: #1D4ED8; }
.hb-suitable  { background: #FEE2E2; color: #B42318; }
.hb-review    { background: #FEE2E2; color: #991B1B; }

div.stButton > button {
    background: #0070FF;
    color: white;
    border: none;
    border-radius: 10px;
    min-height: 46px;
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    box-shadow: 4px 5px 4px rgba(0,0,0,.14);
}

div.stButton > button:hover {
    background: #005fe0;
    color: white;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="home-page">', unsafe_allow_html=True)

top_l, top_mid, top_r = st.columns([5, 3, 2])

with top_r:
    if is_admin:
        btn_a, btn_b = st.columns([1, 1])
        with btn_a:
            if st.button(":material/group: Admin", use_container_width=True):
                st.switch_page("pages/9_Add_New_User.py")
        with btn_b:
            if st.button(":material/logout: Logout", use_container_width=True):
                logout_user()
                st.switch_page("pages/1_Login.py")
    else:
        if st.button(":material/logout: Logout", use_container_width=True):
            logout_user()
            st.switch_page("pages/1_Login.py")

_, logo_col, _ = st.columns([2.5, 1.0, 2.5])
with logo_col:
    show_logo(width=175)

st.markdown('<div class="page-title">Welcome to WAHHAJ</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Start your journey toward smarter solar site selection</div>',
    unsafe_allow_html=True,
)

_, start_col, _ = st.columns([2.8, 1.8, 2.8])
with start_col:
    if st.button("Start Analysis", use_container_width=True):
        reset_for_new_analysis()
        st.switch_page("pages/3_Choose_Location.py")

st.write("")

acc_col, stat_col = st.columns([1.2, 1.8], gap="large")

with acc_col:
    badge_cls = "badge-role badge-admin" if is_admin else "badge-role"
    st.markdown(
        (
            f"<div class='card-box'>"
            f"<div class='card-title'>{ui_icon('account', 18, '#1a1a1a')} &nbsp;Account</div>"
            f"<div class='card-text'>"
            f"<b>{escape(username)}</b><br>"
            f"{escape(user_email)}<br>"
            f"Role: <span class='{badge_cls}'>{escape(user_role)}</span>"
            f"</div>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )

with stat_col:
    total = len(history)
    loc_raw = st.session_state.get("selected_location", {}).get("location_name", "")
    loc_safe = _safe_location_name(loc_raw) if loc_raw else ""
    last_loc = f"Last location: {escape(loc_safe)}" if loc_safe else "No active location"

    pipeline_items = []
    if has_location:
        pipeline_items.append("✅ Location ready")
    if has_image:
        pipeline_items.append("✅ Image uploaded")
    if has_run:
        pipeline_items.append("✅ Analysis complete")

    progress_text = " &nbsp;·&nbsp; ".join(pipeline_items) if pipeline_items else "No active pipeline"

    st.markdown(
        (
            f"<div class='card-box'>"
            f"<div class='card-title'>{ui_icon('status', 18, '#1a1a1a')} &nbsp;Status</div>"
            f"<div class='card-text'>"
            f"Saved analyses: <b>{total}</b><br>"
            f"{progress_text}<br>"
            f"<span style='font-size:12px;color:#888;'>{last_loc}</span>"
            f"</div>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )

    st.write("")
    if has_run:
        if st.button("Continue to Results →", use_container_width=True):
            st.switch_page("pages/7_Ranked_Results.py")
    elif has_location or has_image:
        if st.button("Continue Pipeline →", use_container_width=True):
            if has_image:
                st.switch_page("pages/5_Analysis.py")
            else:
                st.switch_page("pages/4_Upload_Image.py")

st.write("")

_render_history_section(history)

st.markdown("</div>", unsafe_allow_html=True)
render_footer()