import streamlit as st
from pathlib import Path


def init_state():
    defaults = {
        "logged_in": False,
        "username": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def apply_global_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Capriola&family=Inter:wght@400;500;600;700&display=swap');

        [data-testid="stSidebar"] {display: none;}
        [data-testid="stHeader"] {background: transparent;}

        .stApp {
            background: #f7f7f5;
        }

        .main .block-container {
            max-width: 1280px;
            padding-top: 20px;
            padding-bottom: 20px;
        }

        .page-bg {
            position: fixed;
            inset: 0;
            overflow: hidden;
            z-index: 0;
            pointer-events: none;
            background: #f7f7f5;
        }

        .blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(120px);
            opacity: 0.85;
        }

        .blob.tl1 { width: 420px; height: 420px; left: -120px; top: -90px; background: #91D895; }
        .blob.tl2 { width: 440px; height: 440px; left: 120px; top: -170px; background: #4FC3F7; }
        .blob.tl3 { width: 430px; height: 430px; left: -180px; top: 120px; background: #F9B233; }

        .blob.br1 { width: 440px; height: 440px; right: -120px; bottom: -40px; background: #FE753F; }
        .blob.br2 { width: 440px; height: 440px; right: -220px; bottom: 110px; background: #0066FF; }
        .blob.br3 { width: 420px; height: 420px; right: 90px; bottom: -130px; background: #F9B233; opacity: 0.45; }

        .login-main-wrap {
            position: relative;
            z-index: 2;
            margin-top: 40px;
        }

        .login-card {
            background: rgba(255,255,255,0.68);
            border-radius: 24px;
            backdrop-filter: blur(10px);
            padding: 56px 54px;
            box-shadow: 0 10px 34px rgba(0,0,0,0.04);
            min-height: 560px;
        }

        .login-title {
            font-family: 'Capriola', sans-serif;
            font-size: 64px;
            color: #5A5959;
            line-height: 1;
            margin-bottom: 10px;
        }

        .login-subtitle {
            font-family: 'Capriola', sans-serif;
            font-size: 15px;
            color: #5E5B5B;
            margin-bottom: 36px;
        }

        .field-label {
            font-family: 'Capriola', sans-serif;
            font-size: 24px;
            color: #333333;
            margin-bottom: 8px;
        }

        div[data-testid="stTextInput"] input {
            background: #F0EEEE !important;
            color: #707070 !important;
            border: none !important;
            border-radius: 4px !important;
            min-height: 42px !important;
            font-family: 'Capriola', sans-serif !important;
            font-size: 13px !important;
            padding-left: 14px !important;
        }

        div.stButton > button {
            background: #0070FF;
            color: white;
            border: none;
            border-radius: 4px;
            min-height: 50px;
            font-family: 'Capriola', sans-serif;
            font-size: 20px;
            box-shadow: 5px 6px 4px rgba(0,0,0,0.18);
        }

        div.stButton > button:hover {
            background: #005fe0;
            color: white;
        }

        .sun-wrap-fixed {
            position: relative;
            width: 420px;
            height: 420px;
            margin: 80px auto 0 auto;
        }

        .sun-glow {
            position: absolute;
            width: 250px;
            height: 250px;
            left: 85px;
            top: 85px;
            background: #FFA800;
            filter: blur(75px);
            border-radius: 50%;
            opacity: 0.55;
        }

        .sun-core {
            position: absolute;
            width: 260px;
            height: 260px;
            left: 80px;
            top: 80px;
            border-radius: 50%;
            background: linear-gradient(38.87deg, #EE9D3E 37.22%, rgba(236, 161, 74, 0) 78.02%), #FFE600;
            box-shadow: inset 0 1px 16px rgba(255,255,255,0.77);
        }

        .ray {
            position: absolute;
            width: 24px;
            height: 82px;
            border-radius: 18px;
            background: linear-gradient(180deg, #FFE66A 0%, #F0B64A 100%);
            box-shadow: inset 0 2px 8px rgba(255,255,255,0.35);
        }

        .ray.r1 { left: 198px; top: 0px; }
        .ray.r2 { right: 48px; top: 52px; transform: rotate(45deg); }
        .ray.r3 { right: 0px; top: 170px; transform: rotate(90deg); }
        .ray.r4 { right: 48px; bottom: 52px; transform: rotate(135deg); }
        .ray.r5 { left: 198px; bottom: 0px; }
        .ray.r6 { left: 48px; bottom: 52px; transform: rotate(-135deg); }
        .ray.r7 { left: 0px; top: 170px; transform: rotate(90deg); }
        .ray.r8 { left: 48px; top: 52px; transform: rotate(-45deg); }

        @media (max-width: 900px) {
            .sun-wrap-fixed { display: none; }
            .login-card { min-height: auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_bg_start():
    st.markdown(
        """
        <div class="app-shell">
            <div class="blob tl1"></div>
            <div class="blob tl2"></div>
            <div class="blob tl3"></div>
            <div class="blob br1"></div>
            <div class="blob br2"></div>
            <div class="blob br3"></div>
            <div class="stage">
        """,
        unsafe_allow_html=True,
    )


def page_bg_end():
    st.markdown("</div></div>", unsafe_allow_html=True)


def show_logo(image_path="assets/wahhaj_logo.png", width=520):
    path = Path(image_path)
    if path.exists():
        st.image(str(path), width=width)


def login_user(username: str, password: str) -> bool:
    return bool(username and password)