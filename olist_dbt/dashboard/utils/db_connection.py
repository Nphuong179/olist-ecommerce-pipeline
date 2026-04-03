from google.cloud import bigquery
from google.oauth2 import service_account
import streamlit as st

@st.cache_resource
def get_connection():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    return bigquery.Client(
        credentials=credentials,
        project='olist-portfolio-492209'
    )

@st.cache_data(ttl=3600)
def run_query(query):
    conn = get_connection()
    return conn.query_and_wait(query).to_dataframe()