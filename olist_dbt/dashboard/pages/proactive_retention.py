import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from utils.db_connection import run_query
from utils.styles import COLORS, context_box, analysis_sidepanel

st.title("PROACTIVE RETENTION")

# DATA LOADING
# DATA LOAING - Dataset A: Historical baseline. How many days between 1st and 2nd order for repeat customers.
repeat_interval_df = run_query("""
    WITH customer_order_sequence AS (
        SELECT
            dc.customer_id,
            fo.order_id,
            fo.order_purchase_timestamp,
            ROW_NUMBER() OVER(PARTITION BY dc.customer_id ORDER BY fo.order_purchase_timestamp ASC) AS order_sequence
        FROM `olist-portfolio-491906.olist_dbt_dims.dim_customers` dc 
        JOIN `olist-portfolio-491906.olist_dbt_marts.mart_customer_lifecycle` mcl 
            ON dc.customer_id = mcl.customer_id
        LEFT JOIN `olist-portfolio-491906.olist_dbt_facts.fact_orders` fo
            ON dc.customer_key = fo.customer_key
        WHERE mcl.lifecycle_stage like 'repeat%')
    SELECT 
        customer_id,
        TIMESTAMP_DIFF(max(order_purchase_timestamp), min(order_purchase_timestamp),DAY) AS days_to_second_order
    FROM customer_order_sequence
    WHERE order_sequence <= 2
    GROUP BY customer_id
""")

# DATA LOADING - Dataset B: Current one-time-new customers, still within the return window
one_time_new_df = run_query("""
    SELECT
        mcb.customer_id,
        mcb.days_since_last_order
    FROM `olist-portfolio-491906.olist_dbt_marts.mart_customer_lifecycle` mcl 
    JOIN `olist-portfolio-491906.olist_dbt_marts.mart_customers_base` mcb 
        ON mcl.customer_id = mcb.customer_id
    WHERE mcl.lifecycle_stage = 'one_time_new'
""")

# DATA LOADING - Dataset C: Active customers for recovery priority matrix
# Include both one-time-new and repeat-active
one_time_nmv_df = run_query("""
    select 
        mcb.customer_id,
        mcl.recovery_priority_score,
        mcb.total_nmv
    FROM `olist-portfolio-491906.olist_dbt_marts.mart_customers_base` mcb 
    JOIN `olist-portfolio-491906.olist_dbt_marts.mart_customer_lifecycle` mcl 
        ON mcb.customer_id = mcl.customer_id
    WHERE mcl.lifecycle_stage = 'one_time_new'
""")
total_one_time_new = len(one_time_new_df)

# SECTION 1: CONTEXT BOX
median_days = int(repeat_interval_df['days_to_second_order'].median())
st.markdown(context_box(
    f"""The previous pages diagnosed <strong>what went wrong</strong> &mdash;
    failed deliveries, operational failures, silent churn. 
    This page answer a different question:
    <strong>Who are we about to lose, and how soon?</strong>
    <br><br>
    Among historical repeat customers, the median time to second purchase was
    <strong>{median_days} days</strong>. Currently,
    <strong>{total_one_time_new:,}</strong> one-time customers are still within
    the expected return window &mdash; each day that passes without a second purchase
    reduces their conversion probability.""",
    variant='success'
    ),unsafe_allow_html=True)

# SECTION 2: CONVERSION WINDOW
st.subheader("Conversion Window")
sorted_days = np.sort(repeat_interval_df['days_to_second_order'].values)

# Percentile milestones for the sidepanel
p50_days = int(np.percentile(sorted_days, 50))

pct_by_day60 = float((sorted_days <= 60).sum() / len(sorted_days) * 100)

campaign_buffer_days = 10
urgent_threshold = 60 - campaign_buffer_days # 50 days

safe_mask = one_time_new_df['days_since_last_order'] <= p50_days
warning_mask = (one_time_new_df['days_since_last_order'] > p50_days) & (one_time_new_df['days_since_last_order'] <= urgent_threshold)
urgent_mask = one_time_new_df['days_since_last_order'] > urgent_threshold
 

