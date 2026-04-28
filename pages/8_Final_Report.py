"""
pages/8_Final_Report.py
========================
One-screen landscape final report for the selected analysed site.

Goals
-----
- keep the page visible in a single wide screen as much as possible
- make the selected-site map the visual focus
- keep PDF/TXT export working
- use the existing session data without changing the report pipeline
"""

from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4
from html import escape

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from ui_helpers import (
    init_state,
    apply_global_style,
    render_bg,
    require_login,
    render_top_home_button,
    reset_for_new_analysis,
    save_analysis_to_history,
    get_ranked_history,
    get_global_rank_for_run,
    save_final_report_to_db,
    load_final_report_from_db,
)

st.set_page_config(page_title="Final Report", layout="wide")
init_state()
apply_global_style()
render_bg()
require_login()
render_top_home_button("pages/2_Home.py")


# ── navigation guard ────────────────────────────────────────────────────────
# Streamlit reruns the whole page when a button is clicked.
# These callbacks let navigation buttons leave the page before the loading card
# or report/PDF preparation starts on the rerun.
def _queue_final_report_navigation(target_page: str, reset_analysis: bool = False) -> None:
    st.session_state["_final_report_nav_target"] = target_page
    st.session_state["_final_report_nav_reset"] = reset_analysis


def _consume_final_report_navigation() -> None:
    target_page = st.session_state.pop("_final_report_nav_target", None)
    reset_analysis = st.session_state.pop("_final_report_nav_reset", False)

    if target_page:
        if reset_analysis:
            reset_for_new_analysis()
        st.switch_page(target_page)


_consume_final_report_navigation()


