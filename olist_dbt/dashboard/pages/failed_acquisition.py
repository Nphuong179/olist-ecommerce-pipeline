import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.db_connection import run_query
from utils.styles import (COLORS, context_box, chart_instruction_box, analysis_sidepanel)

st.title("FAILED ACQUISITION ANALYSIS")

# DATA LOADING
context_df = run_query("""
SELECT 
    COUNT(distinct mcb.customer_id) as total_failed,
    ROUND(SUM(item_price)) as lost_revenue,
    ROUND(AVG(days_since_last_order), 0) as avg_days_since
FROM `olist-portfolio-491906.olist_dbt_marts.mart_customers_base` mcb
LEFT JOIN `olist-portfolio-491906.olist_dbt_dims.dim_customers` dc
    ON mcb.customer_id = dc.customer_id
LEFT JOIN `olist-portfolio-491906.olist_dbt_facts.fact_order_items` foi
    ON dc.customer_key = foi.customer_key
WHERE mcb.delivered_orders = 0
""")

total_failed = int(context_df['total_failed'].iloc[0])
lost_revenue = int(context_df['lost_revenue'].iloc[0])
avg_days = int(context_df['avg_days_since'].iloc[0])

# SECTION 1: CONTEXT BOX
st.markdown(context_box(
    f"""<strong style="font-size:1.05rem;">
        Why did customers never receive their first order?
    </strong>
    <br><br>
    <strong>{total_failed:,}</strong> customers never received their first order, 
    representing <strong>R$ {lost_revenue:,}</strong> in collected but undelivered revenue. 
    These orders have been stuck for an average of <strong>{avg_days} days</strong>.
    <br><br>
    This is not a customer retention problem — it's a complete <strong>acquisition failure</strong> 
    caused by operational breakdowns in fulfillment, logistics, and inventory management. 
    Every failed delivery represents a customer who paid but received nothing.""",
    variant="failure"
), unsafe_allow_html=True)

# SECTION 2: ACCOUNTABILITY DECOMPOSITION TREE
st.subheader("Accountability Breakdown")

st.markdown("""
<div style="background-color:#EFF6FF; padding:16px 18px; border-radius:8px; 
            border-left:4px solid #2563EB; margin-bottom:16px;">
    <p style="margin:0 0 12px 0; color:#1E40AF; font-size:0.92rem; line-height:1.6;">
        <strong>Purpose:</strong> Trace each failed order to its responsible party through the fulfillment pipeline:
    </p>
    <p style="margin:0 0 14px 0; text-align:center; font-size:1.05rem; font-weight:700; 
              color:#1E40AF; letter-spacing:0.03em;">
        Created → Approved → Invoiced → Processing → Shipped → Delivered
    </p>
    <hr style="border:none; border-top:1px solid #BFDBFE; margin:12px 0;">
    <p style="margin:0 0 8px 0; color:#1E40AF; font-size:0.92rem; font-weight:600;">
        How to read (4 Levels):
    </p>
    <ul style="margin:0 0 12px 20px; padding:0; color:#1E40AF; font-size:0.88rem; line-height:1.8;">
        <li><strong>Level 1:</strong> Failed Acquisition (total customers)</li>
        <li><strong>Level 2:</strong> Responsible Party</li>
        <li><strong>Level 3:</strong> Root Cause — identified by latest order status</li>
        <li><strong>Level 4:</strong> Investigation Plans, Required Action</li>
    </ul>
    <div style="background-color:#1E40AF; border-radius:6px; padding:10px 14px; 
                display:flex; align-items:center; gap:10px;">
        <span style="font-size:1.3rem;">👆</span>
        <strong style="color:#FFFFFF; font-size:0.92rem;">
            Click any segment to zoom into its accountability chain — click the center to zoom back out.
        </strong>
    </div>
</div>
""", unsafe_allow_html=True)

# Query order status breakdown for failed customers
accountability_query = """
SELECT 
    latest_order_status,
    COUNT(*) as customer_count,
    SUM(total_nmv) as lost_revenue,
    ROUND(AVG(days_since_last_order), 0) as avg_days_stuck
FROM `olist-portfolio-491906.olist_dbt_marts.mart_customers_base`
WHERE delivered_orders = 0
GROUP BY latest_order_status
ORDER BY customer_count DESC
"""

