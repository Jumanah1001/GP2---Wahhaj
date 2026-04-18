"""
pages/2_Home.py
===============
Dashboard home page — shown after login.

Changes in this version
-----------------------
1. Analysis History section replaces the single "Analysis Progress" card.
   - Shows ALL saved analysis runs (saved by save_analysis_to_history()).
   - Each entry shows: location, date, top score, recommendation, candidates.
   - User can expand any entry to see ranked candidates table.

2. Working filter: filter by recommendation level (All / Highly Recommended /
   Recommended / Review Required) and by location name search.

3. All dead navigation links corrected:
   - pages/10_Add_New_User.py  →  pages/9_Add_New_User.py
   - pages/8_Ranked_Results.py →  pages/7_Ranked_Results.py
   - pages/6_Run_Analysis.py   →  pages/5_Analysis.py
   - pages/4_Environmental_Data.py → pages/4_Upload_Image.py

4. Text contrast improved throughout (dark text on light backgrounds).
"""
import streamlit as st
from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    show_logo,
    logout_user,
    get_analysis_history,
)

st.set_page_config(page_title="Home", layout="wide")
init_state()
apply_global_style()
render_bg()

if not st.session_state.get("logged_in", False):
    st.switch_page("pages/1_Login.py")

username   = st.session_state.get("username", "—")
user_email = st.session_state.get("user_email", "—")
user_role  = st.session_state.get("user_role", "Analyst")
is_admin   = user_role == "Admin"

has_run      = st.session_state.get("analysis_run") is not None
has_location = st.session_state.get("location_saved", False)
has_image    = bool(st.session_state.get("uploaded_image_name", ""))

history = get_analysis_history()  # newest first

# ── styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.home-page { position:relative; z-index:2; padding-top:8px; }
.page-title {
    font-family:'Capriola',sans-serif; font-size:clamp(34px,3vw,44px);
    color:#1a1a1a; text-align:center; margin-bottom:8px; line-height:1.1;
}
.page-subtitle {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#444; text-align:center; margin-bottom:18px;
}
.card-box {
    background:rgba(255,255,255,0.88); border-radius:18px;
    box-shadow:0 4px 16px rgba(0,0,0,0.06);
    padding:20px 22px; min-height:130px;
    border:1px solid rgba(220,220,220,0.6);
}
.card-title {
    font-family:'Capriola',sans-serif; font-size:18px;
    color:#1a1a1a; margin-bottom:12px; font-weight:700;
}
.card-text {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#333; line-height:1.9;
}
.badge-role {
    display:inline-block; padding:2px 10px; border-radius:12px;
    font-size:12px; font-weight:700; font-family:'Capriola',sans-serif;
    background:#dcfce7; color:#166534;
}
.badge-admin { background:#ffedd5; color:#9a3412; }
.section-title {
    font-family:'Capriola',sans-serif; font-size:22px; font-weight:700;
    color:#1a1a1a; margin-bottom:4px; margin-top:20px;
}
.section-sub {
    font-family:'Capriola',sans-serif; font-size:13px; color:#555;
    margin-bottom:16px;
}

/* history entry card */
.hist-card {
    background:rgba(255,255,255,0.92); border-radius:14px;
    padding:16px 20px; margin-bottom:12px;
    box-shadow:0 2px 10px rgba(0,0,0,0.06);
    border:1px solid #e4e4e4;
}
.hist-location {
    font-family:'Capriola',sans-serif; font-size:17px; font-weight:700;
    color:#1a1a1a; margin-bottom:4px;
}
.hist-meta {
    font-family:'Capriola',sans-serif; font-size:12px; color:#666;
    margin-bottom:10px;
}
.hist-score {
    font-family:'Capriola',sans-serif; font-size:26px; font-weight:800;
    color:#0070FF; display:inline-block; margin-right:12px;
}
.hist-badge {
    display:inline-block; padding:4px 12px; border-radius:20px;
    font-size:12px; font-weight:700;
    vertical-align:middle;
}
.hb-high   { background:#dcfce7; color:#166534; }
.hb-rec    { background:#fef9c3; color:#713f12; }
.hb-review { background:#ffe4e6; color:#9f1239; }

/* ranked mini table */
.mini-tbl { width:100%; border-collapse:collapse; font-size:12px; margin-top:8px; }
.mini-tbl th {
    background:#f4f4f4; color:#444; font-weight:700;
    padding:6px 10px; text-align:left; border-bottom:1px solid #e0e0e0;
}
.mini-tbl td {
    padding:6px 10px; color:#222; border-bottom:1px solid #f0f0f0;
}
.mini-tbl tr:last-child td { border-bottom:none; }

/* empty state */
.empty-history {
    background:rgba(255,255,255,0.75); border-radius:14px;
    padding:32px; text-align:center;
    font-family:'Capriola',sans-serif; font-size:14px; color:#555;
    border:1px dashed #ccc; margin-top:8px;
}

/* filter bar */
.filter-bar {
    background:rgba(255,255,255,0.88); border-radius:10px;
    padding:12px 16px; margin-bottom:14px;
    border:1px solid #e4e4e4;
    display:flex; gap:12px; align-items:center; flex-wrap:wrap;
}

.footer-note {
    font-family:'Capriola',sans-serif; font-size:13px; color:#555;
    text-align:center; margin-top:28px; line-height:1.6;
}
div.stButton > button {
    background:#0070FF; color:white; border:none; border-radius:6px;
    min-height:44px; font-family:'Capriola',sans-serif; font-size:15px;
    box-shadow:3px 4px 4px rgba(0,0,0,0.14);
}
div.stButton > button:hover { background:#005fe0; color:white; }
div[data-testid="stTextInput"] input {
    background:#F0EEEE !important; color:#1a1a1a !important;
    border:1px solid #ccc !important; border-radius:6px !important;
    font-size:14px !important;
}
div[data-testid="stTextInput"] input::placeholder { color:#999 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="home-page">', unsafe_allow_html=True)

# ── top bar: logout + admin ───────────────────────────────────────────────────
top_l, top_mid, top_r = st.columns([5, 3, 2])
with top_r:
    if is_admin:
        btn_a, btn_b = st.columns([1, 1])
        with btn_a:
            if st.button("👥 Admin", use_container_width=True):
                st.switch_page("pages/9_Add_New_User.py")  # FIXED
        with btn_b:
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
    '<div class="page-subtitle">Your solar site selection platform — Saudi Vision 2030</div>',
    unsafe_allow_html=True,
)

# ── start analysis button ─────────────────────────────────────────────────────
_, start_col, _ = st.columns([2.8, 1.8, 2.8])
with start_col:
    if st.button("Start New Analysis", use_container_width=True):
        st.switch_page("pages/3_Choose_Location.py")

st.write("")

# ── top info strip: account + quick status ────────────────────────────────────
acc_col, stat_col = st.columns([1.2, 1.8], gap="large")

with acc_col:
    badge_cls = "badge-role badge-admin" if is_admin else "badge-role"
    st.markdown(
        f"""
        <div class="card-box">
            <div class="card-title">👤 Account</div>
            <div class="card-text">
                <b>{username}</b><br>
                {user_email}<br>
                Role: <span class="{badge_cls}">{user_role}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with stat_col:
    total = len(history)
    loc_name = st.session_state.get("selected_location", {}).get("location_name", "")
    last_loc = f"Last: {loc_name}" if loc_name else "No active location"

    pipeline_items = []
    if has_location:
        pipeline_items.append("✅ Location ready")
    if has_image:
        pipeline_items.append("✅ Image uploaded")
    if has_run:
        pipeline_items.append("✅ Analysis complete")

    progress_text = " &nbsp;·&nbsp; ".join(pipeline_items) if pipeline_items else "No active pipeline"

    st.markdown(
        f"""
        <div class="card-box">
            <div class="card-title">📊 Status</div>
            <div class="card-text">
                Saved analyses: <b>{total}</b><br>
                {progress_text}<br>
                <span style="font-size:12px;color:#888;">{last_loc}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    if has_run:
        if st.button("Continue to Results →", use_container_width=True):
            st.switch_page("pages/7_Ranked_Results.py")  # FIXED
    elif has_location or has_image:
        if st.button("Continue Pipeline →", use_container_width=True):
            if has_image:
                st.switch_page("pages/5_Analysis.py")    # FIXED
            else:
                st.switch_page("pages/4_Upload_Image.py")

st.write("")

# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS HISTORY — full saved results with working filter
# ═══════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-title">📋 Analysis History</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-sub">All previous site analyses — newest first</div>',
    unsafe_allow_html=True,
)

if not history:
    st.markdown(
        """
        <div class="empty-history">
            <div style="font-size:32px;margin-bottom:10px;">📭</div>
            <div style="font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:6px;">
                No analysis results yet
            </div>
            <div style="color:#666;">
                Run your first solar site analysis to see results here.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    # ── Working filter bar ────────────────────────────────────────────────
    f_col1, f_col2 = st.columns([2, 1.5])
    with f_col1:
        filter_search = st.text_input(
            "Search by location",
            placeholder="Filter by location name…",
            label_visibility="collapsed",
            key="hist_search",
        )
    with f_col2:
        filter_rec = st.selectbox(
            "Filter by recommendation",
            options=["All", "Highly Recommended", "Recommended", "Review Required"],
            index=0,
            label_visibility="collapsed",
            key="hist_rec_filter",
        )

    # ── Apply filter ──────────────────────────────────────────────────────
    filtered_history = history
    if filter_search.strip():
        q = filter_search.strip().lower()
        filtered_history = [
            e for e in filtered_history
            if q in e.get("location_name", "").lower()
        ]
    if filter_rec != "All":
        filtered_history = [
            e for e in filtered_history
            if e.get("recommendation", "") == filter_rec
        ]

    if not filtered_history:
        st.info("No results match your filter. Try changing the search or category.")
    else:
        st.markdown(
            f'<div style="font-family:Capriola,sans-serif;font-size:12px;color:#666;'
            f'margin-bottom:10px;">'
            f'Showing {len(filtered_history)} of {len(history)} result(s)</div>',
            unsafe_allow_html=True,
        )

        for entry in filtered_history:
            loc_name   = entry.get("location_name", "Unknown")
            analysed   = entry.get("analysed_at", "—")
            top_score  = entry.get("top_score", 0.0)
            score_pct  = f"{top_score * 100:.1f}%"
            rec        = entry.get("recommendation", "—")
            n_cands    = entry.get("candidate_count", 0)
            ranked     = entry.get("ranked", [])

            if rec == "Highly Recommended":
                badge_cls = "hb-high"
                rec_icon  = "🏆"
            elif rec == "Recommended":
                badge_cls = "hb-rec"
                rec_icon  = "✅"
            else:
                badge_cls = "hb-review"
                rec_icon  = "⚠️"

            with st.expander(f"📍 {loc_name}  —  {score_pct}  —  {analysed}", expanded=False):
                # Header row
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:16px;
                         margin-bottom:14px;flex-wrap:wrap;">
                        <span class="hist-score">{score_pct}</span>
                        <span class="hist-badge {badge_cls}">{rec_icon} {rec}</span>
                        <span style="font-family:Capriola,sans-serif;font-size:13px;
                                     color:#555;">{n_cands} candidate(s) found</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Ranked candidates mini-table
                if ranked:
                    rows_html = "".join(
                        f"""
                        <tr>
                          <td><b>{r['rank']}</b></td>
                          <td>{r['lat'] if r['lat'] else '—'}°N</td>
                          <td>{r['lon'] if r['lon'] else '—'}°E</td>
                          <td><b>{r['s10']}/10</b></td>
                          <td>{r['rec']}</td>
                        </tr>
                        """
                        for r in ranked
                    )
                    st.markdown(
                        f"""
                        <table class="mini-tbl">
                          <thead>
                            <tr>
                              <th>Rank</th>
                              <th>Latitude</th>
                              <th>Longitude</th>
                              <th>Score</th>
                              <th>Recommendation</th>
                            </tr>
                          </thead>
                          <tbody>{rows_html}</tbody>
                        </table>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("No detailed candidate data available for this run.")

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