import streamlit as st
from ui_helpers import init_state, apply_global_style, render_bg, show_logo, render_footer

st.set_page_config(page_title="WAHHAJ", layout="wide")
init_state()
apply_global_style()
render_bg()

st.markdown('<div class="section-layer">', unsafe_allow_html=True)

st.markdown("<div class='home-title-space'></div>", unsafe_allow_html=True)

logo_left, logo_center, logo_right = st.columns([1, 3.2, 1])
with logo_center:
    show_logo(width=760)

st.write("")
btn_left, btn_center, btn_right = st.columns([2.2, 1, 2.2])
with btn_center:
    if st.button("Login", use_container_width=True):
        st.switch_page("pages/1_Login.py")



st.markdown("</div>", unsafe_allow_html=True)
render_footer()