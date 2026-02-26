import streamlit as st
from utils.styles import GLOBAL_CSS

st.set_page_config(
    page_title="OLIST CUSTOMER ANALYTICS",
    layout="wide"
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Define pages
overview_page = st.Page("pages/overview.py", title='Overview', default=True)
failed_acquisition_page = st.Page("pages/failed_acquisition.py", title='Failed Acquisition')
at_risk_page = st.Page("pages/at_risk.py", title='At-Risk Customers')
proactive_retention_page = st.Page("pages/proactive_retention.py", title='Proactive Retention')
data_quality_page = st.Page("pages/data_quality.py", title='Data Quality Monitor')

pg = st.navigation({
    'Analytics': [
        overview_page,
        failed_acquisition_page,
        at_risk_page,
        proactive_retention_page
    ],
    'Data Quality': [data_quality_page]
})

pg.run()