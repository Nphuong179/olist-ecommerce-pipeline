import streamlit as st
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent/"utils"))
from db_connection import run_query

st.title("FAILED ACQUISITION ANALYSIS")

# CONTEXT BOX
context_query = """
SELECT 
    COUNT(*) as total_failed,
    SUM(total_nmv) as lost_revenue,
    ROUND(AVG(days_since_last_order), 0) as avg_days_since
FROM dev.main_marts.mart_customers_base
WHERE delivered_orders = 0
"""

context_df = run_query(context_query)

total_failed = int(context_df['total_failed'].iloc[0])
lost_revenue = context_df['lost_revenue'].iloc[0]
avg_days = int(context_df['avg_days_since'].iloc[0])

st.markdown(f"""
<div style="background-color:#FEF2F2; padding:16px; border-radius:8px; margin-bottom:24px; border-left:4px solid #DC2626;">
    <p style="margin:0; color:#991B1B; font-size:0.95rem; line-height:1.7;">
        <strong>Operational Crisis:</strong> <strong>{total_failed:,}</strong> customers never received their first order, 
        representing <strong>R$ {lost_revenue:,.2f}</strong> in collected but undelivered revenue. 
        These orders have been stuck for an average of <strong>{avg_days} days</strong>.
        <br><br>
        This is not a customer retention problem—it's a complete <strong>acquisition failure</strong> caused by 
        operational breakdowns in fulfillment, logistics, and inventory management. Every failed delivery represents 
        a customer who paid money but received nothing, resulting in refunds, negative reviews, and permanent loss.
    </p>
</div>
""", unsafe_allow_html=True)

# ACCOUNTABILITY DECOMPOSITION TREE
st.subheader("Accountability Breakdown")

st.markdown("""
<div style="background-color:#FFFBEB; padding:12px; border-radius:6px; margin-bottom:16px; border-left:3px solid #F59E0B; font-size:0.9rem; color:#92400E;">
    <strong>Purpose:</strong> Map each failed order to the responsible party based on order status following the e-commerce fulfillment flow: 
    <code>created → approved → invoiced → processing → shipped → delivered</code>
</div>
""", unsafe_allow_html=True)

# Query order status breakdown for failed customers
accountability_query = """
SELECT 
    latest_order_status,
    COUNT(*) as customer_count,
    SUM(total_nmv) as lost_revenue,
    ROUND(AVG(days_since_last_order), 0) as avg_days_stuck
FROM dev.main_marts.mart_customers_base
WHERE delivered_orders = 0
GROUP BY latest_order_status
ORDER BY customer_count DESC
"""

accountability_df = run_query(accountability_query)

