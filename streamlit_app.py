import streamlit as st
from ui_helpers import init_state, apply_global_style

st.set_page_config(page_title="WAHHAJ", layout="wide")
init_state()
apply_global_style()

st.markdown("""
<div class="page-bg">
  <div class="blob tl1"></div>
  <div class="blob tl2"></div>
  <div class="blob tl3"></div>
  <div class="blob br1"></div>
  <div class="blob br2"></div>
  <div class="blob br3"></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br><br><br>", unsafe_allow_html=True)
st.image("assets/wahhaj_logo.png", width=700)

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Login", use_container_width=False):
    st.switch_page("pages/1_Login.py")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center;font-size:24px;color:#5A5959;'>Danah Alhamdi - Walah Alshwair - Ruba Aletri - Jumanah Alharbi</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div style='text-align:center;font-size:24px;color:#5A5959;margin-top:24px;'>© 2025 By PNU's CS Students</div>",
    unsafe_allow_html=True
)