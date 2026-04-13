import streamlit as st
from ui_helpers import init_state, apply_global_style, login_user

st.set_page_config(page_title="Login", layout="wide")
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

# زر الهوم فوق
top1, top2, top3 = st.columns([8, 1, 1])
with top3:
    if st.button("⌂", use_container_width=True):
        st.switch_page("streamlit_app.py")

st.markdown('<div class="login-main-wrap">', unsafe_allow_html=True)
left, right = st.columns([1.3, 0.9], gap="large")

with left:
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">Login</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-subtitle">to start your solar site analysis</div>', unsafe_allow_html=True)

    st.markdown('<div class="field-label">Email</div>', unsafe_allow_html=True)
    email = st.text_input("Email", placeholder="username@gmail.com", label_visibility="collapsed")

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    st.markdown('<div class="field-label">Password</div>', unsafe_allow_html=True)
    password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")

    st.markdown('<div style="height:26px"></div>', unsafe_allow_html=True)

    if st.button("Log in", use_container_width=True):
        if login_user(email, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = email
            st.switch_page("pages/3_Upload_Image.py")
        else:
            st.error("Please enter email and password.")

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown("""
    <div class="sun-wrap-fixed">
        <div class="sun-glow"></div>
        <div class="ray r1"></div>
        <div class="ray r2"></div>
        <div class="ray r3"></div>
        <div class="ray r4"></div>
        <div class="ray r5"></div>
        <div class="ray r6"></div>
        <div class="ray r7"></div>
        <div class="ray r8"></div>
        <div class="sun-core"></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)