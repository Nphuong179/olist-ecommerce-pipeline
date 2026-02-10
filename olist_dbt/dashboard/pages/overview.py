import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent/"utils"))
from db_connection import run_query

st.title("CUSTOMER ANALYTICS OVERVIEW")

query = """
SELECT 
    COUNT(DISTINCT customer_id) as total_customers,
    SUM(CASE WHEN delivered_orders = 0 THEN 1 ELSE 0 END) as never_delivered_customers,
    SUM(CASE WHEN delivered_orders = 1 THEN 1 ELSE 0 END) as one_time_customers,
    SUM(CASE WHEN delivered_orders > 1 THEN 1 ELSE 0 END) as repeat_customers
FROM dev.main_marts.mart_customers_base
"""

df = run_query(query)

# Extract values
total_customers = df['total_customers'].iloc[0]
never_delivered = df['never_delivered_customers'].iloc[0]
one_time = df['one_time_customers'].iloc[0]
repeat = df['repeat_customers'].iloc[0]

never_delivered_pct = (never_delivered / total_customers) * 100
one_time_pct = (one_time / total_customers) * 100
repeat_pct = (repeat / total_customers) * 100

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    label="Total Customers",
    value=f"{total_customers:,}"
)

col2.metric(
    label="Never Delivered Customers", 
    value=f"{int(never_delivered):,}"
)

col3.metric(
    label="One-Time Customers",
    value=f"{int(one_time):,}"
)

col4.metric(
    label="Repeat Customers",
    value=f"{int(repeat):,}"
)

st.markdown(f"""
<div style="background-color:#F0F9FF; padding:16px; border-radius:8px; margin-top:20px; border-left:4px solid #2563EB;">
    <p style="margin:0; color:#1E40AF; font-size:0.95rem;">
        <strong>Customer Composition:</strong> {one_time_pct:.1f}% of customers made only one purchase, 
        {repeat_pct:.1f}% returned for additional orders, while {never_delivered_pct:.1f}% never received any order. This indicates a significant retention challenge.
    </p>
</div>
""", unsafe_allow_html=True)