# UPDATED accountability mapping based on correct order flow
def map_accountability(status):
    status_lower = status.lower()
    
    # Created - Platform issue
    if 'created' in status_lower:
        return {
            'party': 'Platform (Olist)',
            'stage': 'Order Creation',
            'root_cause': 'Order Creation Failure',
            'investigation': 'Check system logs for order creation errors',
            'action': 'Technical investigation of order processing system',
            'priority': 'High',
            'teams': ['Engineering', 'Operations']
        }
    
    # Approved - Customer payment pending
    elif 'approved' in status_lower:
        return {
            'party': 'Customer',
            'stage': 'Payment Processing',
            'root_cause': 'Payment Not Processed',
            'investigation': 'Verify if payment was attempted; Check payment gateway logs',
            'action': 'Contact customers to resolve payment issues or offer payment assistance',
            'priority': 'Medium',
            'teams': ['Customer Service', 'Payment Team']
        }
    
    # Invoiced - Handoff failure between payment and seller
    elif 'invoiced' in status_lower:
        return {
            'party': 'Platform (Olist)',
            'stage': 'Order Processing',
            'root_cause': 'Fulfillment Handoff Failure',
            'investigation': 'Check order processing system; Verify seller notification delivery',
            'action': 'Manual order push to seller; Fix integration issues',
            'priority': 'High',
            'teams': ['Operations', 'Engineering']
        }
    
    # Processing - Seller hasn't fulfilled order
    elif 'processing' in status_lower:
        return {
            'party': 'Seller/Merchant',
            'stage': 'Order Fulfillment',
            'root_cause': 'Seller Fulfillment Negligence',
            'investigation': 'Contact seller to check fulfillment status; Verify if items are in stock',
            'action': 'Escalate to seller; Set fulfillment deadline or cancel & refund',
            'priority': 'High',
            'teams': ['Merchant Support', 'Operations']
        }
    
    # Shipped - Logistics failure
    elif 'shipped' in status_lower or 'ready_for_shipment' in status_lower:
        return {
            'party': 'Logistics Partner',
            'stage': 'Delivery',
            'root_cause': 'Package Lost or Stuck in Transit',
            'investigation': 'Track package with carrier; Locate shipment',
            'action': 'File claim with carrier; Arrange reship or refund',
            'priority': 'High',
            'teams': ['Logistics Coordination', 'Customer Service']
        }
    
    # Canceled - Customer decision
    elif 'canceled' in status_lower or 'cancelled' in status_lower:
        return {
            'party': 'Customer',
            'stage': 'Order Placement',
            'root_cause': 'Customer-Initiated Cancellation',
            'investigation': 'Analyze cancellation timing (immediate vs delayed); Identify patterns',
            'action': 'Survey customers for cancellation reasons; Improve checkout/delivery experience',
            'priority': 'Low',
            'teams': ['Customer Experience', 'Marketing']
        }
    
    # Unavailable - Seller stockout
    elif 'unavailable' in status_lower:
        return {
            'party': 'Seller/Merchant',
            'stage': 'Inventory Management',
            'root_cause': 'Inventory Stockout (Overselling)',
            'investigation': 'Identify sellers with frequent stockouts; Check inventory sync',
            'action': 'Penalize repeat offenders; Improve real-time inventory tracking',
            'priority': 'High',
            'teams': ['Merchant Support', 'Operations', 'Engineering']
        }
    
    # Unknown/Other
    else:
        return {
            'party': 'Platform (Olist)',
            'stage': 'Unknown',
            'root_cause': 'System Investigation Required',
            'investigation': 'Review order lifecycle; Identify where process broke',
            'action': 'Manual investigation and resolution',
            'priority': 'Medium',
            'teams': ['Operations', 'Customer Service']
        }

# Apply mapping - expand the dictionary into columns
accountability_expanded = accountability_df['latest_order_status'].apply(
    lambda x: pd.Series(map_accountability(x))
)
accountability_df = pd.concat([accountability_df, accountability_expanded], axis=1)

icicle_data = []
total_failed = int(accountability_df['customer_count'].sum())

# Level 0: Root
icicle_data.append({
    'labels': 'Failed Acquisition',
    'parents': '',
    'values': total_failed,
    'ids': 'root',
    'party_type': 'root'
})

# Level 1: Responsible Parties
party_summary = accountability_df.groupby('party')['customer_count'].sum().reset_index()

for idx, row in party_summary.iterrows():
    party = row['party']
    count = int(row['customer_count'])
    pct = (count / total_failed) * 100
    
    icicle_data.append({
        'labels': f'{party}<br>{count:,} ({pct:.1f}%)',
        'parents': 'root',  # ✅ References root ID
        'values': count,
        'ids': party,  # Simple party name as ID
        'party_type': party
    })

# Level 2: Root Causes
for idx, row in accountability_df.iterrows():
    party = row['party']
    cause = row['root_cause']
    status = row['latest_order_status']
    count = int(row['customer_count'])
    
    cause_id = f'{party}_{status}'  # Unique ID combining party and status
    
    icicle_data.append({
        'labels': f'{cause}<br>{status}: {count:,}',
        'parents': party,  # ✅ References party ID (which is party name)
        'values': count,
        'ids': cause_id,
        'party_type': party
    })

