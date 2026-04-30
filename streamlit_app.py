import base64
from pathlib import Path

import streamlit as st
from ui_helpers import init_state, apply_global_style, render_bg, render_footer

st.set_page_config(page_title="WAHHAJ", layout="wide")

init_state()
apply_global_style()
render_bg()


def render_center_logo(image_path: str = "assets/wahhaj_logo.png", width: int = 700):
    path = Path(image_path)

    if not path.exists():
        st.error(f"Logo not found: {image_path}")
        return

    encoded = base64.b64encode(path.read_bytes()).decode()

    st.markdown(
        f"""
        <div class="wahhaj-logo-wrapper">
            <img src="data:image/png;base64,{encoded}" class="wahhaj-logo-img">
        </div>

        <style>
        .main .block-container {{
            max-width: 100% !important;
            padding-top: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            padding-bottom: 1rem !important;
        }}

        .section-layer {{
            position: relative;
            z-index: 2;
            width: 100%;
        }}

        .wahhaj-landing-space {{
            height: 13vh;
        }}

        .wahhaj-logo-wrapper {{
            width: 100%;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            margin: 0 auto 2.4rem auto;
        }}

        .wahhaj-logo-img {{
            display: block !important;
            width: min({width}px, 82vw) !important;
            height: auto !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }}

        div.stButton > button {{
            min-height: 58px !important;
            font-size: 17px !important;
            font-weight: 800 !important;
            border-radius: 13px !important;
            padding: 0.85rem 1.4rem !important;
            white-space: nowrap !important;
        }}

        .footer, footer {{
            text-align: center !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


st.markdown('<div class="section-layer">', unsafe_allow_html=True)

st.markdown('<div class="wahhaj-landing-space"></div>', unsafe_allow_html=True)

render_center_logo(width=700)

btn_left, btn_center, btn_right = st.columns([2.45, 0.9, 2.45])

with btn_center:
    if st.button("Login", use_container_width=True):
        st.switch_page("pages/1_Login.py")

st.markdown("</div>", unsafe_allow_html=True)

render_footer()