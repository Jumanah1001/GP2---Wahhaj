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


def _safe_location_name(raw: str, max_len: int = 55) -> str:
    if not raw:
        return "Unknown Location"
    safe = re.sub(r"[^\w\s\u0600-\u06FF\-,.()/\u00B0]", " ", raw)
    safe = re.sub(r"\s+", " ", safe).strip()
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip(" ,-") + "…"
    return safe or "Unknown Location"


def _fmt_coord(value, suffix: str) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):.5f}°{suffix}"
    except Exception:
        return escape(str(value))


def _build_history_section(history_items) -> str:
    history_icon = ui_icon("history", 18, "#1a1a1a")

    if not history_items:
        return (
            "<div class='history-card'>"
            f"<div class='section-title'>{history_icon} &nbsp;Analysis History</div>"
            "<div class='section-sub'>All previous site analyses </div>"
            "<div class='empty-history'>"
            f"<div style='margin-bottom:10px;'>{ui_icon('history', 28, '#888')}</div>"
            "<div style='font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:6px;'>"
            "No analysis results yet</div>"
            "<div style='color:#555;font-family:Capriola,sans-serif;'>"
            "Run your first solar site analysis to see results here.</div>"
            "</div>"
            "</div>"
        )

    entry_blocks = []

    for entry in history_items:
        raw_loc = entry.get("location_name", "Unknown")
        loc_label = escape(_safe_location_name(raw_loc))
        analysed = escape(str(entry.get("analysed_at", "—")))
        top_score = float(entry.get("top_score", 0.0) or 0.0)
        score_pct = escape(f"{top_score * 100:.1f}%")
        rec = str(entry.get("recommendation", "—"))
        n_cands = int(entry.get("candidate_count", 0) or 0)
        ranked = entry.get("ranked", []) or []

        if rec == "Highly Recommended":
            badge_cls = "hb-high"
            badge_label = "Highly Recommended"
        elif rec == "Recommended":
            badge_cls = "hb-rec"
            badge_label = "Recommended"
        else:
            badge_cls = "hb-review"
            badge_label = "Review Required"

        if ranked:
            rows_html_parts = []
            for r in ranked:
                rank = escape(str(r.get("rank", "—")))
                lat = _fmt_coord(r.get("lat"), "N")
                lon = _fmt_coord(r.get("lon"), "E")
                s10 = escape(str(r.get("s10", "—")))
                rec_txt = escape(str(r.get("rec", "—")))

                rows_html_parts.append(
                    "<tr>"
                    f"<td><b>{rank}</b></td>"
                    f"<td>{lat}</td>"
                    f"<td>{lon}</td>"
                    f"<td><b>{s10}/10</b></td>"
                    f"<td>{rec_txt}</td>"
                    "</tr>"
                )

            rows_html = "".join(rows_html_parts)
            table_html = (
                "<table class='mini-tbl'>"
                "<thead><tr>"
                "<th>Rank</th><th>Latitude</th><th>Longitude</th>"
                "<th>Score</th><th>Recommendation</th>"
                "</tr></thead>"
                f"<tbody>{rows_html}</tbody>"
                "</table>"
            )
        else:
            table_html = (
                "<div style='font-family:Capriola,sans-serif;font-size:13px;color:#888;padding:8px 0;'>"
                "No candidate data available."
                "</div>"
            )

        entry_html = (
            "<div class='hist-entry'>"
            f"<div class='hist-location'>{ui_icon('location', 16, '#0070FF')} &nbsp;{loc_label}</div>"
            f"<div class='hist-meta'>{analysed}</div>"
            "<div class='hist-entry-header'>"
            f"<span class='hist-score'>{score_pct}</span>"
            f"<span class='hist-badge {badge_cls}'>{badge_label}</span>"
            f"<span class='hist-cands'>{n_cands} candidate(s)</span>"
            "</div>"
            "<hr class='hist-divider'>"
            f"{table_html}"
            "</div>"
        )
        entry_blocks.append(entry_html)

    joined_entries = "".join(entry_blocks)

    return (
        "<div class='history-card'>"
        f"<div class='section-title'>{history_icon} &nbsp;Analysis History</div>"
        "<div class='section-sub'>All previous site analyses</div>"
        f"{joined_entries}"
        "</div>"
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

.history-card {
    background: rgba(255,255,255,0.92);
    border-radius: 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 20px 22px;
    border: 1px solid rgba(220,220,220,0.6);
    margin-top: 6px;
}

.section-title {
    font-family: 'Capriola', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 2px;
}

.section-sub {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    color: #5E5B5B;
    margin-bottom: 12px;
}

.hist-entry {
    background: #FAFAFA;
    border-radius: 18px;
    padding: 18px 20px;
    border: 1px solid rgba(225,225,225,0.9);
    margin-bottom: 12px;
}

.hist-entry:last-child {
    margin-bottom: 0;
}

.hist-entry-header {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    margin-bottom: 14px;
}

.hist-location {
    font-family: 'Capriola', sans-serif;
    font-size: 16px;
    font-weight: 700;
    color: #1F3864;
    margin-bottom: 3px;
}

.hist-meta {
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
    color: #666;
    margin-bottom: 10px;
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
}

.hb-high   { background: #DCFCE7; color: #166534; }
.hb-rec    { background: #FEF9C3; color: #713f12; }
.hb-review { background: #FEE2E2; color: #991B1B; }

.hist-cands {
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    color: #555;
}

.hist-divider {
    border: none;
    border-top: 1px solid #EFEFEF;
    margin: 12px 0;
}

.mini-tbl {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin-top: 4px;
}

.mini-tbl th {
    background: #f4f4f4;
    color: #444;
    font-weight: 700;
    padding: 7px 10px;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
    font-family: 'Capriola', sans-serif;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .04em;
}

.mini-tbl td {
    padding: 7px 10px;
    color: #222;
    border-bottom: 1px solid #f0f0f0;
    font-family: 'Capriola', sans-serif;
    font-size: 12px;
}

.mini-tbl tr:last-child td {
    border-bottom: none;
}

.empty-history {
    padding: 30px 18px;
    text-align: center;
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    color: #666;
    border: 1px dashed rgba(220,220,220,0.85);
    border-radius: 16px;
    background: rgba(255,255,255,0.55);
}

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

st.markdown(_build_history_section(history), unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
render_footer()