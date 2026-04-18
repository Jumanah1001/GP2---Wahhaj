"""
pages/2_Home.py
===============
Dashboard home page — shown after login.

Implementation pattern
----------------------
The Analysis History section is now built using the same pattern as
5_Analysis.py (the reference page in this project):

  - CSS defined once in a single st.markdown("<style>") block
  - Card styles match result-panel / summary-card from 5_Analysis.py:
      background:rgba(255,255,255,0.92), border-radius:22px,
      box-shadow:0 2px 12px rgba(0,0,0,0.06), border:1px solid rgba(220,220,220,0.6)
  - Each history entry is assembled as a complete HTML string and passed
    to a single st.markdown() call — no open/close div split across calls
  - html.escape() on every dynamic value
  - Interactive widgets (filter text_input, selectbox) live outside HTML blocks

The outer history card:
  - The section-level white card is applied to the Streamlit container via
    CSS :has(.history-card-marker) — the only reliable Streamlit-compatible
    way to add a background card around interactive widget groups
  - All history entry cards INSIDE the section are pure HTML panels
    matching the result-panel pattern from 5_Analysis.py

Location name safety:
  - _safe_location_name() strips Markdown-special characters before any
    location name appears in the UI. This prevents Streamlit's Markdown
    parser from producing _arrow_right_text or other rendering artifacts.
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
    ui_icon,
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
history      = get_analysis_history()


# ── Safe location name helper ─────────────────────────────────────────────────
def _safe_location_name(raw: str, max_len: int = 55) -> str:
    """
    Strip Markdown-special characters that cause Streamlit to produce
    rendering artifacts (_arrow_right_text, garbled Arabic, etc.).
    Keeps letters (Latin + Arabic Unicode block), digits, spaces, and
    basic punctuation safe in both HTML and Markdown contexts.
    """
    if not raw:
        return "Unknown Location"
    safe = re.sub(r"[^\w\s\u0600-\u06FF\-,.()/\u00B0]", " ", raw)
    safe = re.sub(r"\s+", " ", safe).strip()
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip(" ,-") + "…"
    return safe or "Unknown Location"


# ── Styles ────────────────────────────────────────────────────────────────────
# Card values match 5_Analysis.py exactly:
#   result-panel:  border-radius:24px, box-shadow:0 2px 12px rgba(0,0,0,0.06),
#                  border:1px solid rgba(220,220,220,0.6)
#   summary-card:  border-radius:22px, same shadow/border
st.markdown("""
<style>

/* ── page wrapper ── */
.home-page { position:relative; z-index:2; padding-top:8px; }

.page-title {
    font-family:'Capriola',sans-serif; font-size:clamp(34px,3vw,44px);
    color:#1a1a1a; text-align:center; margin-bottom:8px; line-height:1.1;
}
.page-subtitle {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#5E5B5B; text-align:center; margin-bottom:18px;
}

