import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.db_connection import run_query
from utils.styles import COLORS, context_box, chart_instruction_box, page_navigation_footer

st.title("CUSTOMER ANALYTICS OVERVIEW")

# EXTRACT VALUES
context_df = run_query("""
    SELECT 
        COUNT(DISTINCT customer_id) AS total_customers,
        MIN(first_order_date) AS earliest_order,
        MAX(latest_order_date) AS latest_order,
        SUM(CASE WHEN delivered_orders = 0 THEN 1 ELSE 0 END) AS never_delivered,
        SUM(CASE WHEN delivered_orders = 1 THEN 1 ELSE 0 END) AS one_time,
        SUM(CASE WHEN delivered_orders > 1 THEN 1 ELSE 0 END) AS repeat_customers,
        SUM(total_nmv) AS total_revenue,
        SUM(CASE WHEN delivered_orders > 1 THEN total_nmv ELSE 0 END) AS repeat_revenue
    FROM `olist-portfolio-492209.olist_dbt_marts.mart_customers_base`
""")

total_customers = int(context_df['total_customers'].iloc[0])
earliest = context_df['earliest_order'].iloc[0]
latest = context_df['latest_order'].iloc[0]
never_delivered = int(context_df['never_delivered'].iloc[0])
one_time = int(context_df['one_time'].iloc[0])
repeat_customers = int(context_df['repeat_customers'].iloc[0])

successfully_delivered = one_time + repeat_customers
delivery_rate = successfully_delivered / total_customers * 100
retention_rate = repeat_customers / successfully_delivered * 100 if successfully_delivered > 0 else 0

# SECTION 1: CONTEXT BOX
st.markdown(context_box(
    f"""<strong>Dataset:</strong> {earliest} to {latest} — 
    <strong>{total_customers:,}</strong> unique customers acquired on Olist marketplace.
    <br><br>
    The data reveals a critical funnel problem: of all customers acquired, 
    only <strong>{delivery_rate:.1f}%</strong> successfully received their first order, 
    and of those, only <strong>{retention_rate:.1f}%</strong> ever returned for a second purchase.
    Each stage below represents a different type of business problem requiring different interventions.""",
    variant="info"
), unsafe_allow_html=True)

# SECTION 2: SEGMENT CRITERIA
st.subheader("Customer Lifecycle Distribution")

