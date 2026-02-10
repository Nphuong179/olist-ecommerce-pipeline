import streamlit as st

st.set_page_config(
    page_title="OLIST CUSTOMER ANALYTICS",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Style metric cards with blue accent */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-left: 4px solid #2563EB;
    } 
            
    div[data-testid="stMetric"] label {
        color: #6B7280;
        font-size: 0.875rem;
        font-weight: 500;
    }
            
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.875rem;
        font-weight: 700;
        color: #111827;
    }
</style>
""",unsafe_allow_html=True)

# Define pages
overview_page = st.Page("pages/overview.py", title="Overview", default=True)
failed_acquisition_page = st.Page("pages/failed_acquisition.py", title="Failed Acquisition")
issues_page = st.Page("pages/identifiable_issues.py", title="Identifiable Issues")
active_growth_page = st.Page("pages/active_growth.py", title="Active Growth Strategy")

pg = st.navigation({
    "Analytics": [
        overview_page,
        failed_acquisition_page,
        issues_page,
        active_growth_page
    ]
})

pg.run()