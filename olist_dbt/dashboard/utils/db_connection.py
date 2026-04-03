from google.cloud import bigquery
import streamlit as st
import pandas as pd

@st.cache_resource
def get_connection():
    return bigquery.Client(project='olist-portfolio-491906')

@st.cache_data(ttl=3600)
def run_query(query):
    conn = get_connection()
    return conn.query_and_wait(query).to_dataframe()