# ── page-level CSS ──────────────────────────────────────────────────────────
st.markdown(
    """
<style>
:root {
    --wah-primary: #1F3864;
    --wah-border: #D9E3F1;
    --wah-surface: rgba(255,255,255,0.96);
    --wah-muted: #64748B;
    --wah-text: #162033;
    --wah-soft: #F6F9FD;
}

.stApp [data-testid="stAppViewContainer"] {
    background: transparent;
}

.main .block-container {
    max-width: 1480px !important;
    padding-top: 0.45rem !important;
    padding-bottom: 0.35rem !important;
}

#MainMenu, footer {visibility: hidden;}

div[data-testid="stVerticalBlock"] > div:has(> .fr-header-shell) {
    margin-bottom: 0.2rem;
}

.fr-header-shell {
    position: relative;
    z-index: 2;
    margin: 0 0 0.4rem 0;
}

.fr-header {
    background: linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(246,249,253,0.98) 100%);
    border: 1px solid var(--wah-border);
    border-radius: 18px;
    padding: 0.9rem 1rem;
    box-shadow: 0 8px 24px rgba(16, 24, 40, 0.06);
}

.fr-title {
    font-family: 'Capriola', sans-serif;
    color: var(--wah-text);
    font-size: clamp(1.55rem, 2vw, 2.1rem);
    line-height: 1.05;
    margin: 0;
}

.fr-subtitle {
    font-family: 'Capriola', sans-serif;
    color: var(--wah-muted);
    font-size: 0.84rem;
    margin-top: 0.28rem;
}

.fr-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
    margin-top: 0.72rem;
}

.fr-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.36rem 0.62rem;
    border-radius: 999px;
    background: #EEF4FB;
    border: 1px solid #D6E3F3;
    color: #365277;
    font-family: 'Capriola', sans-serif;
    font-size: 0.77rem;
    white-space: nowrap;
}

.fr-card {
    position: relative;
    z-index: 2;
    background: var(--wah-surface);
    border: 1px solid var(--wah-border);
    border-radius: 18px;
    box-shadow: 0 8px 22px rgba(16, 24, 40, 0.05);
    padding: 0.9rem 1rem;
    height: 100%;
}

.fr-card-title {
    font-family: 'Capriola', sans-serif;
    font-size: 0.83rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--wah-muted);
    margin-bottom: 0.7rem;
}

.fr-card-title.compact {
    margin-bottom: 0.45rem;
}

.fr-big-score {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(2rem, 3vw, 2.8rem);
    line-height: 1;
    margin: 0;
}

.fr-score-label {
    margin-top: 0.28rem;
    font-family: 'Capriola', sans-serif;
    font-size: 0.92rem;
    font-weight: 700;
}

.fr-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.38rem 0.62rem;
    border-radius: 999px;
    font-family: 'Capriola', sans-serif;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 0.56rem;
}

.fr-progress {
    margin-top: 0.72rem;
    background: #E9EEF5;
    border-radius: 999px;
    height: 10px;
    overflow: hidden;
}

.fr-progress > span {
    display: block;
    height: 100%;
    border-radius: 999px;
}

.fr-mini-note {
    margin-top: 0.55rem;
    color: var(--wah-muted);
    font-family: 'Capriola', sans-serif;
    font-size: 0.78rem;
    line-height: 1.5;
}

.fr-kv-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.6rem 0.8rem;
}

.fr-kv-item {
    background: #F8FBFF;
    border: 1px solid #E5EEF8;
    border-radius: 12px;
    padding: 0.6rem 0.7rem;
    min-height: 56px;
}

.fr-kv-label {
    font-family: 'Capriola', sans-serif;
    font-size: 0.72rem;
    color: var(--wah-muted);
    margin-bottom: 0.22rem;
}

.fr-kv-value {
    font-family: 'Capriola', sans-serif;
    font-size: 0.85rem;
    color: var(--wah-text);
    font-weight: 700;
    line-height: 1.35;
}

.fr-list {
    display: grid;
    gap: 0.46rem;
}

.fr-list-item {
    display: flex;
    gap: 0.52rem;
    align-items: flex-start;
    background: #F8FBFF;
    border: 1px solid #E5EEF8;
    border-radius: 12px;
    padding: 0.55rem 0.68rem;
    font-family: 'Capriola', sans-serif;
    color: var(--wah-text);
    font-size: 0.8rem;
    line-height: 1.45;
}

.fr-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--wah-primary);
    margin-top: 0.32rem;
    flex-shrink: 0;
}

.fr-factor-rows {
    display: grid;
    gap: 0.48rem;
}

.fr-factor-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 70px;
    gap: 0.65rem;
    align-items: center;
}

.fr-factor-head {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 0.18rem;
    font-family: 'Capriola', sans-serif;
    font-size: 0.79rem;
    color: var(--wah-text);
}

.fr-factor-sub {
    color: var(--wah-muted);
    font-size: 0.7rem;
    font-family: 'Capriola', sans-serif;
    margin-bottom: 0.3rem;
}

.fr-factor-bar {
    width: 100%;
    height: 9px;
    border-radius: 999px;
    background: #E9EEF5;
    overflow: hidden;
}

.fr-factor-bar > span {
    display: block;
    height: 100%;
    border-radius: 999px;
}

.fr-factor-val {
    text-align: right;
    font-family: 'Capriola', sans-serif;
    font-size: 0.79rem;
    font-weight: 700;
    color: #365277;
}

.fr-map-title {
    position: relative;
    z-index: 2;
    background: transparent;
    border: none;
    border-bottom: 1px solid #E5EEF8;
    border-radius: 0;
    padding: 0.85rem 1rem 0.6rem 1rem;
    box-shadow: none;
}

.fr-map-caption {
    font-family: 'Capriola', sans-serif;
    color: var(--wah-muted);
    font-size: 0.74rem;
    margin-top: 0.18rem;
}

.fr-map-shell {
    position: relative;
    z-index: 2;
    border: 1px solid var(--wah-border);
    border-top: none;
    border-radius: 0 0 18px 18px;
    overflow: hidden;
    box-shadow: 0 8px 22px rgba(16, 24, 40, 0.05);
    background: rgba(255,255,255,0.96);
}

.fr-mini-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.6rem;
}

.fr-mini-factor {
    background: #F8FBFF;
    border: 1px solid #E5EEF8;
    border-radius: 14px;
    padding: 0.7rem 0.72rem;
    min-height: 108px;
}

.fr-mini-factor h4 {
    margin: 0 0 0.28rem 0;
    font-family: 'Capriola', sans-serif;
    font-size: 0.74rem;
    color: var(--wah-text);
    line-height: 1.35;
}

.fr-mini-raw {
    font-family: 'Capriola', sans-serif;
    font-size: 0.73rem;
    color: var(--wah-muted);
    line-height: 1.4;
    min-height: 32px;
}

.fr-mini-pill {
    display: inline-flex;
    margin-top: 0.45rem;
    padding: 0.26rem 0.48rem;
    border-radius: 999px;
    background: #EAF1FB;
    color: #365277;
    font-family: 'Capriola', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
}

.fr-summary-grid {
    display: grid;
    gap: 0.52rem;
}

.fr-summary-item {
    background: #F8FBFF;
    border: 1px solid #E5EEF8;
    border-radius: 12px;
    padding: 0.62rem 0.72rem;
}

.fr-summary-item .label {
    font-family: 'Capriola', sans-serif;
    font-size: 0.7rem;
    color: var(--wah-muted);
    margin-bottom: 0.2rem;
}

.fr-ai-hero {
    background: linear-gradient(135deg, #F8FBFF 0%, #EEF4FB 100%);
    border: 1px solid #D6E3F3;
    border-radius: 14px;
    padding: 0.8rem 0.9rem;
    margin-bottom: 0.7rem;
}
.fr-ai-label {
    font-family: 'Capriola', sans-serif;
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--wah-muted);
    margin-bottom: 0.35rem;
}
.fr-ai-value {
    font-family: 'Capriola', sans-serif;
    font-size: 1rem;
    color: var(--wah-text);
    font-weight: 700;
    line-height: 1.35;
}
.fr-ai-note {
    margin-top: 0.35rem;
    font-family: 'Capriola', sans-serif;
    font-size: 0.75rem;
    color: var(--wah-muted);
    line-height: 1.45;
}

.fr-ai-shell {
    min-height: 548px;
    display: flex;
    flex-direction: column;
}

.fr-ai-shell .fr-ai-hero {
    margin-bottom: 0.9rem;
}

.fr-ai-shell .fr-list {
    gap: 0.55rem;
}

.fr-btn-row {
    margin-top: 0.7rem;
}

.fr-action-stack {
    display: grid;
    gap: 0.55rem;
}

.fr-donut-wrap {
    display:flex;
    align-items:center;
    gap:0.9rem;
    margin-top:0.2rem;
}

.fr-donut {
    --pct: 64.2;
    --accent: #4DA8DA;
    width: 102px;
    height: 102px;
    border-radius: 50%;
    background: conic-gradient(var(--accent) calc(var(--pct) * 1%), #E9EEF5 0);
    position: relative;
    flex-shrink:0;
}

.fr-donut::before {
    content: '';
    position: absolute;
    inset: 14px;
    border-radius: 50%;
    background: white;
    border: 1px solid #E5EEF8;
}

.fr-donut-center {
    position:absolute;
    inset:0;
    display:flex;
    align-items:center;
    justify-content:center;
    flex-direction:column;
    z-index:1;
    font-family:'Capriola', sans-serif;
    color: var(--wah-text);
}

.fr-donut-center strong {
    font-size: 1rem;
}

.fr-donut-center span {
    font-size: 0.66rem;
    color: var(--wah-muted);
}

.fr-score-side {
    flex:1;
}

div[data-testid="stDownloadButton"] > button,
div.stButton > button {
    min-height: 46px !important;
    border-radius: 24px 18px 22px 20px / 16px 22px 18px 24px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 0.9rem !important;
    box-shadow: 0 5px 12px rgba(0,0,0,0.08) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}

div[data-testid="stDownloadButton"] > button:hover,
div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 7px 14px rgba(0,0,0,0.10) !important;
}

div[data-testid="stDownloadButton"] > button {
    background: #DDF3FF !important;
    color: #2A5D79 !important;
    border: 1px solid #B9E4F7 !important;
}

.fr-divider-space {
    height: 0.2rem;
}

.fr-main-grid {
    align-items: stretch;
}

.fr-main-grid > div[data-testid="column"] > div {
    height: 100%;
}





.fr-center-actions-shell {
    width: 100%;
    margin: 0.72rem 0 0 0;
    position: relative;
    z-index: 2;
}

.fr-center-actions-shell div[data-testid="stDownloadButton"] > button,
.fr-center-actions-shell div[data-testid="stButton"] > button,
.fr-center-actions-shell div.stButton > button {
    min-height: 38px !important;
    height: 38px !important;
    padding: 7px 14px !important;
    border-radius: 12px !important;
    font-family: 'Capriola', sans-serif !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    line-height: 1.1 !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}

.fr-center-actions-shell div[data-testid="stDownloadButton"] > button:hover,
.fr-center-actions-shell div[data-testid="stButton"] > button:hover,
.fr-center-actions-shell div.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 12px rgba(0,0,0,0.10) !important;
}

.fr-center-actions-shell div[data-testid="stDownloadButton"] > button {
    background: #DDF3FF !important;
    color: #2A5D79 !important;
    border: 1px solid #B9E4F7 !important;
}

.fr-center-actions-shell div[data-testid="stButton"] > button,
.fr-center-actions-shell div.stButton > button {
    background: #0070FF !important;
    color: #FFFFFF !important;
    border: none !important;
}

.fr-weight-shell {
    position: relative;
    z-index: 2;
    margin-top: 0.65rem;
}

.fr-weight-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.58rem 0.62rem;
}

.fr-weight-item {
    background: #F8FBFF;
    border: 1px solid #E5EEF8;
    border-radius: 16px;
    padding: 0.62rem 0.74rem;
    min-height: 94px;
}

.fr-weight-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.8rem;
    margin-bottom: 0.32rem;
}

.fr-weight-name {
    font-family: 'Capriola', sans-serif;
    font-size: 0.79rem;
    color: var(--wah-text);
    line-height: 1.28;
}

.fr-weight-raw {
    font-family: 'Capriola', sans-serif;
    font-size: 0.74rem;
    color: #365277;
    font-weight: 700;
    text-align: right;
    white-space: nowrap;
}

.fr-weight-sub {
    font-family: 'Capriola', sans-serif;
    font-size: 0.67rem;
    color: var(--wah-muted);
    margin-bottom: 0.26rem;
}

.fr-weight-line {
    width: 100%;
    height: 8px;
    border-radius: 999px;
    background: #E9EEF5;
    overflow: hidden;
}

.fr-weight-line > span {
    display: block;
    height: 100%;
    border-radius: 999px;
}

.fr-weight-meta {
    margin-top: 0.42rem;
    display: flex;
    justify-content: space-between;
    gap: 0.6rem;
    align-items: center;
}

.fr-weight-badge {
    display: inline-flex;
    padding: 0.24rem 0.5rem;
    border-radius: 999px;
    background: #EAF1FB;
    color: #365277;
    font-family: 'Capriola', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
}

.fr-weight-pct {
    font-family: 'Capriola', sans-serif;
    font-size: 0.74rem;
    color: #365277;
    font-weight: 700;
}


.fr-loading-wrap {
    position: relative;
    z-index: 2;
    max-width: 900px;
    margin: 1.2rem auto 1.2rem auto;
}
.fr-loading-card {
    background: rgba(255,255,255,0.94);
    border: 1px solid rgba(214,227,243,0.95);
    border-radius: 30px;
    box-shadow: 0 12px 34px rgba(15,23,42,0.08);
    padding: 30px 30px 26px;
    margin: 0 auto;
}
.fr-loader-shell {
    width: 104px;
    height: 104px;
    margin: 0 auto 16px;
    border-radius: 50%;
    background: linear-gradient(180deg,#EEF5FF 0%, #E0EEFF 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: inset 0 0 0 1px #D6E6FF;
}
.fr-loader-ring {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    border: 4px solid rgba(0,112,255,0.15);
    border-top-color: #0070FF;
    animation: frSpin 1.1s linear infinite;
}
@keyframes frSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.fr-loading-title {
    font-family: 'Capriola', sans-serif;
    font-size: clamp(28px,2.4vw,40px);
    color: #1F3864;
    line-height: 1.18;
    text-align: center;
    margin: 0 0 10px;
}
.fr-loading-copy {
    font-family: 'Capriola', sans-serif;
    font-size: 15px;
    color: #667085;
    line-height: 1.75;
    text-align: center;
    max-width: 760px;
    margin: 0 auto 20px;
}
.fr-loading-progress-wrap {
    max-width: 760px;
    margin: 10px auto 0;
}
.fr-loading-progress-label {
    font-family: 'Capriola', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #53627C;
    text-align: center;
    margin: 0 0 9px;
}
.fr-loading-progress-track {
    width: 100%;
    height: 22px;
    background: rgba(0,0,0,0.07);
    border-radius: 999px;
    overflow: hidden;
    box-shadow: inset 0 2px 6px rgba(0,0,0,0.10);
}
.fr-loading-progress-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg,#003caa 0%,#0070FF 25%,#38b6ff 50%,#0070FF 75%,#003caa 100%);
    background-size: 400% 100%;
    animation: frShimmer 2s linear infinite;
    box-shadow: 0 0 20px rgba(0,112,255,0.50),0 3px 10px rgba(0,112,255,0.24);
    transition: width .7s cubic-bezier(.4,0,.2,1);
}
@keyframes frShimmer { 0% { background-position: 200% center; } 100% { background-position: -200% center; } }
.fr-loading-status-pill {
    width: fit-content;
    margin: 12px auto 0;
    padding: 8px 14px;
    border-radius: 999px;
    background: #EEF5FF;
    border: 1px solid #DCEAFD;
    font-family: 'Capriola', sans-serif;
    font-size: 13px;
    color: #365277;
}
@media (max-width: 760px) {
    .fr-loading-card { padding: 22px 18px; border-radius: 24px; }
    .fr-loading-title { font-size: 30px; }
}

@media (max-width: 1280px) {
    .fr-center-actions-shell {
        width: min(600px, 92%);
    }
    .fr-weight-grid {
        grid-template-columns: 1fr;
    }
    .fr-ai-shell {
        min-height: auto;
    }
}




@media (max-width: 1280px) {
    .main .block-container {
        max-width: 1380px !important;
    }
    .fr-mini-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ── SVG icon helpers ───────────────────────────────────────────────────────
def _icon(path_d, size=14, color="currentColor", sw=2):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{sw}" '
        f'stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;">'
        f'{path_d}</svg>'
    )


ICON_PIN = _icon(
    '<path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z"/>'
    '<circle cx="12" cy="10" r="3"/>'
)
ICON_CLOCK = _icon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>')
ICON_HASH = _icon('<line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/>')


def _selected_site_badge(score: float):
    pct = float(score) * 100
    if pct >= 75:
        return "Highly Suitable", "#166534", "#DCFCE7"
    if pct >= 55:
        return "Suitable", "#713f12", "#FEF9C3"
    if pct >= 35:
        return "Moderately Suitable", "#92400E", "#FEF3C7"
    return "Not Suitable", "#991B1B", "#FEE2E2"


def _display_location_name(location_name, lat, lon):
    name = (location_name or "").strip()
    if name and any(ch.isalpha() for ch in name):
        return name
    if lat is not None and lon is not None:
        return f"Selected Site ({lat:.4f}, {lon:.4f})"
    return "Selected Site"


def _interp(v0, v1, t):
    return int(round(v0 + (v1 - v0) * t))


def _score_color_rgb(score):
    score = float(max(0.0, min(1.0, score)))
    anchors = [
        (0.00, (231, 76, 60)),
        (0.35, (244, 176, 64)),
        (0.55, (241, 196, 15)),
        (0.75, (127, 204, 80)),
        (1.00, (34, 197, 94)),
    ]
    for i in range(len(anchors) - 1):
        s0, c0 = anchors[i]
        s1, c1 = anchors[i + 1]
        if s0 <= score <= s1:
            t = 0.0 if s1 == s0 else (score - s0) / (s1 - s0)
            return (
                _interp(c0[0], c1[0], t),
                _interp(c0[1], c1[1], t),
                _interp(c0[2], c1[2], t),
            )
    return anchors[-1][1]


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _aoi_bounds_polygon(aoi):
    lon_min, lat_min, lon_max, lat_max = aoi
    return [
        [lat_min, lon_min],
        [lat_min, lon_max],
        [lat_max, lon_max],
        [lat_max, lon_min],
        [lat_min, lon_min],
    ]


def _mean_valid_suitability_score(suitability) -> float | None:
    if suitability is None or getattr(suitability, "data", None) is None:
        return None
    data = np.asarray(suitability.data, dtype=np.float32)
    nodata = getattr(suitability, "nodata", -9999.0)
    valid = data[np.isfinite(data)]
    valid = valid[valid != nodata]
    if valid.size == 0:
        return None
    return float(valid.mean())


def _resolve_site_score(run, selected_site):
    candidate_keys = ["overall_score", "site_score", "final_score", "score"]
    if isinstance(selected_site, dict):
        for key in candidate_keys:
            value = selected_site.get(key)
            if isinstance(value, (int, float)):
                return float(value)
    if run is not None:
        for key in candidate_keys:
            value = getattr(run, key, None)
            if isinstance(value, (int, float)):
                return float(value)
    suitability = getattr(run, "suitability", None) if run is not None else None
    return _mean_valid_suitability_score(suitability)


def _resolve_selected_site(run, location, aoi, selected_site):
    selected_site = dict(selected_site or {})
    if selected_site.get("score") is not None and selected_site.get("label"):
        return selected_site

    lat = selected_site.get("latitude", location.get("latitude"))
    lon = selected_site.get("longitude", location.get("longitude"))
    if lat is None or lon is None:
        return selected_site

    score = _resolve_site_score(run, selected_site)
    if score is None:
        return selected_site

    label, _, _ = _selected_site_badge(score)
    selected_site.setdefault(
        "site_display_name",
        _display_location_name(location.get("location_name"), lat, lon),
    )
    selected_site.setdefault("location_name", location.get("location_name"))
    selected_site["latitude"] = lat
    selected_site["longitude"] = lon
    selected_site["score"] = score
    selected_site["score_text"] = f"{score * 100:.1f}%"
    selected_site["label"] = label
    return selected_site


def _build_map_html(aoi, site_info, suitability=None, height=430):
    map_id = f"wahhaj_map_{uuid4().hex}"

    lon_min, lat_min, lon_max, lat_max = aoi
    bounds = [[lat_min, lon_min], [lat_max, lon_max]]
    aoi_outline = _aoi_bounds_polygon(aoi)

    selected_json = json.dumps(site_info, ensure_ascii=False)
    bounds_json = json.dumps(bounds)
    aoi_outline_json = json.dumps(aoi_outline)

    grid_cells = []
    if suitability is not None and getattr(suitability, "data", None) is not None:
        data = np.asarray(suitability.data, dtype=float)
        nodata = getattr(suitability, "nodata", -9999.0)

        rows, cols = data.shape[:2]
        lat_step = (lat_max - lat_min) / rows
        lon_step = (lon_max - lon_min) / cols

        for r in range(rows):
            for c in range(cols):
                score = float(data[r, c])
                if not np.isfinite(score) or score == nodata:
                    continue

                score = max(0.0, min(1.0, score))
                color = _rgb_to_hex(_score_color_rgb(score))

                cell_lat_max = lat_max - (r * lat_step)
                cell_lat_min = lat_max - ((r + 1) * lat_step)
                cell_lon_min = lon_min + (c * lon_step)
                cell_lon_max = lon_min + ((c + 1) * lon_step)

                grid_cells.append({
                    "bounds": [[cell_lat_min, cell_lon_min], [cell_lat_max, cell_lon_max]],
                    "score_text": f"{score * 100:.1f}%",
                    "fillColor": color,
                })

    grid_json = json.dumps(grid_cells, ensure_ascii=False)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; background: transparent; }}
        #{map_id} {{
            width: 100%;
            height: {height}px;
            border-radius: 0 0 18px 18px;
            overflow: hidden;
        }}
        .leaflet-container {{ font-family: Arial, sans-serif; background: #eaeaea; }}
        .leaflet-control-attribution {{ font-size: 10px; }}
        .wahhaj-legend {{
            background: rgba(255,255,255,0.95);
            border-radius: 12px;
            padding: 10px 12px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.12);
            line-height: 1.35;
            min-width: 210px;
        }}
        .wahhaj-legend-title {{
            font-size: 12px;
            font-weight: 700;
            color: #1f3864;
            margin-bottom: 7px;
        }}
        .wahhaj-legend-bar {{
            height: 10px;
            border-radius: 999px;
            background: linear-gradient(90deg, #e74c3c, #f4b040, #f1c40f, #7fcc50, #22c55e);
            margin-bottom: 6px;
        }}
        .wahhaj-legend-scale {{
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            color: #666;
            margin-bottom: 6px;
        }}
        .wahhaj-legend-note {{
            font-size: 10px;
            color: #666;
            margin-bottom: 3px;
        }}
        .selected-label {{ background: transparent; border: none; }}
        .selected-label div {{
            background: rgba(0,112,255,0.96);
            color: #fff;
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            box-shadow: 0 4px 14px rgba(0,0,0,0.18);
        }}
        .wahhaj-popup-title {{
            font-size: 13px;
            font-weight: 700;
            color: #1f3864;
            margin-bottom: 4px;
        }}
        .wahhaj-popup-line {{
            font-size: 12px;
            color: #444;
            margin-bottom: 2px;
        }}
    </style>
</head>
<body>
    <div id="{map_id}"></div>
    <script>
        const selected = {selected_json};
        const bounds = {bounds_json};
        const aoiOutline = {aoi_outline_json};
        const gridCells = {grid_json};

        const map = L.map("{map_id}", {{ zoomControl: true, scrollWheelZoom: true, preferCanvas: true }});

        const satellite = L.tileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
            {{ attribution: "Tiles &copy; Esri, Maxar, Earthstar Geographics, and contributors", maxZoom: 19 }}
        );
        const streets = L.tileLayer(
            "https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",
            {{ attribution: "&copy; OpenStreetMap contributors", maxZoom: 19 }}
        );

        satellite.addTo(map);
        L.control.layers({{"Satellite": satellite, "Streets": streets}}, null, {{ collapsed: true, position: "topright" }}).addTo(map);

        gridCells.forEach(cell => {{
            L.rectangle(cell.bounds, {{
                color: "#4a8f2a",
                weight: 0.55,
                fill: true,
                fillColor: cell.fillColor,
                fillOpacity: 0.42
            }})
            .bindTooltip(`Suitability Score: ${{cell.score_text}}`)
            .addTo(map);
        }});

        L.polygon(aoiOutline, {{
            color: "#0070FF",
            weight: 2.8,
            fill: false
        }}).addTo(map);

        const selectedIcon = L.divIcon({{
            className: "selected-label",
            html: `<div>${{selected.name}}</div>`,
            iconSize: [130, 26],
            iconAnchor: [65, -6]
        }});

        L.circleMarker([selected.lat, selected.lon], {{
            radius: 8,
            color: "#0070FF",
            weight: 3,
            fillColor: "#ffffff",
            fillOpacity: 0.95
        }})
        .bindPopup(`
            <div class="wahhaj-popup-title">${{selected.name}}</div>
            <div class="wahhaj-popup-line">Overall score: ${{selected.score_text}}</div>
            <div class="wahhaj-popup-line">Suitability: ${{selected.suitability}}</div>
        `)
        .addTo(map);

        L.marker([selected.lat, selected.lon], {{ icon: selectedIcon }}).addTo(map);
        map.fitBounds(bounds, {{ padding: [24, 24] }});

        const legend = L.control({{ position: "bottomleft" }});
        legend.onAdd = function() {{
            const div = L.DomUtil.create("div", "wahhaj-legend");
            div.innerHTML = `
                <div class="wahhaj-legend-title">Selected Location Suitability Scale</div>
                <div class="wahhaj-legend-bar"></div>
                <div class="wahhaj-legend-scale"><span>Low</span><span>High</span></div>
                <div class="wahhaj-legend-note">Blue outline = selected analysis boundary</div>
                <div class="wahhaj-legend-note">Colored cells = AHP suitability scores</div>
                <div class="wahhaj-legend-note">Blue marker = selected site center</div>
            `;
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
"""


def _recommendation_text(label: str) -> str:
    label_l = (label or "").lower()
    if "high" in label_l:
        return "Recommended for solar site consideration based on the current weighted environmental and geospatial assessment."
    if "moderate" in label_l:
        return "Conditionally recommended and may benefit from additional field validation before final adoption."
    if "not" in label_l:
        return "Not recommended at this stage based on the current suitability assessment."
    return "Recommended for further review based on the current site analysis results."


def _safe_text(value, default="—"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _safe_html(value, default="—"):
    return escape(_safe_text(value, default))


def _factor_accent(index: int) -> str:
    palette = ["#1F3864", "#2F6DB2", "#F59E0B", "#10B981", "#8B5CF6", "#EC4899"]
    return palette[index % len(palette)]


def _normalize_factor_bars(factors: list[dict]) -> list[dict]:
    values = [max(0.0, float(item.get("contribution_pct", 0.0) or 0.0)) for item in factors]
    max_val = max(values) if values else 1.0
    max_val = max(max_val, 1.0)
    out = []
    for idx, item in enumerate(factors):
        value = max(0.0, float(item.get("contribution_pct", 0.0) or 0.0))
        out.append(
            {
                **item,
                "bar_pct": max(14.0, min(100.0, (value / max_val) * 100.0 if max_val else 0.0)),
                "accent": _factor_accent(idx),
            }
        )
    return out


def _factor_snapshot_html(factors: list[dict]) -> str:
    cards = []
    for idx, item in enumerate(factors[:5]):
        title = _safe_html(item.get("title", item.get("name", "Factor")))
        raw_label = _safe_html(item.get("raw_label"))
        score = float(item.get("contribution_pct", 0.0) or 0.0)
        accent = _factor_accent(idx)
        cards.append(
            '<div class="fr-mini-factor">'
            f'<h4>{title}</h4>'
            f'<div class="fr-mini-raw">{raw_label}</div>'
            f'<div class="fr-mini-pill" style="background:{accent}18;color:{accent};">Weighted impact {score:.1f}%</div>'
            '</div>'
        )
    return '<div class="fr-mini-grid">' + "".join(cards) + "</div>"


def _reason_list_html(reasons: list[dict]) -> str:
    if not reasons:
        reasons = [{"reason": "Selected site interpretation will appear here after the analysis is completed."}]
    rows = []
    for item in reasons[:4]:
        text = _safe_html(item.get("reason") or item.get("title") or item.get("name"))
        rows.append(f'<div class="fr-list-item"><span class="fr-dot"></span><span>{text}</span></div>')
    return '<div class="fr-list">' + "".join(rows) + "</div>"


def _weight_panel_html(factors: list[dict]) -> str:
    if not factors:
        return '<div class="fr-mini-note" style="margin-top:0;">No factor contribution data available.</div>'
    cards = []
    for idx, item in enumerate(_normalize_factor_bars(factors)):
        title = _safe_html(item.get("title") or item.get("name") or f"Factor {idx + 1}")
        raw_label = _safe_html(item.get("raw_label"), "No value")
        contribution = float(item.get("contribution_pct", 0.0) or 0.0)
        bar_pct = float(item.get("bar_pct", 0.0) or 0.0)
        accent = item.get("accent", _factor_accent(idx))
        weight_pct = item.get("weight_pct")
        badge_text = f"Weight {float(weight_pct):.1f}%" if isinstance(weight_pct, (int, float)) else "Weighted factor"
        cards.append(
            '<div class="fr-weight-item">'
            '<div class="fr-weight-top">'
            f'<div class="fr-weight-name">{title}</div>'
            f'<div class="fr-weight-raw">{raw_label}</div>'
            '</div>'
            '<div class="fr-weight-sub">Contribution to the selected-site result</div>'
            f'<div class="fr-weight-line"><span style="width:{bar_pct:.1f}%;background:{accent};"></span></div>'
            '<div class="fr-weight-meta">'
            f'<span class="fr-weight-badge">{escape(badge_text)}</span>'
            f'<span class="fr-weight-pct">{contribution:.1f}%</span>'
            '</div>'
            '</div>'
        )
    return '<div class="fr-weight-grid">' + ''.join(cards) + '</div>'

def _summary_item(label: str, value: str) -> str:
    return (
        '<div class="fr-summary-item">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(value)}</div>'
        '</div>'
    )





def _render_final_report_loading(slot, progress_pct: int = 58, progress_msg: str = "Preparing final report...") -> None:
    progress_pct = max(8, min(98, int(progress_pct)))
    slot.markdown(
        f"""
        <div class="fr-loading-wrap">
            <div class="fr-loading-card">
                <div class="fr-loader-shell"><div class="fr-loader-ring"></div></div>
                <div class="fr-loading-title">Preparing Final Report</div>
                <div class="fr-loading-copy">WAHHAJ is loading the report content, map details, and stored PDF file. This may take a few moments.</div>
                <div class="fr-loading-progress-wrap">
                    <div class="fr-loading-progress-label">{escape(progress_msg)}</div>
                    <div class="fr-loading-progress-track"><div class="fr-loading-progress-fill" style="width:{progress_pct}%;"></div></div>
                    <div class="fr-loading-status-pill">Final report is loading...</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _safe_aoi(value):
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            lon_min, lat_min, lon_max, lat_max = [float(v) for v in value]
            if lon_min < lon_max and lat_min < lat_max:
                return (lon_min, lat_min, lon_max, lat_max)
        except Exception:
            return None
    return None


def _clean_ranked_for_storage(items: list) -> list[dict]:
    clean = []
    for idx, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        score = _safe_float(item.get("score"), 0.0)
        clean.append({
            "rank": item.get("rank", idx),
            "report_id": item.get("report_id"),
            "run_id": item.get("run_id"),
            "location_name": item.get("location_name") or "Unnamed Site",
            "lat": item.get("lat"),
            "lon": item.get("lon"),
            "score": score,
            "score_pct": item.get("score_pct") or f"{score * 100:.1f}%",
            "label": item.get("label") or item.get("recommendation") or "Review Required",
            "analysed_at": item.get("analysed_at") or item.get("report_date") or "—",
        })
    return clean


def _display_from_saved_report(report: dict) -> dict:
    criteria = report.get("criteria_data") or {}
    if isinstance(criteria, dict):
        display = criteria.get("display") or criteria.get("report_data") or criteria
    else:
        display = {}

    final_score = _safe_float(report.get("final_score"), _safe_float(display.get("selected_score"), 0.0))
    final_label = report.get("final_label") or display.get("selected_label") or "—"
    score_text = display.get("selected_score_text") or f"{final_score * 100:.1f}%"

    lat = _safe_float(report.get("lat"), _safe_float(display.get("selected_lat")))
    lon = _safe_float(report.get("lon"), _safe_float(display.get("selected_lon")))
    coords = display.get("selected_coords") or (f"{lat:.4f}°N, {lon:.4f}°E" if lat is not None and lon is not None else "—")

    selected_color = display.get("selected_color") or "#1a1a1a"
    selected_bg = display.get("selected_bg") or "#EEF4FB"
    if final_score is not None and not display.get("selected_color"):
        _, selected_color, selected_bg = _selected_site_badge(float(final_score))

    return {
        "report_id": report.get("report_id") or "—",
        "run_id": report.get("run_id") or "—",
        "location_name": report.get("location_name") or display.get("location_name") or "Selected Site",
        "selected_display_name": display.get("selected_display_name") or report.get("location_name") or "Selected Site",
        "selected_score": final_score,
        "selected_score_text": score_text,
        "selected_label": final_label,
        "selected_color": selected_color,
        "selected_bg": selected_bg,
        "selected_lat": lat,
        "selected_lon": lon,
        "selected_coords": coords,
        "aoi": _safe_aoi(report.get("aoi") or display.get("aoi")),
        "recommendation": report.get("recommendation") or display.get("recommendation") or _recommendation_text(final_label),
        "report_date": report.get("report_date") or display.get("now") or "—",
        "status_text": display.get("status_text") or "Completed",
        "duration_text": display.get("duration_text") or "—",
        "image_name": display.get("image_name") or "Uploaded image",
        "ai_assessment": display.get("ai_assessment") or "Pending AI model result",
        "reasons": display.get("reasons") or [],
        "factors": report.get("factors_data") or display.get("factors") or [],
        "ranked_sites": report.get("ranked_sites") or [],
        "global_rank_text": display.get("global_rank_text") or "Saved report",
        "pdf_bytes": report.get("pdf_file"),
        "pdf_filename": report.get("pdf_filename") or f"wahhaj_report_{str(report.get('report_id') or 'saved')[:8]}.pdf",
    }


def _render_saved_final_report(report: dict) -> None:
    data = _display_from_saved_report(report)

    selected_score = data["selected_score"] or 0.0
    selected_label = data["selected_label"]
    selected_score_text = data["selected_score_text"]
    selected_color = data["selected_color"]
    selected_bg = data["selected_bg"]
    selected_display_name = data["selected_display_name"]
    selected_lat = data["selected_lat"]
    selected_lon = data["selected_lon"]
    selected_coords = data["selected_coords"]
    aoi = data["aoi"]
    factors = list(data["factors"] or [])
    reasons = list(data["reasons"] or [])

    if not factors:
        factors = [
            {"title": "Solar Irradiance", "raw_label": "Saved report data", "contribution_pct": 0.0},
            {"title": "Sunshine Hours", "raw_label": "Saved report data", "contribution_pct": 0.0},
            {"title": "Terrain Slope", "raw_label": "Saved report data", "contribution_pct": 0.0},
            {"title": "LST", "raw_label": "Saved report data", "contribution_pct": 0.0},
            {"title": "Elevation", "raw_label": "Saved report data", "contribution_pct": 0.0},
        ]

    report_id_short = f"{str(data['report_id'])[:8]}..." if data.get("report_id") else "—"
    run_id_short = f"{str(data['run_id'])[:8]}..." if data.get("run_id") else "—"
    now = str(data.get("report_date") or "—")

    st.markdown(
        f"""
<div class="fr-header-shell">
  <div class="fr-header">
    <div class="fr-title">Final Site Suitability Report</div>
    <div class="fr-subtitle">Saved report page loaded from the system database with its stored PDF file.</div>
    <div class="fr-chip-row">
      <span class="fr-chip">{ICON_PIN}<span>{_safe_html(data.get('location_name') or selected_display_name)}</span></span>
      <span class="fr-chip">{ICON_CLOCK}<span>{escape(now)}</span></span>
      <span class="fr-chip">{ICON_HASH}<span>Report {escape(report_id_short)}</span></span>
      <span class="fr-chip">{ICON_HASH}<span>Run {escape(run_id_short)}</span></span>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="fr-divider-space"></div>', unsafe_allow_html=True)
    left_col, center_col, right_col = st.columns([1.00, 1.78, 1.20], gap="small")

    with left_col:
        score_bar_width = float(selected_score or 0.0) * 100.0
        st.markdown(
            f"""
            <div class="fr-card">
                <div class="fr-card-title">Overall Suitability Score</div>
                <div class="fr-badge" style="background:{selected_bg};color:{selected_color};">{_safe_html(selected_label)}</div>
                <div class="fr-donut-wrap">
                    <div class="fr-donut" style="--pct:{score_bar_width:.1f};--accent:{selected_color};">
                        <div class="fr-donut-center"><strong>{_safe_html(selected_score_text)}</strong><span>Score</span></div>
                    </div>
                    <div class="fr-score-side">
                        <div class="fr-score-label">Selected site result</div>
                        <div class="fr-progress"><span style="width:{score_bar_width:.1f}%;background:{selected_color};"></span></div>
                        <div class="fr-mini-note">This saved score represents the stored final suitability result for this report.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="fr-card">
                <div class="fr-card-title compact">Recommendation</div>
                <div class="fr-mini-note" style="margin-top:0;color:#162033;font-size:0.82rem;">{escape(data['recommendation'])}</div>
                <div class="fr-mini-note" style="margin-top:0.55rem;color:#475569;font-size:0.78rem;"><b>Global Rank:</b> {_safe_html(data['global_rank_text'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="fr-card">
                <div class="fr-card-title compact">Site Information</div>
                <div class="fr-kv-grid">
                    <div class="fr-kv-item"><div class="fr-kv-label">Display Name</div><div class="fr-kv-value">{_safe_html(selected_display_name)}</div></div>
                    <div class="fr-kv-item"><div class="fr-kv-label">Coordinates</div><div class="fr-kv-value">{_safe_html(selected_coords)}</div></div>
                    <div class="fr-kv-item"><div class="fr-kv-label">Image Source</div><div class="fr-kv-value">{_safe_html(data['image_name'])}</div></div>
                    <div class="fr-kv-item"><div class="fr-kv-label">Run Status</div><div class="fr-kv-value">{_safe_html(data['status_text'])}</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with center_col:
        st.markdown(
            """
            <div class="fr-card" style="padding:0;overflow:hidden;">
                <div class="fr-map-title">
                    <div class="fr-card-title compact">Selected Site Suitability Map</div>
                    <div class="fr-map-caption">Saved AOI view reconstructed from the stored report record.</div>
                </div>
            """,
            unsafe_allow_html=True,
        )
        if aoi and selected_lat is not None and selected_lon is not None and selected_score is not None:
            fill_color = _rgb_to_hex(_score_color_rgb(float(selected_score)))
            site_info = {
                "name": selected_display_name,
                "score_text": selected_score_text,
                "suitability": selected_label,
                "lat": selected_lat,
                "lon": selected_lon,
                "fillColor": fill_color,
            }
            st.markdown('<div class="fr-map-shell">', unsafe_allow_html=True)
            components.html(_build_map_html(aoi=aoi, site_info=site_info, height=430), height=432, scrolling=False)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                """
                <div class="fr-card" style="min-height:432px;display:flex;align-items:center;justify-content:center;">
                    <div class="fr-mini-note" style="margin-top:0;text-align:center;max-width:420px;">Saved map data is not available for this report.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with right_col:
        st.markdown(
            f"""
            <div class="fr-card fr-ai-shell">
                <div class="fr-card-title">AI Assessment</div>
                <div class="fr-ai-hero">
                    <div class="fr-ai-label">AI image assessment</div>
                    <div class="fr-ai-value">{_safe_html(data['ai_assessment'])}</div>
                    <div class="fr-ai-note">This saved assessment is loaded from the stored report record.</div>
                </div>
                <div class="fr-card-title compact">Key Drivers Behind This Score</div>
                {_reason_list_html(reasons)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="fr-card fr-weight-shell">
            <div class="fr-card-title">Weighted Factor Contribution</div>
            {_weight_panel_html(factors)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="fr-center-actions-shell">', unsafe_allow_html=True)
    pdf_sp_left, pdf_col, pdf_sp_right = st.columns([1.75, 2.50, 1.75], gap="small")
    with pdf_col:
        if data.get("pdf_bytes"):
            st.download_button(
                "Export PDF",
                data=data["pdf_bytes"],
                file_name=data["pdf_filename"],
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("No saved PDF is available for this report.")

    st.markdown('<div style="height:0.42rem"></div>', unsafe_allow_html=True)
    btn_sp_left, btn_left, btn_gap, btn_right, btn_sp_right = st.columns([1.70, 1.20, 0.06, 1.20, 1.70], gap="small")
    with btn_left:
        st.button(
            "View Heatmap",
            use_container_width=True,
            key="saved_report_view_heatmap_btn",
            on_click=_queue_final_report_navigation,
            args=("pages/6_Suitability_Heatmap.py", False),
        )
    with btn_right:
        st.button(
            "New Analysis",
            use_container_width=True,
            key="saved_report_new_analysis_btn",
            on_click=_queue_final_report_navigation,
            args=("pages/3_Choose_Location.py", True),
        )
    st.markdown('</div>', unsafe_allow_html=True)


# ── initial loading only ────────────────────────────────────────────────────
_report_loading_slot = st.empty()

_run_for_loading = st.session_state.get("analysis_run")
_loading_ref = (
    getattr(_run_for_loading, "runId", None)
    or st.session_state.get("current_report_id")
    or "current"
)
_loading_key = f"final_report_initial_loading_done_{_loading_ref}"

_show_initial_loading = not st.session_state.get(_loading_key, False)

if _show_initial_loading:
    _render_final_report_loading(
        _report_loading_slot,
        46,
        "Opening final report..."
    )

# ── saved report mode: open real report records from the database ───────────
_saved_report_id = st.session_state.get("current_report_id")
_saved_report_requested = bool(
    _saved_report_id
    and (
        st.session_state.get("saved_report_open_requested")
        or st.session_state.get("analysis_run") is None
    )
)

if _saved_report_requested:
    saved_report = st.session_state.get("saved_report_data")
    if not saved_report or str(saved_report.get("report_id")) != str(_saved_report_id):
        saved_report = load_final_report_from_db(str(_saved_report_id))

    if saved_report:
        _report_loading_slot.empty()
        _render_saved_final_report(saved_report)
        st.stop()

    _report_loading_slot.empty()
    st.markdown('<div class="fr-card">', unsafe_allow_html=True)
    st.error("The saved report could not be loaded from the database.")
    st.button(
        "Back Home",
        key="saved_report_error_back_home_btn",
        on_click=_queue_final_report_navigation,
        args=("pages/2_Home.py", False),
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ── guard: need a completed run ────────────────────────────────────────────
run = st.session_state.get("analysis_run")
if run is None:
    _report_loading_slot.empty()
    st.markdown('<div class="fr-card">', unsafe_allow_html=True)
    st.warning("No analysis found. Complete the pipeline first.")
    st.button(
        "Back to Analysis",
        key="final_report_missing_back_analysis_btn",
        on_click=_queue_final_report_navigation,
        args=("pages/5_Analysis.py", False),
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


from Wahhaj.SiteCandidate import SiteCandidate
from Wahhaj.report import Report

loc = st.session_state.get("selected_location", {})
# Local candidate ranking is still used for the selected AOI/heatmap details.
# The user-facing/global rank comes from analysis_history via get_ranked_history().
ranked = SiteCandidate.rank_all(list(run.candidates)) if getattr(run, "candidates", None) else []
summary = run.summary()
aoi = st.session_state.get("aoi", (0, 0, 0, 0))
selected_site = _resolve_selected_site(
    run,
    loc,
    aoi if isinstance(aoi, tuple) and len(aoi) == 4 else None,
    st.session_state.get("selected_site_analysis", {}),
)
st.session_state["selected_site_analysis"] = selected_site

selected_score = selected_site.get("score")
selected_label = selected_site.get("label") or "—"
selected_score_text = selected_site.get("score_text") or (
    f"{float(selected_score) * 100:.1f}%" if selected_score is not None else "—"
)
selected_display_name = selected_site.get("site_display_name") or loc.get("location_name") or "Selected Site"
selected_lat = selected_site.get("latitude", loc.get("latitude"))
selected_lon = selected_site.get("longitude", loc.get("longitude"))
selected_coords = (
    f"{selected_lat:.4f}°N, {selected_lon:.4f}°E"
    if selected_lat is not None and selected_lon is not None
    else "—"
)
selected_color = "#1a1a1a"
selected_bg = "#EEF4FB"
if selected_score is not None:
    _, selected_color, selected_bg = _selected_site_badge(float(selected_score))

if "report_obj" not in st.session_state or st.session_state["report_obj"] is None:
    rpt = Report()
    rpt.generate(run, ranked, location=loc, selected_site=selected_site)
    st.session_state["report_obj"] = rpt
else:
    rpt = st.session_state["report_obj"]

if selected_score is not None:
    rpt.summary = (
        f"Solar site analysis for {loc.get('location_name', 'the selected site')} completed on "
        f"{datetime.now().strftime('%Y-%m-%d')}. "
        f"The analysed location achieved a suitability score of {selected_score_text} "
        f"and was classified as {selected_label}."
    )

save_analysis_to_history(run, ranked, loc)
global_ranked_sites = get_ranked_history()
current_global_rank, total_ranked_sites = get_global_rank_for_run(getattr(run, "runId", None))
global_rank_text = (
    f"#{current_global_rank} out of {total_ranked_sites} saved site{'s' if total_ranked_sites != 1 else ''}"
    if current_global_rank else
    "Not ranked yet"
)

now = datetime.now().strftime("%d %b %Y • %H:%M")
report_id_short = f"{str(rpt.report_id)[:8]}..." if getattr(rpt, "report_id", None) else "—"
run_id_short = f"{str(run.runId)[:8]}..." if getattr(run, "runId", None) else "—"
duration_text = f"{summary.get('durationSec', '—')} sec"
status_text = _safe_text(summary.get("status"), "Completed")
image_name = _safe_text(selected_site.get("image_name"), "Uploaded image")
ai_assessment = _safe_text(selected_site.get("ai_assessment"), "Pending AI model result")
recommendation = _recommendation_text(selected_label)
factors = list(selected_site.get("factors") or [])
reasons = list(selected_site.get("reasons") or [])

if not factors:
    factors = [
        {"title": "Solar Irradiance", "raw_label": "No factor data", "contribution_pct": 0.0},
        {"title": "Sunshine Hours", "raw_label": "No factor data", "contribution_pct": 0.0},
        {"title": "Terrain Slope", "raw_label": "No factor data", "contribution_pct": 0.0},
        {"title": "Obstacle Density", "raw_label": "No factor data", "contribution_pct": 0.0},
        {"title": "Elevation", "raw_label": "No factor data", "contribution_pct": 0.0},
    ]

st.markdown(
    f"""
<div class="fr-header-shell">
  <div class="fr-header">
    <div class="fr-title">Final Site Suitability Report</div>
    <div class="fr-subtitle">Single-screen summary for the selected analysed site with the map, decision cues, and export controls visible together.</div>
    <div class="fr-chip-row">
      <span class="fr-chip">{ICON_PIN}<span>{_safe_html(loc.get('location_name') or selected_display_name)}</span></span>
      <span class="fr-chip">{ICON_CLOCK}<span>{escape(now)}</span></span>
      <span class="fr-chip">{ICON_HASH}<span>Report {escape(report_id_short)}</span></span>
      <span class="fr-chip">{ICON_HASH}<span>Run {escape(run_id_short)}</span></span>
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)



report_text = rpt._generate_report_content(run, ranked)

pdf_cache_key = f"final_report_pdf_bytes_{getattr(run, 'runId', 'current')}"
pdf_bytes = st.session_state.get(pdf_cache_key)

# Save this Final Report as a real database record exactly once per run.
# The PDF bytes stored here are reused later; old reports do not regenerate the PDF.
_report_id_for_db = str(st.session_state.get("current_report_id") or f"report_{getattr(run, 'runId', uuid4().hex)}")
_pdf_filename = f"wahhaj_report_{str(getattr(run, 'runId', _report_id_for_db))[:8]}.pdf"

if pdf_bytes is None:
    if _show_initial_loading:
        _render_final_report_loading(_report_loading_slot, 78, "Generating the report PDF...")
    pdf_bytes = rpt.build_pdf_bytes(
        run,
        ranked,
        location=loc,
        suitability=run.suitability if run else None,
        aoi=aoi if aoi and len(aoi) == 4 else None,
        selected_site=selected_site,
        global_ranked_sites=global_ranked_sites,
    )
    st.session_state[pdf_cache_key] = pdf_bytes

_saved_ranked_sites = _clean_ranked_for_storage(global_ranked_sites)
_report_display_data = {
    "report_id": _report_id_for_db,
    "run_id": getattr(run, "runId", None),
    "user_email": st.session_state.get("user_email", ""),
    "location_name": loc.get("location_name") or selected_display_name,
    "lat": selected_lat,
    "lon": selected_lon,
    "aoi": list(aoi) if isinstance(aoi, (list, tuple)) and len(aoi) == 4 else None,
    "final_score": float(selected_score) if selected_score is not None else None,
    "final_label": selected_label,
    "recommendation": recommendation,
    "factors": factors,
    "reasons": reasons,
    "ranked_sites": _saved_ranked_sites,
    "report_text": report_text,
    "display": {
        "location_name": loc.get("location_name") or selected_display_name,
        "selected_display_name": selected_display_name,
        "selected_score": float(selected_score) if selected_score is not None else None,
        "selected_score_text": selected_score_text,
        "selected_label": selected_label,
        "selected_color": selected_color,
        "selected_bg": selected_bg,
        "selected_lat": selected_lat,
        "selected_lon": selected_lon,
        "selected_coords": selected_coords,
        "aoi": list(aoi) if isinstance(aoi, (list, tuple)) and len(aoi) == 4 else None,
        "recommendation": recommendation,
        "global_rank_text": global_rank_text,
        "now": now,
        "duration_text": duration_text,
        "status_text": status_text,
        "image_name": image_name,
        "ai_assessment": ai_assessment,
        "factors": factors,
        "reasons": reasons,
    },
}


_report_save_key = f"final_report_saved_{_report_id_for_db}"
_report_pdf_save_key = f"final_report_pdf_saved_{_report_id_for_db}"

if (not st.session_state.get(_report_save_key, False)) or (
    pdf_bytes is not None and not st.session_state.get(_report_pdf_save_key, False)
):
    _saved_report_id = save_final_report_to_db(
        {
            "report_id": _report_id_for_db,
            "run_id": getattr(run, "runId", None),
            "user_email": st.session_state.get("user_email", ""),
            "location_name": loc.get("location_name") or selected_display_name,
            "lat": selected_lat,
            "lon": selected_lon,
            "aoi": list(aoi) if isinstance(aoi, (list, tuple)) and len(aoi) == 4 else None,
            "final_score": float(selected_score) if selected_score is not None else None,
            "final_label": selected_label,
            "recommendation": recommendation,
            "criteria_data": _report_display_data,
            "factors_data": factors,
            "ranked_sites": _saved_ranked_sites,
            "report_date": datetime.now().isoformat(),
        },
        pdf_bytes,
        pdf_filename=_pdf_filename,
        report_id=_report_id_for_db,
    )

    if _saved_report_id:
        st.session_state["current_report_id"] = _saved_report_id

    st.session_state[_report_save_key] = True
    if pdf_bytes is not None:
        st.session_state[_report_pdf_save_key] = True


_report_loading_slot.empty()

if _show_initial_loading:
    st.session_state[_loading_key] = True

st.markdown('<div class="fr-divider-space"></div>', unsafe_allow_html=True)

left_col, center_col, right_col = st.columns([1.00, 1.78, 1.20], gap="small")

with left_col:
    score_bar_width = float(selected_score or 0.0) * 100.0
    st.markdown(
        f"""
        <div class="fr-card">
            <div class="fr-card-title">Overall Suitability Score</div>
            <div class="fr-badge" style="background:{selected_bg};color:{selected_color};">{_safe_html(selected_label)}</div>
            <div class="fr-donut-wrap">
                <div class="fr-donut" style="--pct:{score_bar_width:.1f};--accent:{selected_color};">
                    <div class="fr-donut-center"><strong>{_safe_html(selected_score_text)}</strong><span>Score</span></div>
                </div>
                <div class="fr-score-side">
                    <div class="fr-score-label">Selected site result</div>
                    <div class="fr-progress"><span style="width:{score_bar_width:.1f}%;background:{selected_color};"></span></div>
                    <div class="fr-mini-note">This score represents the consolidated suitability estimate for the chosen site based on the currently processed layers.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="fr-card">
            <div class="fr-card-title compact">Recommendation</div>
            <div class="fr-mini-note" style="margin-top:0;color:#162033;font-size:0.82rem;">{escape(recommendation)}</div>
            <div class="fr-mini-note" style="margin-top:0.55rem;color:#475569;font-size:0.78rem;"><b>Global Rank:</b> {_safe_html(global_rank_text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="fr-card">
            <div class="fr-card-title compact">Site Information</div>
            <div class="fr-kv-grid">
                <div class="fr-kv-item">
                    <div class="fr-kv-label">Display Name</div>
                    <div class="fr-kv-value">{_safe_html(selected_display_name)}</div>
                </div>
                <div class="fr-kv-item">
                    <div class="fr-kv-label">Coordinates</div>
                    <div class="fr-kv-value">{_safe_html(selected_coords)}</div>
                </div>
                <div class="fr-kv-item">
                    <div class="fr-kv-label">Image Source</div>
                    <div class="fr-kv-value">{_safe_html(image_name)}</div>
                </div>
                <div class="fr-kv-item">
                    <div class="fr-kv-label">Run Status</div>
                    <div class="fr-kv-value">{_safe_html(status_text)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with center_col:
    st.markdown(
        """
        <div class="fr-card" style="padding:0;overflow:hidden;">
            <div class="fr-map-title">
                <div class="fr-card-title compact">Selected Site Suitability Map</div>
                <div class="fr-map-caption">Satellite view of the selected AOI with the analysed site marker and suitability overlay.</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    if run.suitability is not None and aoi and len(aoi) == 4 and selected_lat is not None and selected_lon is not None and selected_score is not None:
        fill_color = _rgb_to_hex(_score_color_rgb(float(selected_score)))
        site_info = {
            "name": selected_display_name,
            "score_text": selected_score_text,
            "suitability": selected_label,
            "lat": selected_lat,
            "lon": selected_lon,
            "fillColor": fill_color,
        }
        st.markdown('<div class="fr-map-shell">', unsafe_allow_html=True)
        components.html(
            _build_map_html(
                aoi=aoi,
                site_info=site_info,
                suitability=run.suitability,
                height=430,
            ),
            height=432,
            scrolling=False,
        )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div class="fr-card" style="min-height:432px;display:flex;align-items:center;justify-content:center;">
                <div class="fr-mini-note" style="margin-top:0;text-align:center;max-width:420px;">
                    The selected-site map will appear here once suitability, AOI bounds, and site coordinates are available.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown(
        f"""
        <div class="fr-card fr-ai-shell">
            <div class="fr-card-title">AI Assessment</div>
            <div class="fr-ai-hero">
                <div class="fr-ai-label">AI image assessment</div>
                <div class="fr-ai-value">{_safe_html(ai_assessment)}</div>
                <div class="fr-ai-note">This result is shown here deliberately as a primary decision cue, not as a secondary footer item.</div>
            </div>
            <div class="fr-card-title compact">Key Drivers Behind This Score</div>
            {_reason_list_html(reasons)}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    f"""
    <div class="fr-card fr-weight-shell">
        <div class="fr-card-title">Weighted Factor Contribution</div>
        {_weight_panel_html(factors)}
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="fr-center-actions-shell">', unsafe_allow_html=True)
pdf_sp_left, pdf_col, pdf_sp_right = st.columns([1.75, 2.50, 1.75], gap="small")

with pdf_col:
    pdf_cache_key = f"final_report_pdf_bytes_{getattr(run, 'runId', 'current')}"

    if st.session_state.get(pdf_cache_key):
        st.download_button(
            "Export PDF",
            data=st.session_state[pdf_cache_key],
            file_name=_pdf_filename,
            mime="application/pdf",
            use_container_width=True,
            key="download_current_report_pdf_btn",
        )
    else:
        if st.button("Generate PDF", use_container_width=True, key="generate_current_report_pdf_btn"):
            st.session_state[pdf_cache_key] = rpt.build_pdf_bytes(
                run,
                ranked,
                location=loc,
                suitability=run.suitability if run else None,
                aoi=aoi if aoi and len(aoi) == 4 else None,
                selected_site=selected_site,
                global_ranked_sites=global_ranked_sites,
            )
            st.rerun()

st.markdown('<div style="height:0.42rem"></div>', unsafe_allow_html=True)
btn_sp_left, btn_left, btn_gap, btn_right, btn_sp_right = st.columns([1.70, 1.20, 0.06, 1.20, 1.70], gap="small")
with btn_left:
    st.button(
        "View Heatmap",
        use_container_width=True,
        key="final_report_back_to_map_btn",
        on_click=_queue_final_report_navigation,
        args=("pages/6_Suitability_Heatmap.py", False),
    )

with btn_right:
    st.button(
        "New Analysis",
        use_container_width=True,
        key="final_report_new_analysis_btn",
        on_click=_queue_final_report_navigation,
        args=("pages/3_Choose_Location.py", True),
    )
st.markdown('</div>', unsafe_allow_html=True)

