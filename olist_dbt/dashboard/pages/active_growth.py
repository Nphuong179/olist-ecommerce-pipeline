"""
Active Growth Strategy Page — Where to invest in currently healthy customers.

PURPOSE:
    The previous pages focused on problems (failed orders, churn risks).
    This page answers a different question: "Among customers who ARE satisfied 
    and active, where's the biggest growth lever?"
    
    Three growth strategies from mart_customer_value_growth:
    1. Increase basket size — mid-value customers who could spend more
    2. Category expansion — single-category shoppers who could cross-buy
    3. Maintain engagement — high-value customers to protect from churn

CHART CHOICES:
    - Horizontal bar (ranked by addressable revenue) → instant priority read
    - Scatter plot (avg NMV vs categories purchased) → visualize the expansion space
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.db_connection import run_query
from utils.styles import COLORS, context_box, analysis_sidepanel

st.title("ACTIVE GROWTH STRATEGY")

# ============================================================
# DATA LOADING
# ============================================================

growth_df = run_query("""
    SELECT
        mcvg.customer_id,
        mcvg.actionable_segment,
        mcvg.lifecycle_stage,
        mcb.avg_nmv_per_order,
        mcb.unique_categories_purchased,
        mcb.delivered_orders,
        mcb.total_nmv,
        mcb.avg_review_score
    FROM dev.main_marts.mart_customer_value_growth mcvg
    JOIN dev.main_marts.mart_customers_base mcb
        ON mcvg.customer_id = mcb.customer_id
    WHERE mcvg.lifecycle_stage IN ('one_time_new', 'repeat_active')
        AND mcvg.actionable_segment IN ('increase_basket_size', 'category_expansion', 'maintain_engagement')