accountability_df = run_query(accountability_query)

# UPDATED accountability mapping based on correct order flow
def map_accountability(status):
    mapping = {
        'created': {
            'party': 'Platform (Olist)',
            'root_cause': 'Order Routing Failure',
            'investigation': (
                'Check payment gateway response logs for timeout or authorization failure; '
                'Verify seller assignment queue processed the order'
            ),
            'action': (
                'Retry payment authorization if gateway timeout; '
                'Manually assign seller if routing queue stuck; '
                'Refund customer if unrecoverable after 48h'
            ),
            'teams': ['Engineering', 'Payment Ops']
        },
        'approved': {
            'party': 'Platform (Olist)',
            'root_cause': 'Seller Notification Failure',
            'investigation': (
                'Payment was approved but order never reached the seller. '
                'Check if seller notification system delivered the order alert; '
                'Verify order appeared in seller dashboard'
            ),
            'action': (
                'Re-send seller notification; '
                'If seller unresponsive after 24h, reassign to backup seller or cancel with full refund'
            ),
            'teams': ['Operations', 'Merchant Support']
        },
        'invoiced': {
            'party': 'Platform (Olist)',
            'root_cause': 'Invoice-to-Fulfillment Automation Failure',
            'investigation': (
                'Check if the invoice-to-processing automation triggered; '
                'Verify seller received and acknowledged the fulfillment request'
            ),
            'action': (
                'Re-trigger fulfillment workflow; '
                'If seller shows no acknowledgment within 24h, escalate to Merchant Support; '
                'Fix automation pipeline if system-level failure confirmed'
            ),
            'teams': ['Operations', 'Engineering']
        },
        'processing': {
            'party': 'Seller/Merchant',
            'root_cause': 'Seller Fulfillment Delay',
            'investigation': (
                'Check days since seller acknowledged vs. fulfillment SLA; '
                'Review this seller recent fulfillment rate for pattern of delays'
            ),
            'action': (
                'Send warning at 48h past SLA; '
                'Auto-escalate and reassign at 72h; '
                'Suspend seller listing if pattern of repeated delays detected'
            ),
            'teams': ['Merchant Support', 'Operations']
        },
        'shipped': {
            'party': 'Logistics Partner',
            'root_cause': 'Package Lost or Stuck in Transit',
            'investigation': (
                'Check last carrier scan event to determine failure point: '
                'no scan after pickup = first-mile loss (seller-to-hub); '
                'last scan at sorting hub = in-transit loss (hub-to-customer)'
            ),
            'action': (
                'No scan after pickup: contact seller to verify carrier handoff actually occurred; '
                'Hub scan exists: file carrier claim for lost package; '
                'Both cases: arrange reship or full refund to customer'
            ),
            'teams': ['Logistics Ops', 'Carrier Relations']
        },
        'canceled': {
            'party': 'Customer',
            'root_cause': 'Customer-Initiated Cancellation',
            'investigation': (
                'Analyze cancellation timing: immediate (within 1h) suggests checkout friction, '
                'delayed (after 24h+) suggests buyer remorse or found better price elsewhere'
            ),
            'action': (
                'Deploy exit survey at cancellation point; '
                'For delayed cancellations, test proactive order confirmation messaging; '
                'Analyze if specific product categories have higher cancellation rates'
            ),
            'teams': ['Customer Experience', 'Product']
        },
        'unavailable': {
            'party': 'Seller/Merchant',
            'root_cause': 'Inventory Stockout (Overselling)',
            'investigation': (
                'Identify sellers with stockout rate above 5%; '
                'Check inventory sync frequency between seller system and Olist platform'
            ),
            'action': (
                'Penalize sellers exceeding 5% stockout rate with reduced listing visibility; '
                'Require real-time inventory API integration for high-volume sellers; '
                'Immediate refund to affected customers'
            ),
            'teams': ['Merchant Support', 'Engineering']
        }
    }
    
    return mapping.get(status.lower(), {
        'party': 'Platform (Olist)',
        'root_cause': 'System Investigation Required',
        'investigation': 'Order stuck at unrecognized status. Review full order event log to identify where the pipeline broke',
        'action': 'Manual investigation; Escalate to Engineering if no event log entries found after order creation',
        'teams': ['Operations', 'Engineering']
    })