urgent_count = int(urgent_mask.sum())
safe_count = int(safe_mask.sum())
warning_count = int(warning_mask.sum())
col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure()

    # Three histogram traces — one per urgency zone.
    # Plotly renders them as a single continuous histogram because the
    # ranges don't overlap, but each zone gets its own color and legend entry.
    zone_config = [
        ('Safe', safe_mask, '#059669', 'rgba(5, 150, 105, 0.7)'),
        ('Warning', warning_mask, '#F59E0B', 'rgba(245, 158, 11, 0.7)'),
        ('Urgent', urgent_mask, '#DC2626', 'rgba(220, 38, 38, 0.7)')
    ]

    for zone_name, mask, color, fill_color in zone_config:
        subset = one_time_new_df[mask]
        if len(subset) > 0:
            fig.add_trace(go.Histogram(
                x=subset['days_since_last_order'],
                name=f'{zone_name} ({len(subset):,})',
                marker=dict(color=fill_color, line=dict(color='white', width=1)),
                xbins=dict(start=0, end=62, size=2),
                hovertemplate=f'{zone_name}<br>Day %{{x}}: %{{y}} customers<extra></extra>'
            ))

    # Reference line: P50 (median) — the empirical threshold
    fig.add_vline(
        x=p50_days, line_dash='dash', line_color='#1E293B', line_width=2,
        annotation_text=f'<b>Repeat Customers Median: {p50_days}days </b>',
        annotation_position='top left',
        annotation_font=dict(size=12, color='#1E293B', family='Inter, sans-serif')
    )

    # Reference line: Operational threshold — campaign execution deadline
    fig.add_vline(
        x=urgent_threshold, line_dash='dash', line_color='#DC2626', line_width=2,
        annotation_text=f'Urgent: {urgent_threshold}d',
        annotation_position='top right',
        annotation_font=dict(size=12, color='#DC2626', family='Inter, sans-serif')
    )

    fig.update_layout(
        title=dict(
            text='One-Time Customers: Where Are They in the Conversion Window?',
            font=dict(size=18, family='Inter, sans-serif', color='#111827'),
            x=0.5, xanchor='center'
        ),
        xaxis=dict(
            title='Days Since First Purchase',
            gridcolor='#F1F5F9',
            range=[-1, 63],
            dtick=5
        ),
        yaxis=dict(
            title='Number of Customers',
            gridcolor='#F1F5F9'
        ),
        barmode='stack',
        height=500,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Inter, sans-serif', size=12),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1, font=dict(size=11)
        )
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    from utils.styles import progress_bar

    urgency_bars = (
        progress_bar(f"Urgent (>{urgent_threshold} days)",
                     urgent_count / total_one_time_new * 100,
                     urgent_count, '#DC2626', unit='customers')
        + progress_bar(f"Warning ({p50_days}&ndash;{urgent_threshold} days)",
                       warning_count / total_one_time_new * 100,
                       warning_count, '#F59E0B', unit='customers')
        + progress_bar(f"Safe (&le;{p50_days} days)",
                       safe_count / total_one_time_new * 100,
                       safe_count, '#059669', unit='customers')
    )

    safe_pct = safe_count / total_one_time_new * 100
    actionable_count = urgent_count + warning_count

    st.markdown(analysis_sidepanel(
        context=(
            f"&bull; This chart maps where each one-time-new customer sits "
            f"in the conversion window based on repeat customer behavior. "
            f"<br>"
            f"&bull; Customers in the <b>Urgent zone</b> who do not return within "
            f"10 days will be reclassified as <b>one-time at-risk</b> "
            f"and transferred to the At-Risk Customers page."
        ),
        finding=(
            f"Safe zone accounts half "
            f"({safe_pct:.0f}%) of all one-time-new customers. "
            f"The remaining <strong>{actionable_count:,}</strong> "
            f"({100 - safe_pct:.0f}%) are actionable and need"
            f"to plan retention investment now."
        ),
        action=(
            f"<strong>Urgent ({urgent_count:,}):</strong> "
            f"Prioritize based on customer spend level to allocate "
            f"resources in emergent retention engagement "
            f"&mdash; see the Customer Value Map below."
        ),
        border_color='#DC2626',
        extra_sections=(
            f'<hr style="border:none; border-top:1px solid #E2E8F0; margin:15px 0;">'
            f'<h4 style="margin:0 0 12px 0; color:#1E293B; font-size:1rem;">Urgency Breakdown</h4>'
            f'{urgency_bars}'
        )
    ), unsafe_allow_html=True)

# SECTION 3: RECOVERY PRIORITY MATRIX
st.subheader("Customer Value Map")

# Reuse the same urgency zones from the histogram, now with NMV data.
one_time_enriched = one_time_new_df.merge(
    one_time_nmv_df[['customer_id', 'total_nmv']],
    on='customer_id', how='left'
)

# Assign zone labels
one_time_enriched['zone'] = 'Warning'
one_time_enriched.loc[
    one_time_enriched['days_since_last_order'] <= p50_days, 'zone'
] = 'Safe'
one_time_enriched.loc[
    one_time_enriched['days_since_last_order'] > urgent_threshold, 'zone'
] = 'Urgent'

# NMV bins — wider bins at higher values to handle right skew naturally.
# Last bin is open-ended: captures ALL premium customers without removal.
nmv_bins = [0, 50, 100, 200, 500, float('inf')]
nmv_labels = ['R$0-50', 'R$50-100', 'R$100-200', 'R$200-500', 'R$500+']
nmv_midpoints = [25, 75, 150, 350, 600]

one_time_enriched['nmv_bin'] = pd.cut(
    one_time_enriched['total_nmv'],
    bins=nmv_bins, labels=nmv_labels, right=False
)

# Aggregate: one row per zone × bin
bubble_df = one_time_enriched.groupby(['zone', 'nmv_bin'], observed=True).agg(
    customer_count=('customer_id', 'count'),
    total_rev=('total_nmv', 'sum'),
    median_nmv=('total_nmv', 'median')
).reset_index()