/* ── Account / Status cards — same as summary-card in 5_Analysis.py ── */
.card-box {
    background:rgba(255,255,255,0.92);
    border-radius:22px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    padding:20px 22px;
    min-height:130px;
    border:1px solid rgba(220,220,220,0.6);
}
.card-title {
    font-family:'Capriola',sans-serif; font-size:18px;
    color:#1a1a1a; margin-bottom:12px; font-weight:700;
}
.card-text {
    font-family:'Capriola',sans-serif; font-size:14px;
    color:#222; line-height:1.9;
}
.badge-role {
    display:inline-block; padding:2px 10px; border-radius:12px;
    font-size:12px; font-weight:700; font-family:'Capriola',sans-serif;
    background:#dcfce7; color:#166534;
}
.badge-admin { background:#ffedd5; color:#9a3412; }

/* ── History section heading ── */
.section-title {
    font-family:'Capriola',sans-serif; font-size:20px; font-weight:700;
    color:#1a1a1a; margin-bottom:2px;
}
.section-sub {
    font-family:'Capriola',sans-serif; font-size:13px;
    color:#5E5B5B; margin-bottom:10px;
}

/* ─────────────────────────────────────────────────────────────────────
   HISTORY SECTION OUTER CARD

   Applied to the stVerticalBlock of st.container() via CSS :has().
   Marker div .history-card-marker is injected first inside the container.
   This is the only Streamlit-safe way to add a background to a group
   containing interactive widgets (text_input, selectbox).

   Values match the project's card style: same as .card-box above.
   ──────────────────────────────────────────────────────────────────── */
.history-card-marker {
    display:block; height:0; width:0;
    overflow:hidden; visibility:hidden; position:absolute;
}
[data-testid="stVerticalBlock"]:has(.history-card-marker) {
    background: rgba(255,255,255,0.92);
    border-radius: 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border: 1px solid rgba(220,220,220,0.6);
    padding: 20px 22px;
}

/* ─────────────────────────────────────────────────────────────────────
   HISTORY ENTRY CARDS

   Matches result-panel pattern from 5_Analysis.py:
     border-radius:24px, same shadow/border, padding:20px 24px
   Each entry rendered as a complete self-contained HTML block
   in a single st.markdown() call.
   ──────────────────────────────────────────────────────────────────── */
.hist-entry {
    background:rgba(255,255,255,0.92);
    border-radius:24px;
    padding:20px 24px;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    border:1px solid rgba(220,220,220,0.6);
    margin-bottom:12px;
}
.hist-entry-header {
    display:flex; align-items:center; gap:14px;
    flex-wrap:wrap; margin-bottom:14px;
}
.hist-location {
    font-family:'Capriola',sans-serif; font-size:16px; font-weight:700;
    color:#1F3864; margin-bottom:3px;
}
.hist-meta {
    font-family:'Capriola',sans-serif; font-size:12px; color:#666;
    margin-bottom:10px;
}
.hist-score {
    font-family:'Capriola',sans-serif; font-size:28px; font-weight:800;
    color:#0070FF; line-height:1;
}
.hist-badge {
    display:inline-block; padding:5px 13px; border-radius:999px;
    font-size:12px; font-weight:700;
}
.hb-high   { background:#DCFCE7; color:#166534; }
.hb-rec    { background:#FEF9C3; color:#713f12; }
.hb-review { background:#FEE2E2; color:#991B1B; }
.hist-cands {
    font-family:'Capriola',sans-serif; font-size:13px; color:#555;
}
.hist-divider {
    border:none; border-top:1px solid #EFEFEF; margin:12px 0;
}

/* ── Candidate mini-table inside history entries ── */
.mini-tbl {
    width:100%; border-collapse:collapse; font-size:12px; margin-top:4px;
}
.mini-tbl th {
    background:#f4f4f4; color:#444; font-weight:700;
    padding:7px 10px; text-align:left; border-bottom:1px solid #e0e0e0;
    font-family:'Capriola',sans-serif; font-size:11px;
    text-transform:uppercase; letter-spacing:.04em;
}
.mini-tbl td {
    padding:7px 10px; color:#222; border-bottom:1px solid #f0f0f0;
    font-family:'Capriola',sans-serif; font-size:12px;
}
.mini-tbl tr:last-child td { border-bottom:none; }

/* ── Empty state ── */
.empty-history {
    padding:28px 16px; text-align:center;
    font-family:'Capriola',sans-serif; font-size:14px; color:#666;
    border:1px dashed rgba(220,220,220,0.8); border-radius:16px;
}

/* ── Filter result count ── */
.history-count {
    font-family:'Capriola',sans-serif; font-size:12px;
    color:#666; margin-bottom:12px;
}

/* ── Buttons ── */
div.stButton > button {
    background:#0070FF; color:white; border:none; border-radius:10px;
    min-height:46px; font-family:'Capriola',sans-serif; font-size:15px;
    box-shadow:4px 5px 4px rgba(0,0,0,.14);
}
div.stButton > button:hover { background:#005fe0; color:white; }

/* ── Filter inputs ── */
div[data-testid="stTextInput"] input {
    background:#F0EEEE !important; color:#1a1a1a !important;
    border:1px solid rgba(220,220,220,0.8) !important;
    border-radius:6px !important; font-size:14px !important;
}
div[data-testid="stTextInput"] input::placeholder { color:#999 !important; }

/* ── Footer ── */
.footer-note {
    font-family:'Capriola',sans-serif; font-size:13px; color:#5E5B5B;
    text-align:center; margin-top:28px; line-height:1.6;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="home-page">', unsafe_allow_html=True)

# ── Top bar ───────────────────────────────────────────────────────────────────
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

# ── Logo ──────────────────────────────────────────────────────────────────────
_, logo_col, _ = st.columns([2.5, 1.0, 2.5])
with logo_col:
    show_logo(width=175)

# ── Title ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">Welcome to Wahhaj</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Your solar site selection platform — Saudi Vision 2030</div>',
    unsafe_allow_html=True,
)

# ── Start analysis button ─────────────────────────────────────────────────────
_, start_col, _ = st.columns([2.8, 1.8, 2.8])
with start_col:
    if st.button("Start New Analysis", use_container_width=True):
        st.switch_page("pages/3_Choose_Location.py")

st.write("")

# ── Account + Status cards ────────────────────────────────────────────────────
# These are static HTML — use the single st.markdown() pattern (same as 5_Analysis.py)
acc_col, stat_col = st.columns([1.2, 1.8], gap="large")

with acc_col:
    badge_cls = "badge-role badge-admin" if is_admin else "badge-role"
    st.markdown(
        f"<div class='card-box'>"
        f"<div class='card-title'>{ui_icon('account', 18, '#1a1a1a')} &nbsp;Account</div>"
        f"<div class='card-text'>"
        f"<b>{escape(username)}</b><br>"
        f"{escape(user_email)}<br>"
        f"Role: <span class='{badge_cls}'>{escape(user_role)}</span>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

with stat_col:
    total    = len(history)
    loc_raw  = st.session_state.get("selected_location", {}).get("location_name", "")
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
        f"<div class='card-box'>"
        f"<div class='card-title'>{ui_icon('status', 18, '#1a1a1a')} &nbsp;Status</div>"
        f"<div class='card-text'>"
        f"Saved analyses: <b>{total}</b><br>"
        f"{progress_text}<br>"
        f"<span style='font-size:12px;color:#888;'>{last_loc}</span>"
        f"</div>"
        f"</div>",
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

# ═══════════════════════════════════════════════════════════════════════════
# ANALYSIS HISTORY
# ═══════════════════════════════════════════════════════════════════════════

# Section heading lives ABOVE the card (same pattern as page-title/page-subtitle
# sitting outside panels in 5_Analysis.py)
st.markdown(
    f'<div class="section-title">{ui_icon("history", 18, "#1a1a1a")} &nbsp;Analysis History</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="section-sub">All previous site analyses — newest first</div>',
    unsafe_allow_html=True,
)

# ── Outer card via st.container() + :has() ────────────────────────────────────
# st.container() creates a [data-testid="stVerticalBlock"] that genuinely wraps
# its children. The .history-card-marker triggers the card CSS on that element.
# This is the same structural approach used by the project — no open/close div split.
with st.container():
    # Marker: injected first, triggers :has() card style on this container
    st.markdown('<div class="history-card-marker"></div>', unsafe_allow_html=True)

    if not history:
        # ── Empty state: pure HTML block — same pattern as state-panel in 5_Analysis.py
        st.markdown(
            "<div class='empty-history'>"
            f"<div style='margin-bottom:10px;'>{ui_icon('history', 28, '#888')}</div>"
            "<div style='font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:6px;'>"
            "No analysis results yet</div>"
            "<div style='color:#555;font-family:Capriola,sans-serif;'>"
            "Run your first solar site analysis to see results here.</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    else:
        # ── Filter bar (interactive widgets — outside HTML blocks) ───────────
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
        filtered = history
        if filter_search.strip():
            q = filter_search.strip().lower()
            filtered = [
                e for e in filtered
                if q in e.get("location_name", "").lower()
            ]
        if filter_rec != "All":
            filtered = [
                e for e in filtered
                if e.get("recommendation", "") == filter_rec
            ]

        if not filtered:
            st.markdown(
                "<div style='padding:14px 0;font-family:Capriola,sans-serif;"
                "font-size:14px;color:#666;'>No results match your filter.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='history-count'>"
                f"Showing {len(filtered)} of {len(history)} result(s)</div>",
                unsafe_allow_html=True,
            )

            for entry in filtered:
                # ── Clean every dynamic value with escape() and _safe_location_name()
                raw_loc   = entry.get("location_name", "Unknown")
                loc_label = escape(_safe_location_name(raw_loc))
                analysed  = escape(entry.get("analysed_at", "—"))
                top_score = entry.get("top_score", 0.0)
                score_pct = escape(f"{top_score * 100:.1f}%")
                rec       = entry.get("recommendation", "—")
                n_cands   = entry.get("candidate_count", 0)
                ranked    = entry.get("ranked", [])

                if rec == "Highly Recommended":
                    badge_cls = "hb-high"
                    badge_label = "Highly Recommended"
                elif rec == "Recommended":
                    badge_cls = "hb-rec"
                    badge_label = "Recommended"
                else:
                    badge_cls = "hb-review"
                    badge_label = "Review Required"

                # ── Candidate table rows HTML ──────────────────────────────────
                if ranked:
                    rows_html = "".join(
                        f"<tr>"
                        f"<td><b>{r['rank']}</b></td>"
                        f"<td>{escape(str(r['lat']))+'°N' if r['lat'] else '—'}</td>"
                        f"<td>{escape(str(r['lon']))+'°E' if r['lon'] else '—'}</td>"
                        f"<td><b>{escape(str(r['s10']))}/10</b></td>"
                        f"<td>{escape(r['rec'])}</td>"
                        f"</tr>"
                        for r in ranked
                    )
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
                        "<div style='font-family:Capriola,sans-serif;"
                        "font-size:13px;color:#888;padding:8px 0;'>"
                        "No candidate data available.</div>"
                    )

                # ── History entry card: ONE st.markdown() call, all content inside
                # Matches the result-panel / factors-panel pattern from 5_Analysis.py:
                # complete HTML string, html.escape() on all dynamic values.
                entry_html = (
                    "<div class='hist-entry'>"

                    # Location + date
                    f"<div class='hist-location'>{ui_icon('location', 16, '#0070FF')} &nbsp;{loc_label}</div>"
                    f"<div class='hist-meta'>{analysed}</div>"

                    # Score + badge + candidate count
                    "<div class='hist-entry-header'>"
                    f"<span class='hist-score'>{score_pct}</span>"
                    f"<span class='hist-badge {badge_cls}'>{badge_label}</span>"
                    f"<span class='hist-cands'>{n_cands} candidate(s)</span>"
                    "</div>"

                    # Divider
                    "<hr class='hist-divider'>"

                    # Ranked candidates table
                    + table_html +

                    "</div>"
                )
                st.markdown(entry_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)  # home-page
render_footer()