# Level 3: Actions/Solutions
for idx, row in accountability_df.iterrows():
    party = row['party']
    status = row['latest_order_status']
    investigation = row['investigation']
    action = row['action']
    teams = row['teams']
    count = int(row['customer_count'])
    
    cause_id = f'{party}_{status}'
    action_id = f'action_{party}_{status}'
    
    # Format investigation
    investigation_parts = [part.strip() for part in investigation.split(';')]
    investigation_formatted = '<br>• '.join(investigation_parts)
    investigation_formatted = '• ' + investigation_formatted

    # Format actions with bullet points on separate lines
    action_parts = [part.strip() for part in action.split(';')]
    action_formatted = '<br>• '.join(action_parts)
    action_formatted = '• ' + action_formatted

    # Format team
    teams_list = ', '.join(teams)

    # Combine three sections with headers
    comprehensive_label = (
    f'INVESTIGATION:<br>{investigation_formatted}<br><br>'
    f'ACTION REQUIRED:<br>{action_formatted}<br><br>'
    f'TEAMS: {teams_list}'
    )
    
    icicle_data.append({
        'labels': comprehensive_label,
        'parents': cause_id,
        'values': count,
        'ids': action_id,
        'party_type': party
    })

icicle_df = pd.DataFrame(icicle_data)
def get_layer_depth(row):
    if row['ids'] == 'root':
        return 0
    elif row['parents'] == 'root':
        return 1
    elif row['parents'] in ['Customer', 'Seller/Merchant', 'Logistics Partner', 'Platform (Olist)']:
        return 2
    else:
        return 3

icicle_df['layer_depth'] = icicle_df.apply(get_layer_depth, axis=1)
gradient_colors = {
    'root': {
        0: '#475569',
        1: '#475569',
        2: '#475569',
        3: '#475569'
    },
    'Customer': {
        1: '#8A5C00',
        2: '#DB9200',
        3: '#E8A600'
    },
    'Seller/Merchant': {
        1: '#910000',
        2: '#C41E3A',
        3: '#D20A2E' 
    },
    'Logistics Partner': {
        1: '#000099',
        2: '#0000CD',
        3: '#0000CD'
    },
    'Platform (Olist)': {
        1: '#B01C55',
        2: '#E3256B',
        3: '#FF4D8B'
    }
}

def get_gradient_color_manual(row):
    party = row['party_type']
    depth = row['layer_depth']
    if party in gradient_colors and depth in gradient_colors[party]:
        return gradient_colors[party][depth]
    return '#64748B'

icicle_df['node_color'] = icicle_df.apply(get_gradient_color_manual, axis=1)
# Create Icicle chart using px (same approach that worked before)
fig = go.Figure(go.Icicle(
    labels=icicle_df['labels'],
    parents=icicle_df['parents'],
    values=icicle_df['values'],
    ids=icicle_df['ids'],
    marker=dict(
        colors=icicle_df['node_color'],
        line=dict(color='white', width=3),
        colorscale=None,
        showscale=False
    ),
    branchvalues='total',
    hoverinfo='skip'
))

fig.update_traces(
    textfont=dict(
        size=14,
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

st.markdown("""
<div style="background-color:#EFF6FF; padding:10px; border-radius:6px; font-size:0.85rem; color:#1E40AF; margin-bottom:20px;">
    <strong>How to read (4 Levels):</strong>
    <ul style="margin:8px 0 0 20px; padding:0;">
        <li><strong>Level 1:</strong> Failed Acquisition (2,732 total customers)</li>
        <li><strong>Level 2:</strong> Responsible Party (color-coded by accountability)</li>
        <li><strong>Level 3:</strong> Root Cause (specific failure type)</li>
        <li><strong>Level 4:</strong> Required Action (remediation steps)</li>
    </ul>
    Click any segment to zoom into the accountability chain.
</div>
""", unsafe_allow_html=True)