""")

total_active_growth = len(growth_df)

# ============================================================
# SECTION 1: CONTEXT BOX
# ============================================================

st.markdown(context_box(
    f"""These <strong>{total_active_growth:,}</strong> customers are currently active, satisfied, 
    and show no churn signals — they represent the <strong>highest-ROI growth investment</strong>. 
    <br><br>
    Rather than generic "send everyone a coupon" campaigns, each segment below has a specific 
    growth lever backed by their purchasing pattern.""",
    variant="success"
), unsafe_allow_html=True)

# ============================================================
# SECTION 2: GROWTH SEGMENTS — Ranked by addressable revenue
# ============================================================

st.subheader("Growth Opportunity Segments")

segment_summary = growth_df.groupby('actionable_segment').agg(
    customer_count=('customer_id', 'nunique'),
    avg_nmv=('avg_nmv_per_order', 'mean'),
    total_revenue=('total_nmv', 'sum'),
    avg_categories=('unique_categories_purchased', 'mean'),
    avg_review=('avg_review_score', 'mean')
).reset_index()

# Rename for display
segment_labels = {
    'increase_basket_size': 'Increase Basket Size',
    'category_expansion': 'Category Expansion',
    'maintain_engagement': 'Maintain Engagement'
}

segment_colors = {
    'increase_basket_size': '#2563EB',
    'category_expansion': '#7C3AED',
    'maintain_engagement': '#059669'
}

segment_descriptions = {
    'increase_basket_size': (
        'Mid-value active customers (R$100-500 avg order). '
        'Strategy: Bundle recommendations, "frequently bought together" prompts, '
        'free shipping thresholds slightly above their current basket size.'
    ),
    'category_expansion': (
        'Single-category shoppers with proven purchase intent. '
        'Strategy: Cross-category recommendations based on what similar buyers purchased, '
        'discovery-focused email campaigns highlighting complementary categories.'
    ),
    'maintain_engagement': (
        'High-value customers (R$500+ avg order) already engaged. '
        'Strategy: Priority customer service, early access to promotions, '
        'loyalty recognition — protect these relationships above all.'
    )
}

segment_summary['label'] = segment_summary['actionable_segment'].map(segment_labels)
segment_summary = segment_summary.sort_values('total_revenue', ascending=True)

col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure(go.Bar(
        y=segment_summary['label'],
        x=segment_summary['total_revenue'],
        orientation='h',
        marker=dict(
            color=[segment_colors.get(s, '#64748B') for s in segment_summary['actionable_segment']],
            line=dict(color='white', width=2)
        ),
        text=segment_summary.apply(
            lambda r: f"R${r['total_revenue']:,.0f} | {int(r['customer_count']):,} customers", axis=1
        ),
        textposition='inside',
        textfont=dict(color='white', size=13, family='Inter, sans-serif'),
        hovertemplate='<b>%{y}</b><br>Total Revenue: R$%{x:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text="Growth Segments Ranked by Total Addressable Revenue",
            font=dict(size=18, family="Inter, sans-serif", color='#111827'),
            x=0.5, xanchor='center'
        ),
        xaxis=dict(title="Total Revenue (R$)", gridcolor='#F1F5F9'),
        yaxis=dict(title=""),
        height=350,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family="Inter, sans-serif", size=12)
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    largest_seg = segment_summary.iloc[-1]  # Highest revenue (sorted ascending, last = highest)
    
    st.markdown(analysis_sidepanel(
        context=(
            f"<strong>{total_active_growth:,}</strong> active customers with growth potential, "
            f"segmented by their most impactful growth lever based on current purchasing patterns."
        ),
        finding=(
            f"<strong>{segment_labels.get(largest_seg['actionable_segment'], '')}</strong> "
            f"represents the largest revenue opportunity with "
            f"<strong>{int(largest_seg['customer_count']):,}</strong> customers generating "
            f"<strong>R${largest_seg['total_revenue']:,.0f}</strong> in total revenue."
        ),
        action=(
            segment_descriptions.get(largest_seg['actionable_segment'], 'Review segment strategy.')
        ),
        border_color=COLORS["success"]
    ), unsafe_allow_html=True)

# ============================================================
# SECTION 3: SCATTER — Expansion space visualization
# ============================================================

st.subheader("Customer Value vs. Category Diversity")

# This scatter plot visualizes WHERE each customer sits in the
# "spending × diversity" space. It helps identify:
# - Bottom-left cluster: low spend, single category → expansion opportunity
# - Bottom-right: diverse but low spend → basket size opportunity
# - Top-left: high spend, single category → cross-sell opportunity
# - Top-right: high spend, diverse → maintain & protect

scatter_df = growth_df.copy()
scatter_df['segment_label'] = scatter_df['actionable_segment'].map(segment_labels)

fig = px.scatter(
    scatter_df,
    x='unique_categories_purchased',
    y='avg_nmv_per_order',
    color='segment_label',
    color_discrete_map={
        'Increase Basket Size': '#2563EB',
        'Category Expansion': '#7C3AED',
        'Maintain Engagement': '#059669'
    },
    size='delivered_orders',
    size_max=15,
    opacity=0.6,
    labels={
        'unique_categories_purchased': 'Categories Purchased',
        'avg_nmv_per_order': 'Avg Order Value (R$)',
        'segment_label': 'Growth Segment',
        'delivered_orders': 'Orders'
    },
    hover_data={
        'avg_nmv_per_order': ':.2f',
        'unique_categories_purchased': True,
        'delivered_orders': True
    }
)

fig.update_layout(
    height=500,
    margin=dict(l=20, r=20, t=20, b=20),
    plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family="Inter, sans-serif", size=12),
    xaxis=dict(gridcolor='#F1F5F9'),
    yaxis=dict(gridcolor='#F1F5F9'),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(size=11)
    )
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# SEGMENT STRATEGY CARDS
# ============================================================

st.subheader("Segment Strategies")

for _, seg in segment_summary.sort_values('total_revenue', ascending=False).iterrows():
    seg_key = seg['actionable_segment']
    color = segment_colors.get(seg_key, '#64748B')
    label = segment_labels.get(seg_key, seg_key)
    description = segment_descriptions.get(seg_key, '')
    
    st.markdown(f"""
    <div style="background-color:white; padding:16px; border-radius:8px; 
                border-left:4px solid {color}; margin-bottom:12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
            <strong style="color:#111827; font-size:1rem;">{label}</strong>
            <span style="font-size:0.85rem; color:#64748B;">
                {int(seg['customer_count']):,} customers | Avg R${seg['avg_nmv']:.0f}/order | 
                {seg['avg_categories']:.1f} categories | ★ {seg['avg_review']:.1f}
            </span>
        </div>
        <p style="margin:0; font-size:0.85rem; color:#475569; line-height:1.6;">
            {description}
        </p>
    </div>
    """, unsafe_allow_html=True)
