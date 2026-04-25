import os
import streamlit as st
from supabase import create_client


def get_supabase():
    url = st.secrets.get("sb_publishable_wNorRItkoRBXiWvOlTlt3Q_WgkRs9mS") or os.getenv("sb_publishable_wNorRItkoRBXiWvOlTlt3Q_WgkRs9mS")
    key = st.secrets.get("sb_publishable_wNorRItkoRBXiWvOlTlt3Q_WgkRs9mS") or os.getenv("sb_publishable_wNorRItkoRBXiWvOlTlt3Q_WgkRs9mS")

    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY")

    return create_client(url, key)


def get_analysis_history_by_email(user_email: str):
    sb = get_supabase()
    res = (
        sb.table("analysis_history")
        .select("*")
        .eq("user_email", user_email)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def get_analysis_by_run_id(run_id: str):
    sb = get_supabase()
    res = (
        sb.table("analysis_history")
        .select("*")
        .eq("run_id", run_id)
        .limit(1)
        .execute()
    )
    data = res.data or []
    return data[0] if data else None