# Apply mapping - expand the dictionary into columns
accountability_expanded = accountability_df['latest_order_status'].apply(
    lambda x: pd.Series(map_accountability(x))
)
accountability_df = pd.concat([accountability_df, accountability_expanded], axis=1)

icicle_data = []
total_failed_chart = int(accountability_df['customer_count'].sum())

# Level 0: Root
icicle_data.append({
    'labels': 'Failed Acquisition',
    'parents': '',
    'values': total_failed_chart,
    'ids': 'root',
    'party_type': 'root'
})

# Level 1: Responsible Parties
party_summary = accountability_df.groupby('party')['customer_count'].sum().reset_index()

for _, row in party_summary.iterrows():
    party = row['party']
    count = int(row['customer_count'])
    pct = (count / total_failed_chart) * 100
    
    icicle_data.append({
        'labels': f'{party}<br>{count:,} ({pct:.1f}%)',
        'parents': 'root',
        'values': count,
        'ids': party,
        'party_type': party
    })

# Level 2: Root Causes
for _, row in accountability_df.iterrows():
    party = row['party']
    cause = row['root_cause']
    status = row['latest_order_status']
    count = int(row['customer_count'])
    
    icicle_data.append({
        'labels': f'{cause}<br>{status}: {count:,}',
        'parents': party,
        'values': count,
        'ids': f'{party}_{status}',
        'party_type': party
    })

# Level 3: Actions/Solutions
for _, row in accountability_df.iterrows():
    party = row['party']
    status = row['latest_order_status']
    count = int(row['customer_count'])
    
    inv_parts = [p.strip() for p in row['investigation'].split(';')]
    inv_formatted = '• ' + '<br>• '.join(inv_parts)
    
    act_parts = [p.strip() for p in row['action'].split(';')]
    act_formatted = '• ' + '<br>• '.join(act_parts)
    
    teams_list = ', '.join(row['teams'])
    
    label = (
        f'INVESTIGATION:<br>{inv_formatted}<br><br>'
        f'ACTION REQUIRED:<br>{act_formatted}<br><br>'
        f'INVOLVED TEAMS: {teams_list}'
    )
    
    icicle_data.append({
        'labels': label,
        'parents': f'{party}_{status}',
        'values': count,
        'ids': f'action_{party}_{status}',
        'party_type': party
    })

icicle_df = pd.DataFrame(icicle_data)
def get_layer_depth(row):
    if row['ids'] == 'root':
        return 0
    elif row['parents'] == 'root':
        return 1
    elif row['parents'] in party_summary['party'].values:
        return 2
    else:
        return 3

icicle_df['layer_depth'] = icicle_df.apply(get_layer_depth, axis=1)
gradient_colors = {
    'root': {0: '#475569'},
    'Customer': {1: '#8A5C00', 2: '#DB9200', 3: '#E8A600'},
    'Seller/Merchant': {1: '#910000', 2: '#C41E3A', 3: '#D20A2E'},
    'Logistics Partner': {1: '#000099', 2: '#0000CD', 3: '#0000CD'},
    'Platform (Olist)': {1: '#B01C55', 2: '#E3256B', 3: '#FF4D8B'}
}

icicle_df['node_color'] = icicle_df.apply(
    lambda r: gradient_colors.get(r['party_type'], {}).get(r['layer_depth'], '#64748B'),
    axis=1
)

# Build Icicle Chart
fig = go.Figure(go.Icicle(
    labels=icicle_df['labels'],
    parents=icicle_df['parents'],
    values=icicle_df['values'],
    ids=icicle_df['ids'],
    marker=dict(
        colors=icicle_df['node_color'],
        line=dict(color='white', width=3)
    ),
    branchvalues='total',
    hoverinfo='skip'
))

fig.update_traces(
    textfont=dict(
        size=16,
        family="Inter, sans-serif",
        color='white'
    ),
    textposition='middle left'
)

fig.update_layout(
    height=700,
    margin=dict(l=0, r=0, t=10, b=10),
    font=dict(family="Inter, sans-serif", size=11)
)

