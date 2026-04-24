"""Supabase PostgreSQL connection helper for WAHHAJ."""

from contextlib import contextmanager
import streamlit as st
import psycopg2


@contextmanager
def get_db():
    """Yield a PostgreSQL cursor, commit on success, rollback on error."""
    conn = psycopg2.connect(st.secrets["supabase"]["db_url"])
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
