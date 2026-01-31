import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb

# Page configuration
st.set_page_config(
    page_title='Olist Analytics',
    layout='wide'
)

# TITLE
st.title("Olist E-commerce Dashboard")
st.markdown("---")

# Connect to DuckDB
@st.cache_resource
def get_connection():
    db_path = 'dev.duckdb'
    return duckdb.connect(db_path, read_only=True)

# Test connection
try:
    conn = get_connection()
except Exception as e:
    st.error(f"Unable to load data. Please check database connection")
    st.stop()

# LOAD DATA - mart_customer_base
@st.cache_data
def load_customers_engagement_summary():
    query = """
    SELECT
        COUNT(DISTINCT mcb.customer_id) AS total_customers,
        SUM(CASE WHEN mcb.delivered_orders = 1 THEN 1 ELSE 0 END) AS one_time_buyers,
        SUM(CASE WHEN mcb.delivered_orders > 1 THEN 1 ELSE 0 END) AS repeat_buyers,

        -- Lifetime Value
        AVG(CASE WHEN mcb.delivered_orders = 1 THEN mcb.total_nmv END) AS one_time_buyer_avg_ltv,
        AVG(CASE WHEN mcb.delivered_orders > 1 THEN mcb.total_nmv END) AS repeat_buyer_avg_ltv,
        
        -- Overdue
        SUM(CASE WHEN mcl.days_overdue >= 60 THEN 1 ELSE 0 END) AS at_risk_customers
    FROM main_marts.mart_customers_base mcb
    JOIN main_marts.mart_customer_lifecycle mcl
        ON mcb.customer_id = mcl.customer_id
    """
    conn = get_connection()
    df = conn.execute(query).df()
    return df.iloc[0]

# HEADLINE
customer_engagement_summary = load_customers_engagement_summary()
churn_pct = (customer_engagement_summary['one_time_buyers'] / customer_engagement_summary['total_customers']) * 100
ltv_multiplier = customer_engagement_summary['repeat_buyer_avg_ltv'] / customer_engagement_summary['one_time_buyer_avg_ltv']
at_risk_customer_pct = (customer_engagement_summary['at_risk_customers'] / customer_engagement_summary['total_customers']) * 100
st.header(f"The Retention Crisis: {churn_pct:.0f}% of Customers Never Return")
st.markdown("---")

# KEY METRICS
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="One-Time Buyer Percent",
        value=f"{churn_pct:.1f}%",
        delta=None,
        help="% of customers who made only one purchase"
    )

with col2:
    st.metric(
        label="Repeat Buyer Value",
        value=f"{ltv_multiplier:.2f}x",
        delta=f"+R$ {customer_engagement_summary['repeat_buyer_avg_ltv'] - customer_engagement_summary['one_time_buyer_avg_ltv']:.0f}",
        help="How much more repeat buyers spend compared to one-time buyers"
    )

with col3:
    st.metric(
        label="At-Risk Customer Percent",
        value=f"{at_risk_customer_pct:.1f}%",
        delta=None,
        help="Percentage of customers who are 60+ days past their expected return date"
    )
st.info(f"""
    ### Business Challenge
    
    Out of **{customer_engagement_summary['total_customers']:,.0f} customers**, 
    **{customer_engagement_summary['one_time_buyers']:,.0f} ({churn_pct:.1f}%)** made only one purchase and never returned.

    Meanwhile, repeat buyers generate **{ltv_multiplier:.2f}x more lifetime value**
    (R\\$ {customer_engagement_summary['repeat_buyer_avg_ltv']:.0f} vs. R\\$ {customer_engagement_summary['one_time_buyer_avg_ltv']:.0f})
    
    Additionally, **{customer_engagement_summary['at_risk_customers']:,.0f} customers ({at_risk_customer_pct:.1f}%)** are 60+ days overdue for their expected return, indicating they may have churned.

    **The analysis identifies why customers do not return and how to recover them.** 
""")

