import duckdb
from pathlib import Path
import streamlit as st
import pandas as pd

@st.cache_resource
def get_connection():
    db_path = Path(__file__).parent.parent.parent/"dev.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    return conn

@st.cache_data(ttl=3600)
def run_query(query):
    conn = get_connection()
    return conn.execute(query).df()