st.plotly_chart(fig, use_container_width=True)

# SECTION 3: MONTHLY TREND
st.subheader("Pipeline Failure Over Time")

trend_df = run_query("""
    SELECT 
        DATE_TRUNC(fo.order_purchase_timestamp, MONTH) AS order_month,
        fo.order_status,
        COUNT(DISTINCT dc.customer_id) AS failed_customers
    FROM `olist-portfolio-491906.olist_dbt_marts.mart_customers_base` mcb
    JOIN `olist-portfolio-491906.olist_dbt_dims.dim_customers` dc
        ON mcb.customer_id = dc.customer_id
    JOIN `olist-portfolio-491906.olist_dbt_facts.fact_orders` fo
        ON dc.customer_key = fo.customer_key
    WHERE mcb.delivered_orders = 0
        AND fo.order_purchase_timestamp < '2018-09-01'
        AND fo.order_status IN ('created', 'approved', 'invoiced', 'processing', 'shipped')
    GROUP BY order_month, fo.order_status
    ORDER BY order_month
""")

if not trend_df.empty:
    # Status color mapping — consistent with accountability semantics
    status_colors = {
        'created': '#8B5CF6',
        'approved': '#A78BFA',
        'invoiced': '#EC4899',
        'processing': '#F97316',
        'shipped': '#3B82F6',
    }
    
    fig = px.line(
        trend_df,
        x='order_month',
        y='failed_customers',
        color='order_status',
        facet_row='order_status',
        color_discrete_map=status_colors,
        labels={
            'order_month': '',
            'failed_customers': 'Customers',
            'order_status': 'Status'
        }
    )
    
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1].title()))

    fig.update_traces(fill='tozeroy', fillcolor=None)
    # Apply semi-transparent fill matching each line's color
    for trace in fig.data:
        status = trace.name
        base_color = status_colors.get(status, '#64748B')
        # Convert hex to rgba with 0.15 opacity for subtle fill
        r, g, b = int(base_color[1:3], 16), int(base_color[3:5], 16), int(base_color[5:7], 16)
        trace.fillcolor = f'rgba({r},{g},{b},0.15)'

    fig.update_layout(
        height=600,
        margin=dict(l=20, r=20, t=10, b=20),
        font=dict(family="Inter, sans-serif", size=11),
        plot_bgcolor='white',
        paper_bgcolor='white',
        showlegend=False,  # Facet labels serve as legend
        xaxis=dict(gridcolor='#F1F5F9'),
        yaxis=dict(gridcolor='#F1F5F9')
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"""
<div style="background-color:#F8FAFC; padding:20px; border-radius:8px; border-left:4px solid {COLORS['failure']};">
<h4 style="margin:0 0 12px 0; color:#1E293B; font-size:1.2rem;">Finding</h4>
<p style="margin:0; font-size:1.0rem; color:#475569; line-height:1.6;">
<strong>Shipped</strong>, <strong>Processing</strong> and <strong>Invoiced</strong> failures persist
at steady rates across the entire period &mdash; suggesting systemic issues rather than isolated incidents.
</p>
</div>""", unsafe_allow_html=True)

# NAVIGATION FOOTER

at_risk_count_df = run_query("""
    SELECT COUNT(DISTINCT customer_id) AS customer_count
    FROM `olist-portfolio-491906.olist_dbt_marts.mart_customer_value_growth`
    WHERE lifecycle_stage LIKE '%_at_risk'
        AND total_issues > 0
""")
at_risk_with_issues = int(at_risk_count_df['customer_count'].iloc[0])

st.divider()

col_footer_text, col_footer_link = st.columns([3, 1])

with col_footer_text:
    st.markdown(f"""
    <div>
        <p style="margin:0 0 4px 0; font-size:0.85rem; color:#F59E0B; text-transform:uppercase; letter-spacing:0.05em; font-weight:700;">Next Step</p>
        <p style="margin:0 0 8px 0; font-size:0.95rem; color:#92400E; line-height:1.5;">
        Among customers who did receive orders, {at_risk_with_issues:,} show identifiable
        friction points we can act on. Diagnose which issues are fixable.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_footer_link:
    st.page_link(
        "pages/at_risk.py",
        label="At-Risk Customers →"
    )