# Map bin labels to x positions and zone to y positions
bin_to_x = dict(zip(nmv_labels, nmv_midpoints))
bubble_df['x'] = bubble_df['nmv_bin'].astype(str).map(bin_to_x)

zone_to_y = {'Safe': 0, 'Warning': 1, 'Urgent': 2}
bubble_df['y'] = bubble_df['zone'].map(zone_to_y)

# Compute zone-level stats for the sidepanel
zone_stats = one_time_enriched.groupby('zone').agg(
    median_nmv=('total_nmv', 'median'),
    count=('customer_id', 'count'),
    total_rev=('total_nmv', 'sum')
).reindex(['Urgent', 'Warning', 'Safe'])

col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure()

    zone_colors = {
        'Safe': '#059669',
        'Warning': '#F59E0B',
        'Urgent': '#DC2626'
    }

    # Scale bubble sizes: largest bubble = 70px, smallest proportional
    max_count = bubble_df['customer_count'].max()

    for zone_name in ['Safe', 'Warning', 'Urgent']:
        zone_data = bubble_df[bubble_df['zone'] == zone_name]
        color = zone_colors[zone_name]

        fig.add_trace(go.Scatter(
            x=zone_data['x'],
            y=zone_data['y'],
            mode='markers+text',
            name=zone_name,
            marker=dict(
                size=zone_data['customer_count'],
                sizemode='area',
                sizeref=2 * max_count / (70 ** 2),
                sizemin=8,
                color=color,
                opacity=0.7,
                line=dict(color='white', width=2)
            ),
            text=zone_data['customer_count'].apply(lambda x: f'{x:,}'),
            textposition='middle center',
            textfont=dict(
                color='white', size=11, family='Inter, sans-serif'
            ),
            hovertemplate=(
                '<b>%{customdata[0]}</b> | %{customdata[1]}<br>'
                'Customers: %{customdata[2]:,}<br>'
                'Total Revenue: R$%{customdata[3]:,.0f}<br>'
                'Median NMV: R$%{customdata[4]:,.0f}'
                '<extra></extra>'
            ),
            customdata=list(zip(
                zone_data['zone'],
                zone_data['nmv_bin'].astype(str),
                zone_data['customer_count'],
                zone_data['total_rev'],
                zone_data['median_nmv']
            ))
        ))

    fig.update_layout(
        title=dict(
            text='Where Are High-Value Customers in the Conversion Window?',
            font=dict(size=18, family='Inter, sans-serif', color='#111827'),
            x=0.5, xanchor='center'
        ),
        xaxis=dict(
            title='Order Value',
            tickmode='array',
            tickvals=nmv_midpoints,
            ticktext=nmv_labels,
            gridcolor='#F1F5F9',
            zeroline=False
        ),
        yaxis=dict(
            title='',
            tickmode='array',
            tickvals=[0, 1, 2],
            ticktext=[
                f'Safe<br><span style="font-size:10px;color:#6B7280">(0\u2013{p50_days} days)</span>',
                f'Warning<br><span style="font-size:10px;color:#6B7280">({p50_days}\u2013{urgent_threshold} days)</span>',
                f'Urgent<br><span style="font-size:10px;color:#6B7280">({urgent_threshold}\u201360 days)</span>'
            ],
            gridcolor='#F1F5F9',
            zeroline=False
        ),
        height=450,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family='Inter, sans-serif', size=12),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown(analysis_sidepanel(
        context=(
            f"When retention budget is limited, two questions determine "
            f"where to invest: <strong>how soon</strong> will we lose them (y-axis) and "
            f"<strong>how much</strong> are they worth (x-axis)."
        ),
        finding=(
            f"The chart implicitly creates a priority diagonal: "
            f"<strong>top-right</strong> (most urgent + highest value) to "
            f"<strong>bottom-left</strong> (safest + lowest value)."
        ),
        action=(
            f"Use this matrix as the campaign targeting sequence "
            f"&mdash; allocate outreach resources along the diagonal "
            f"until budget is exhausted."
        ),
        border_color=COLORS['info']
    ), unsafe_allow_html=True)

# SECTION 4: NARRATIVE FOOTER
st.divider()

st.markdown(f"""
<div style="background-color:#F8FAFC; padding:16px 20px; border-radius:8px; border:1px solid #E2E8F0;">
<p style="margin:0 0 4px 0; font-size:0.8rem; color:#94A3B8; text-transform:uppercase; letter-spacing:0.05em;">
Dashboard Summary
</p>
<p style="margin:0; font-size:0.85rem; color:#64748B; line-height:1.7;">
<strong style="color:#DC2626;">Failed Acquisition</strong> identified orders that never reached customers. 
<strong style="color:#F59E0B;">At-Risk Customers</strong> separated fixable friction from silent churn. 
<strong style="color:#059669;">Proactive Retention</strong> quantified the conversion window 
and prioritized where re-engagement resources deliver the highest return.
</p>
</div>
""", unsafe_allow_html=True)
