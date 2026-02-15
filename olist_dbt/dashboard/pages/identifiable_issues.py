import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from matplotlib_venn import venn3
from matplotlib.patches import Circle
import matplotlib.patches as mpatches

sys.path.append(str(Path(__file__).parent.parent/"utils"))
from db_connection import run_query

st.title("IDENTIFIABLE ISSUES")

# AT RISK OVERVIEW
# LOAD DATA
at_risk_customer_query = """
SELECT
    customer_id,
    lifecycle_stage,
    has_satisfaction_issue AS has_quality_issues,
    (has_delivery_issue OR has_stockout_issue) AS has_operational_issues,
    (has_promo_dependency OR has_freight_burden) AS has_economic_issues,
    total_issues
FROM dev.main_marts.mart_customer_value_growth
WHERE lifecycle_stage LIKE '%_at_risk'
"""

at_risk_customer_df = run_query(at_risk_customer_query)
total_at_risk = len(at_risk_customer_df)
# Silent Churn
silent_churn_df = at_risk_customer_df[at_risk_customer_df['total_issues'] == 0]
silent_churn_count = len(silent_churn_df)
# Identifiable Issues: customers with at least one issue
identifiable_df = at_risk_customer_df[at_risk_customer_df['total_issues'] > 0]
identifiable_count = len(identifiable_df)
# Calculate percentage
pct_silent_churn = silent_churn_count / total_at_risk * 100
pct_identifiable = identifiable_count / total_at_risk * 100

quality_issues = set(identifiable_df[identifiable_df['has_quality_issues']]['customer_id'])
operational_issues = set(identifiable_df[identifiable_df['has_operational_issues']]['customer_id'])
economic_issues = set(identifiable_df[identifiable_df['has_economic_issues']]['customer_id'])

fig = plt.figure(figsize=(16, 9), facecolor='white')
ax = fig.add_axes([0.02, 0.05, 0.96, 0.9])

# === LEFT DIAGRAM - IDENTIFIABLE ISSUES
venn = venn3(
    [quality_issues, operational_issues, economic_issues],
    set_labels=(
        f'Quality/Experience\n{len(quality_issues):,} customers',
        f'Operational Failures\n{len(operational_issues):,} customers',
        f'Economic Barriers\n{len(economic_issues):,} customers'
    ),
    ax=ax,
    alpha=0.75,
    subset_label_formatter=lambda x: f'{(x/total_at_risk*100):.1f}%' if x > 0 else ''
)

# Colors
venn.get_patch_by_id('100').set_color('#FCA5A5')
venn.get_patch_by_id('010').set_color('#93C5FD')
venn.get_patch_by_id('001').set_color('#FCD34D')
venn.get_patch_by_id('110').set_color('#DDA5E8')
venn.get_patch_by_id('101').set_color('#FFCFA3')
venn.get_patch_by_id('011').set_color('#B4E7CE')
venn.get_patch_by_id('111').set_color('#E5D5F0')

# Enhanced label styling
for text in venn.set_labels:
    text.set_fontsize(14)
    text.set_weight('bold')
    text.set_color('#1F2937')

for text in venn.subset_labels:
    if text:
        text.set_fontsize(13)
        text.set_weight('bold')
        text.set_color('#374151')

# RIGHT: Silent Churn Circle 
silent_radius = 0.75

silent_circle = Circle(
    xy=(1.7, 0),  
    radius=silent_radius,
    facecolor='#E5E7EB',
    edgecolor='none',  # No border
    alpha=0.9
)
ax.add_patch(silent_circle)

# Question mark (no bbox, no frame)
ax.text(
    1.7, 0.5,
    '❓',
    ha='center',
    va='center',
    fontsize=60,
    alpha=0.6
)

# Count and percentage
ax.text(
    1.7, -0.05,
    f'{silent_churn_count:,} customers\n({pct_silent_churn:.1f}%)',
    ha='center',
    va='center',
    fontsize=14,
    weight='bold',
    color='#1F2937'
)

# "Silent Churn" label
ax.text(
    1.7, -0.6,
    'Silent Churn',
    ha='center',
    va='center',
    fontsize=15,
    weight='bold',
    color='#374151'
)

# Subtitle
ax.text(
    1.7, -0.85,
    'No identifiable data signals',
    ha='center',
    va='center',
    fontsize=11,
    style='italic',
    color='#6B7280'
)

# Main title at top
fig.text(
    0.5, 0.97,
    f'Customer Churn Analysis: {total_at_risk:,} At-Risk Customers',
    ha='center',
    fontsize=17,
    weight='bold',
    color='#111827'
)

# Subtitle
fig.text(
    0.5, 0.93,
    f'Identifiable Issues ({pct_identifiable:.1f}%) vs. Silent Churn ({pct_silent_churn:.1f}%)',
    ha='center',
    fontsize=13,
    color='#4B5563'
)

