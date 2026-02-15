import streamlit as st
import sys
from pathlib import Path
import plotly.express as px
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent/"utils"))
from db_connection import run_query

st.title("CUSTOMER ANALYTICS OVERVIEW")

# CONTEXTUAL INFORMATION BOX
context_query = """
SELECT 
    COUNT(DISTINCT customer_id) as total_customers,
    MIN(first_order_date) as earliest_order,
    MAX(latest_order_date) as latest_order,
    SUM(CASE WHEN delivered_orders = 0 THEN 1 ELSE 0 END) as never_delivered,
    SUM(CASE WHEN delivered_orders = 1 THEN 1 ELSE 0 END) as one_time,
    SUM(CASE WHEN delivered_orders > 1 THEN 1 ELSE 0 END) as repeat_customers
FROM dev.main_marts.mart_customers_base
"""

context_df = run_query(context_query)

total_customers = int(context_df['total_customers'].iloc[0])
earliest = context_df['earliest_order'].iloc[0]
latest = context_df['latest_order'].iloc[0]
never_delivered = int(context_df['never_delivered'].iloc[0])
one_time = int(context_df['one_time'].iloc[0])
repeat_customers = int(context_df['repeat_customers'].iloc[0])

never_pct = (never_delivered / total_customers) * 100
one_time_pct = (one_time / total_customers) * 100
repeat_pct = (repeat_customers / total_customers) * 100

st.markdown(f"""
<div style="background-color:#EFF6FF; padding:16px; border-radius:8px; margin-bottom:24px; border-left:4px solid #2563EB;">
    <p style="margin:0; color:#1E40AF; font-size:0.95rem; line-height:1.7;">
        <strong>Dataset Overview:</strong> Between <strong>{earliest}</strong> and <strong>{latest}</strong>, 
        Olist acquired <strong>{total_customers:,}</strong> customers. Of these:
        <br><br>
        • <strong>{never_delivered:,} customers ({never_pct:.1f}%)</strong> never received their orders due to 
        operational failures (stuck processing, customer cancellations, or inventory stockouts)
        <br>
        • <strong>{one_time:,} customers ({one_time_pct:.1f}%)</strong> successfully received one order but 
        never returned, indicating a severe retention challenge
        <br>
        • <strong>{repeat_customers:,} customers ({repeat_pct:.1f}%)</strong> made repeat purchases, 
        demonstrating sustained engagement
        <br><br>
        The data reveals a critical business problem: <strong>97% of customers fail to progress beyond their first purchase</strong>, 
        representing massive revenue leakage and indicating fundamental issues with customer retention strategy.
    </p>
</div>
""", unsafe_allow_html=True)

# CUSTOMER LIFECYCLE HIERARCHY DATA
st.subheader("Customer Lifecycle Distribution")

hierarchy_query = """
WITH lifecycle_calculated AS (
    SELECT 
        customer_id,
        lifecycle_stage,
        CASE 
            WHEN lifecycle_stage LIKE 'never_delivered%' THEN 'Failed Acquisition'
            WHEN lifecycle_stage LIKE 'one_time%' THEN 'One-Time Buyers'
            WHEN lifecycle_stage LIKE 'repeat%' THEN 'Repeat Customers'
        END as primary_category
    FROM dev.main_marts.mart_customer_lifecycle
)
SELECT 
    primary_category,
    lifecycle_stage,
    COUNT(*) as customer_count
FROM lifecycle_calculated
GROUP BY primary_category, lifecycle_stage
ORDER BY primary_category, customer_count DESC
"""

hierarchy_df = run_query(hierarchy_query)

# Prepare sunburst data
total_customers_chart = hierarchy_df['customer_count'].sum()

root_data = pd.DataFrame({
    'labels': ['All Customers'],
    'parents': [''],
    'values': [total_customers_chart]
})

primary_categories = hierarchy_df.groupby('primary_category')['customer_count'].sum().reset_index()
primary_data = pd.DataFrame({
    'labels': primary_categories['primary_category'],
    'parents': ['All Customers'] * len(primary_categories),
    'values': primary_categories['customer_count']
})

lifecycle_data = pd.DataFrame({
    'labels': hierarchy_df['lifecycle_stage'],
    'parents': hierarchy_df['primary_category'],
    'values': hierarchy_df['customer_count']
})

sunburst_df = pd.concat([root_data, primary_data, lifecycle_data], ignore_index=True)

# TWO COLUMNS: Chart + Segment Deep Dive
col_chart, col_analytics = st.columns([1.7, 1])