st.markdown("""
<div style="background-color:#FFFFFF; padding:16px 20px; border-radius:8px; 
            border:1px solid #E5E7EB; margin-bottom:20px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);">
    <p style="margin:0 0 12px 0; color:#111827; font-size:0.95rem; font-weight:700;">
        Segment Definitions
    </p>
    <div style="display:flex; gap:20px; flex-wrap:wrap;">
        <div style="flex:1; min-width:220px;">
            <p style="margin:0 0 6px 0; font-weight:700; font-size:0.85rem; 
                      color:#991B1B; border-bottom:2px solid #DC2626; 
                      padding-bottom:4px; display:inline-block;">
                FAILED ACQUISITION
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>Stuck:</strong> Order never reached terminal status
                (still processing, approved, shipped, etc.)
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>Canceled:</strong> Customer canceled the order
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>Stockout:</strong> Product unavailable after payment
            </p>
        </div>
        <div style="flex:1; min-width:220px;">
            <p style="margin:0 0 6px 0; font-weight:700; font-size:0.85rem; 
                      color:#92400E; border-bottom:2px solid #F59E0B; 
                      padding-bottom:4px; display:inline-block;">
                AT-RISK
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>One-time at risk:</strong> 1 delivered order, &gt;60 days 
                since purchase with no return
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>Repeat at risk:</strong> 2+ orders, overdue by 1.2–2x 
                their avg purchase interval
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>Repeat lapsed:</strong> 2+ orders, overdue by &gt;2x 
                their avg purchase interval
            </p>
        </div>
        <div style="flex:1; min-width:220px;">
            <p style="margin:0 0 6px 0; font-weight:700; font-size:0.85rem; 
                      color:#065F46; border-bottom:2px solid #059669; 
                      padding-bottom:4px; display:inline-block;">
                ACTIVE & GROWTH
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>One-time new:</strong> 1 delivered order, &le;60 days 
                since purchase (still within return window)
            </p>
            <p style="margin:2px 0; font-size:0.8rem; color:#475569; line-height:1.5;">
                <strong>Repeat active:</strong> 2+ orders, purchasing within 
                1.2x their avg interval
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# SECTION 3: LIFECYCLE DISTRIBUTION (Sunburst + Segment Cards)

st.markdown(chart_instruction_box(
    "Click any segment to zoom into that customer group. "
    "Click the <strong>center circle</strong> to zoom back out."
), unsafe_allow_html=True)

# SECTION 3  - EXTRACT DATA
hierarchy_df = run_query("""
    WITH lifecycle_grouped AS (
        SELECT 
            customer_id,
            lifecycle_stage,
            CASE 
                WHEN lifecycle_stage LIKE 'never_delivered%' 
                    THEN 'Failed Acquisition'
                WHEN lifecycle_stage IN ('one_time_at_risk', 'repeat_at_risk', 'repeat_lapsed') 
                    THEN 'At-Risk Customers'
                WHEN lifecycle_stage IN ('one_time_new', 'repeat_active') 
                    THEN 'Active & Growth'
            END AS action_category
        FROM `olist-portfolio-492209.olist_dbt_marts.mart_customer_lifecycle`
    )
    SELECT 
        action_category,
        lifecycle_stage,
        COUNT(*) AS customer_count
    FROM lifecycle_grouped
    GROUP BY action_category, lifecycle_stage
    ORDER BY action_category, customer_count DESC
""")

STAGE_LABEL = {
        # Failed Acquisition children
    'never_delivered_stuck': 'Stuck Orders',
    'never_delivered_canceled': 'Canceled',
    'never_delivered_stockout': 'Stockout',
    # At-Risk children
    'one_time_at_risk': 'One-Time at Risk',
    'repeat_at_risk': 'Repeat at Risk',
    'repeat_lapsed': 'Repeat Lapsed',
    # Active children
    'one_time_new': 'One-Time New',
    'repeat_active': 'Repeat Active'
}

# Build sunburst dataframe
total_chart = hierarchy_df['customer_count'].sum()

root_data = pd.DataFrame({
    'labels': ['All Customers'],
    'parents': [''],
    'values': [total_chart]
})

category_totals = hierarchy_df.groupby('action_category')['customer_count'].sum().reset_index()
category_data = pd.DataFrame({
    'labels': category_totals['action_category'],
    'parents': ['All Customers'] * len(category_totals),
    'values': category_totals['customer_count']
})

stage_data = pd.DataFrame({
    'labels': hierarchy_df['lifecycle_stage'].map(STAGE_LABEL).fillna(hierarchy_df['lifecycle_stage']),
    'parents': hierarchy_df['action_category'],
    'values': hierarchy_df['customer_count']
})

sunburst_df = pd.concat([root_data, category_data, stage_data], ignore_index=True)

# SECTION 3 - VISUALIZE
# SECTION 3 - VISUALIZE - LAYOUT
color_map = {
    'All Customers': COLORS["neutral"],
    
    # Level 1: Action categories
    'Failed Acquisition':'#DC2626',
    'At-Risk Customers':'#F59E0B',
    'Active & Growth':'#059669',
    
    # Level 2: Failed Acquisition sub-segments
    'Stuck Orders':'#B91C1C',
    'Canceled':'#EF4444',
    'Stockout':'#F87171',
    
    # Level 2: At-Risk sub-segments
    'One-Time at Risk':'#D97706',
    'Repeat at Risk':'#FBBF24',
    'Repeat Lapsed':'#FDE68A',
    
    # Level 2: Active sub-segments
    'One-Time New':'#10B981',
    'Repeat Active':'#064E3B',
}

col_chart, col_analytics = st.columns([1.7, 1])

# SECTION 3 - VISUALIZE - SUNBURST
with col_chart:
    fig = px.sunburst(
        sunburst_df,
        names='labels',
        parents='parents',
        values='values',
        branchvalues='total',
        color='labels',
        color_discrete_map=color_map
    )

    fig.update_traces(
        textinfo='label+percent parent',
        hovertemplate='<b>%{label}</b><br>Customers: %{value:,}',
        marker=dict(line=dict(color='white', width=2))
    )

    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=20, b=0),
        font=dict(family="Inter, sans-serif", size=12)
    )

    st.plotly_chart(fig, use_container_width=True)

# SECTION 3 - VISUALIZE - INVESTIGATION CARDS
with col_analytics:
    st.markdown("### Investigation Paths")

    # Card 1: Failed Acquisition
    failed_stats = run_query("""
        SELECT 
            COUNT(DISTINCT customer_id) AS num_customers,
            ROUND(AVG(avg_review_score), 2) AS avg_review
        FROM `olist-portfolio-492209.olist_dbt_marts.mart_customers_base`
        WHERE delivered_orders = 0
    """)

    f_num = int(failed_stats['num_customers'].iloc[0])
    f_review = failed_stats['avg_review'].iloc[0]
    f_pct = (f_num / total_customers) * 100
    # NaN handling: these customers have delivered_orders = 0, so total_nmv is NULL
    # Showing "No delivered orders" instead of "R$ nan" communicates WHY the data is missing
    f_review_str = f"{f_review:.2f} / 5.0" if pd.notna(f_review) else "N/A"

    st.markdown(f"""
    <div style="background-color:{COLORS['failure_bg']}; padding:14px 16px; border-radius:8px; 
                border-left:4px solid {COLORS['seg_failed']}; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:baseline;">
            <strong style="color:{COLORS['failure_text']}; font-size:0.95rem;">Failed Acquisition</strong>
            <span style="color:{COLORS['failure_text']}; font-size:0.78rem; font-style:italic;">→ Failed Acquisition page</span>
        </div>
        <div style="display:flex; gap:16px; margin:8px 0; flex-wrap:wrap;">
            <span style="color:{COLORS['failure_text']}; font-size:0.85rem;">
                <strong>{f_num:,}</strong> customers ({f_pct:.1f}%)
            </span>
            <span style="color:{COLORS['failure_text']}; font-size:0.85rem;">
                Avg NMV: <strong>No delivered orders</strong>
            </span>
            <span style="color:{COLORS['failure_text']}; font-size:0.85rem;">
                Review: <strong>{f_review_str}</strong>
            </span>
        </div>
        <p style="margin:0; color:{COLORS['failure_text']}; font-size:0.82rem; line-height:1.5;">
            Customers who paid but never received their order.
            The next page traces <strong>accountability</strong> to specific teams:
            platform, seller, or logistics.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Card 2: At-Risk Customers
    atrisk_stats = run_query("""
        SELECT 
            COUNT(DISTINCT mcb.customer_id) AS num_customers,
            ROUND(AVG(mcb.total_nmv), 2) AS avg_nmv,
            ROUND(AVG(CASE WHEN mcb.avg_review_score IS NOT NULL 
                       THEN mcb.avg_review_score END), 2) AS avg_review
        FROM `olist-portfolio-492209.olist_dbt_marts.mart_customers_base` mcb
        JOIN `olist-portfolio-492209.olist_dbt_marts.mart_customer_lifecycle` mcl
            ON mcb.customer_id = mcl.customer_id
        WHERE mcl.lifecycle_stage IN ('one_time_at_risk', 'repeat_at_risk', 'repeat_lapsed')
    """)

    ar_num = int(atrisk_stats['num_customers'].iloc[0])
    ar_nmv = atrisk_stats['avg_nmv'].iloc[0] or 0
    ar_review = atrisk_stats['avg_review'].iloc[0]
    ar_pct = (ar_num / total_customers) * 100
    ar_review_str = f"{ar_review:.2f} / 5.0" if pd.notna(ar_review) else "N/A"

    st.markdown(f"""
    <div style="background-color:{COLORS['warning_bg']}; padding:14px 16px; border-radius:8px; 
                border-left:4px solid {COLORS['warning']}; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:baseline;">
            <strong style="color:{COLORS['warning_text']}; font-size:0.95rem;">At-Risk Customers</strong>
            <span style="color:{COLORS['warning_text']}; font-size:0.78rem; font-style:italic;">→ At-Risk Customers page</span>
        </div>
        <div style="display:flex; gap:16px; margin:8px 0; flex-wrap:wrap;">
            <span style="color:{COLORS['warning_text']}; font-size:0.85rem;">
                <strong>{ar_num:,}</strong> customers ({ar_pct:.1f}%)
            </span>
            <span style="color:{COLORS['warning_text']}; font-size:0.85rem;">
                Avg NMV: <strong>R$ {ar_nmv:,.2f}</strong>
            </span>
            <span style="color:{COLORS['warning_text']}; font-size:0.85rem;">
                Review: <strong>{ar_review_str}</strong>
            </span>
        </div>
        <p style="margin:0; color:{COLORS['warning_text']}; font-size:0.82rem; line-height:1.5;">
            Customers who received orders but show churn signals.
            The At-Risk Customers page separates <strong>fixable problems</strong>
            (delivery failures, low reviews, price sensitivity) from <strong>silent churn</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Card 3: Active & Growth
    active_stats = run_query("""
        SELECT 
            COUNT(DISTINCT mcb.customer_id) AS num_customers,
            ROUND(AVG(mcb.total_nmv), 2) AS avg_nmv,
            ROUND(AVG(CASE WHEN mcb.avg_review_score IS NOT NULL 
                       THEN mcb.avg_review_score END), 2) AS avg_review
        FROM `olist-portfolio-492209.olist_dbt_marts.mart_customers_base` mcb
        JOIN `olist-portfolio-492209.olist_dbt_marts.mart_customer_lifecycle` mcl
            ON mcb.customer_id = mcl.customer_id
        WHERE mcl.lifecycle_stage IN ('one_time_new', 'repeat_active')
    """)

    ac_num = int(active_stats['num_customers'].iloc[0])
    ac_nmv = active_stats['avg_nmv'].iloc[0] or 0
    ac_review = active_stats['avg_review'].iloc[0]
    ac_pct = (ac_num / total_customers) * 100
    ac_review_str = f"{ac_review:.2f} / 5.0" if pd.notna(ac_review) else "N/A"

    st.markdown(f"""
    <div style="background-color:{COLORS['success_bg']}; padding:14px 16px; border-radius:8px; 
                border-left:4px solid {COLORS['seg_active']}; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:baseline;">
            <strong style="color:{COLORS['success_text']}; font-size:0.95rem;">Active & Growth</strong>
            <span style="color:{COLORS['success_text']}; font-size:0.78rem; font-style:italic;">→ Active Growth page</span>
        </div>
        <div style="display:flex; gap:16px; margin:8px 0; flex-wrap:wrap;">
            <span style="color:{COLORS['success_text']}; font-size:0.85rem;">
                <strong>{ac_num:,}</strong> customers ({ac_pct:.1f}%)
            </span>
            <span style="color:{COLORS['success_text']}; font-size:0.85rem;">
                Avg NMV: <strong>R$ {ac_nmv:,.2f}</strong>
            </span>
            <span style="color:{COLORS['success_text']}; font-size:0.85rem;">
                Review: <strong>{ac_review_str}</strong>
            </span>
        </div>
        <p style="margin:0; color:{COLORS['success_text']}; font-size:0.82rem; line-height:1.5;">
            Satisfied, currently engaged customers. The growth page identifies
            <strong>basket size expansion</strong>, <strong>category cross-sell</strong>,
            and <strong>retention</strong> opportunities.
        </p>
    </div>
    """, unsafe_allow_html=True)

# SECTION 4: NAVIGATION FOOTER
st.divider()

col_footer_text, col_footer_link = st.columns([3, 1])

with col_footer_text:
    st.markdown(f"""
    <div>
        <p style="margin:0 0 4px 0; font-size:0.85rem; color:#DC2626; text-transform:uppercase; letter-spacing:0.05em; font-weight:700;">Next Step</p>
        <p style="margin:0 0 8px 0; font-size:0.95rem; color:#991B1B; line-height:1.5;">
        {f_num:,} customers paid but never received their orders. Trace each failure to its responsible team.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_footer_link:
    st.page_link("pages/failed_acquisition.py", label="Failed Acquisition Analysis →")