# Bottom caption
fig.text(
    0.5, 0.01,
    'Left: Customers with data-driven investigation paths  |  Right: Customers with successful delivery but no obvious friction',
    ha='center',
    fontsize=10,
    style='italic',
    color='#6B7280'
)

# Tight axis limits to maximize diagram size
ax.set_xlim(-1.6, 2.8)
ax.set_ylim(-1.3, 1.3)
ax.axis('off')

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
st.pyplot(fig, use_container_width=True)

# OPERATIONAL FAILURES
# LOAD DATA
operational_failures_query = """
WITH operational_orders AS (
    SELECT
        fo.order_id,
        fo.order_status,
        BOOL_AND(foi.met_shipping_deadline) AS is_shipping_late
    FROM dev.main_dims.dim_customers dc
    LEFT JOIN dev.main_marts.mart_customer_value_growth mcvg
        ON dc.customer_id = mcvg.customer_id
    JOIN dev.main_facts.fact_orders fo
        ON dc.customer_key = fo.customer_key
    LEFT JOIN dev.main_facts.fact_order_items foi
        ON fo.order_id = foi.order_id
    WHERE (mcvg.has_delivery_issue = TRUE OR mcvg.has_stockout_issue = TRUE)
        AND (fo.delivered_on_time = FALSE OR fo.order_status = 'unavailable') 
        AND fo.order_status IN ('delivered', 'unavailable')
    GROUP BY fo.order_id, fo.order_status)
SELECT
    SUM(CASE WHEN order_status = 'unavailable' THEN 1 ELSE 0 END) AS unavailable_orders,
    SUM(CASE WHEN is_shipping_late = TRUE THEN 1 ELSE 0 END) AS late_shipping_orders,
    COUNT(*) AS total_orders
FROM operational_orders
"""

operational_failures_df = run_query(operational_failures_query)

unavailable_orders = int(operational_failures_df['unavailable_orders'].iloc[0])
late_shipping_orders = int(operational_failures_df['late_shipping_orders'].iloc[0])
total_orders = int(operational_failures_df['total_orders'].iloc[0])
late_delivery_orders = total_orders - unavailable_orders - late_shipping_orders

seller_accountability = unavailable_orders + late_shipping_orders
logistics_accountability = late_delivery_orders

labels = [
    f"Operational Failures<br>{total_orders:,} orders",
    f"Unavailable<br>{unavailable_orders:,} orders",
    f"Late Delivery<br>{late_shipping_orders + late_delivery_orders:,} orders",
    f"Seller Accountability<br>{seller_accountability:,} orders<br>({seller_accountability/total_orders*100:.1f}%)",
    f"Logistics Accountability<br>{logistics_accountability:,} orders<br>({logistics_accountability/total_orders*100:.1f}%)"
]

sources = [0, 0, 1, 2, 2]
targets = [1, 2, 3, 3, 4]

values = [
    unavailable_orders, 
    late_delivery_orders + late_shipping_orders,
    unavailable_orders,
    late_shipping_orders,
    late_delivery_orders
]

fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=20,
        thickness=25,
        line=dict(color='white', width=2),
        label=labels,
        color=[
            '#64748B',  # Operational Failures - Dark gray/slate
            '#EF4444',  # Unavailable - Strong red
            '#3B82F6',  # Late Delivery - Strong blue
            '#DC2626',  # Seller Accountability - Dark red
            '#1D4ED8'   # Logistics Accountability - Dark blue
        ]
    ),
    link=dict(
        source=sources,
        target=targets,
        value=values,
        color=[
            'rgba(239, 68, 68, 0.5)',   # Operational → Unavailable (red with opacity)
            'rgba(59, 130, 246, 0.5)',  # Operational → Late Delivery (blue with opacity)
            'rgba(220, 38, 38, 0.6)',   # Unavailable → Seller (dark red)
            'rgba(220, 38, 38, 0.4)',   # Late Delivery → Seller (red with less opacity)
            'rgba(29, 78, 216, 0.6)'    # Late Delivery → Logistics (dark blue)
        ],
        label=[
            f"{unavailable_orders:,}",
            f"{late_shipping_orders + late_delivery_orders:,}",
            f"{unavailable_orders:,}",
            f"{late_shipping_orders:,}",
            f"{late_delivery_orders:,}"
        ]
    ),
    textfont=dict(
        color='white',  # WHITE TEXT for all labels
        size=13,
        family='Inter, sans-serif'
    )
)])

fig.update_layout(
    title=dict(
        text="Operational Failures: Order-Level Accountability",
        font=dict(size=18, family="Inter, sans-serif", color='#111827'),
        x=0.5,
        xanchor='center'
    ),
    font=dict(size=12, family="Inter, sans-serif", color='#111827'),
    height=500,
    margin=dict(l=20, r=20, t=60, b=20),
    paper_bgcolor='white',
    plot_bgcolor='white'
)

st.plotly_chart(fig, use_container_width=True)