with col_chart:
    # Create sunburst chart
    fig = px.sunburst(
        sunburst_df,
        names='labels',
        parents='parents',
        values='values',
        branchvalues='total',
        color='labels',
        color_discrete_map={
            'All Customers': '#64748B',
            'Failed Acquisition': '#DC2626',
            'One-Time Buyers': '#8B5CF6',
            'Repeat Customers': '#10B981',
            'never_delivered_stuck': '#B91C1C',
            'never_delivered_canceled': '#EF4444',
            'never_delivered_stockout': '#F87171',
            'one_time_at_risk': '#7C3AED',
            'one_time_new': '#3B82F6',
            'repeat_active': '#059669',
            'repeat_at_risk': '#F59E0B',
            'repeat_lapsed': '#DC2626'
        }
    )

    fig.update_traces(
        textinfo='label+percent parent',
        hovertemplate='<b>%{label}</b><br>Customers: %{value:,}<br>% of Parent: %{percentParent}<extra></extra>',
        marker=dict(line=dict(color='white', width=2))
    )

    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=20, b=0),
        font=dict(family="Inter, sans-serif", size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

with col_analytics:
    st.markdown("### Segment Deep Dive")
    
    # Category selector
    selected_category = st.selectbox(
        "Select primary segment:",
        options=['Failed Acquisition', 'One-Time Buyers', 'Repeat Customers'],
        index=1  # Default to One-Time Buyers (biggest problem)
    )
    
    # Query segment-specific metrics
    category_filter = {
        'Failed Acquisition': 'delivered_orders = 0',
        'One-Time Buyers': 'delivered_orders = 1',
        'Repeat Customers': 'delivered_orders > 1'
    }
    
    segment_query = f"""
    SELECT 
        COUNT(DISTINCT customer_id) as num_customers,
        SUM(total_orders) as num_orders,
        ROUND(AVG(total_nmv), 2) as avg_nmv,
        ROUND(AVG(CASE WHEN avg_review_score IS NOT NULL THEN avg_review_score END), 2) as avg_review_score
    FROM dev.main_marts.mart_customers_base
    WHERE {category_filter[selected_category]}
    """
    
    segment_stats = run_query(segment_query)
    
    # Extract values
    num_customers = int(segment_stats['num_customers'].iloc[0])
    num_orders = int(segment_stats['num_orders'].iloc[0]) if segment_stats['num_orders'].iloc[0] else 0
    avg_nmv = segment_stats['avg_nmv'].iloc[0] if segment_stats['avg_nmv'].iloc[0] else 0
    avg_review = segment_stats['avg_review_score'].iloc[0]
    
    # Display metrics
    st.metric("Number of Customers", f"{num_customers:,}")
    st.metric("Number of Orders", f"{num_orders:,}")
    st.metric("Average NMV", f"R$ {avg_nmv:,.2f}")
    
    if avg_review and avg_review > 0:
        st.metric("Average Review Score", f"{avg_review:.2f} / 5.0")
    else:
        st.metric("Average Review Score", "N/A")
    
    # Segment-specific insights
    st.markdown("---")
    st.markdown("**Segment Characteristics:**")
    
    if selected_category == 'Failed Acquisition':
        st.markdown("""
        <div style="background-color:#FEF2F2; padding:12px; border-radius:6px; font-size:0.85rem; color:#991B1B;">
            Customers who never received their first order. This represents <strong>complete acquisition failure</strong> 
            caused by operational issues (stuck processing, customer cancellations, or inventory stockouts). 
            These customers paid but received nothing, resulting in refunds, negative sentiment, and lost opportunities.
        </div>
        """, unsafe_allow_html=True)
    
    elif selected_category == 'One-Time Buyers':
        pct_of_total = (num_customers / total_customers) * 100
        st.markdown(f"""
        <div style="background-color:#FEF3C7; padding:12px; border-radius:6px; font-size:0.85rem; color:#92400E;">
            The <strong>largest segment</strong> representing {pct_of_total:.1f}% of all customers. 
            These customers successfully received one order but never returned. This is not an operational failure—
            they chose not to come back, indicating issues with product value, pricing, experience, or competition. 
            <strong>This is the primary business problem.</strong>
        </div>
        """, unsafe_allow_html=True)
    
    else:  # Repeat Customers
        pct_of_total = (num_customers / total_customers) * 100
        st.markdown(f"""
        <div style="background-color:#F0FDF4; padding:12px; border-radius:6px; font-size:0.85rem; color:#065F46;">
            The <strong>most valuable segment</strong> but only {pct_of_total:.1f}% of all customers. 
            These customers came back for additional purchases, demonstrating product-market fit and loyalty. 
            They represent proven buyers who should be prioritized for retention, upsell, and VIP treatment.
        </div>
        """, unsafe_allow_html=True)

import plotly.express as px
