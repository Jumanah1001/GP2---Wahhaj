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

        [data-testid="stSidebar"] { display: none; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { right: 14px; top: 10px; }

        .stApp {
            background: #f7f7f5;
        }

        .main .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 1.2rem;
        }

        .page-bg {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
            background: #f7f7f5;
        }

        .blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(120px);
            opacity: 0.82;
        }

        .blob.tl1 { width: 420px; height: 420px; left: -120px; top: -80px; background: #91D895; }
        .blob.tl2 { width: 430px; height: 430px; left: 120px; top: -170px; background: #4FC3F7; }
        .blob.tl3 { width: 420px; height: 420px; left: -160px; top: 120px; background: #F9B233; }

        .blob.br1 { width: 430px; height: 430px; right: -120px; bottom: -40px; background: #FE753F; }
        .blob.br2 { width: 430px; height: 430px; right: -220px; bottom: 120px; background: #0066FF; }
        .blob.br3 { width: 410px; height: 410px; right: 80px; bottom: -130px; background: #F9B233; opacity: 0.46; }

        .section-layer {
            position: relative;
            z-index: 2;
        }

        .home-title-space {
            height: 30px;
        }

        .credits {
            text-align: center;
            font-family: 'Capriola', sans-serif;
            color: #5A5959;
            font-size: clamp(20px, 2vw, 32px);
            line-height: 1.8;
            margin-top: 70px;
        }

        .login-title {
            font-family: 'Capriola', sans-serif;
            font-size: clamp(58px, 5vw, 72px);
            color: #5A5959;
            line-height: 1;
            margin-bottom: 10px;
        }

        .login-subtitle {
            font-family: 'Capriola', sans-serif;
            font-size: 15px;
            color: #5E5B5B;
            margin-bottom: 34px;
        }

        .field-label {
            font-family: 'Capriola', sans-serif;
            font-size: clamp(22px, 1.9vw, 26px);
            color: #333333;
            margin-bottom: 8px;
            margin-top: 8px;
        }

        .login-card-box {
            background: rgba(255,255,255,0.68);
            border-radius: 24px;
            backdrop-filter: blur(10px);
            padding: 54px 50px;
            box-shadow: 0 10px 34px rgba(0,0,0,0.04);
            min-height: 560px;
        }

        div[data-testid="stTextInput"] input {
            background: #F0EEEE !important;
            color: #6f6f6f !important;
            border: none !important;
            border-radius: 4px !important;
            min-height: 42px !important;
            font-family: 'Capriola', sans-serif !important;
            font-size: 13px !important;
            padding-left: 14px !important;
            box-shadow: none !important;
        }

        div[data-testid="stTextInput"] label {
            display: none !important;
        }

        div.stButton > button {
            background: #0070FF;
            color: white;
            border: none;
            border-radius: 4px;
            min-height: 52px;
            font-family: 'Capriola', sans-serif;
            font-size: 18px;
            box-shadow: 5px 6px 4px rgba(0,0,0,0.18);
        }

        div.stButton > button:hover {
            background: #005fe0;
            color: white;
        }

        .sun-wrap-fixed {
            position: relative;
            width: 390px;
            height: 390px;
            margin: 90px auto 0 auto;
        }

        .sun-glow {
            position: absolute;
            width: 240px;
            height: 240px;
            left: 75px;
            top: 75px;
            background: #FFA800;
            filter: blur(72px);
            border-radius: 50%;
            opacity: 0.58;
        }

        .sun-core {
            position: absolute;
            width: 250px;
            height: 250px;
            left: 70px;
            top: 70px;
            border-radius: 50%;
            background: linear-gradient(38.87deg, #EE9D3E 37.22%, rgba(236, 161, 74, 0) 78.02%), #FFE600;
            box-shadow: inset 0 1px 16px rgba(255,255,255,0.77);
        }

        .ray {
            position: absolute;
            width: 22px;
            height: 78px;
            border-radius: 16px;
            background: linear-gradient(180deg, #FFE66A 0%, #F0B64A 100%);
            box-shadow: inset 0 2px 8px rgba(255,255,255,0.35);
        }

        .ray.r1 { left: 184px; top: 0px; }
        .ray.r2 { right: 42px; top: 48px; transform: rotate(45deg); }
        .ray.r3 { right: 0px; top: 156px; transform: rotate(90deg); }
        .ray.r4 { right: 42px; bottom: 48px; transform: rotate(135deg); }
        .ray.r5 { left: 184px; bottom: 0px; }
        .ray.r6 { left: 42px; bottom: 48px; transform: rotate(-135deg); }
        .ray.r7 { left: 0px; top: 156px; transform: rotate(90deg); }
        .ray.r8 { left: 42px; top: 48px; transform: rotate(-45deg); }

        .top-home-btn {
            width: 84px;
            margin-left: auto;
        }

        .top-home-btn div.stButton > button {
            min-height: 44px;
            font-size: 20px;
            border-radius: 12px;
            box-shadow: none;
        }

        @media (max-width: 900px) {
            .sun-wrap-fixed { display: none; }
            .login-card-box { min-height: auto; padding: 40px 28px; }
            .credits { margin-top: 50px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_bg():
    st.markdown(
        """
        <div class="page-bg">
            <div class="blob tl1"></div>
            <div class="blob tl2"></div>
            <div class="blob tl3"></div>
            <div class="blob br1"></div>
            <div class="blob br2"></div>
            <div class="blob br3"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_logo(image_path="assets/wahhaj_logo.png", width=520):
    path = Path(image_path)
    if path.exists():
        st.image(str(path), width=width)


def login_user(username: str, password: str) -> bool:
    return bool(username and password)