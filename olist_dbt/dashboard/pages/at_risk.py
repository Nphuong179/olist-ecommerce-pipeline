import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from matplotlib_venn import venn3
from matplotlib.patches import Circle
from utils.db_connection import run_query
from utils.styles import (COLORS, context_box, analysis_sidepanel, progress_bar, page_navigation_footer, chart_instruction_box)

st.title("AT-RISK CUSTOMERS")

# EXTRACT DATA
at_risk_customer_df = run_query("""
    SELECT
        customer_id,
        lifecycle_stage,
        has_satisfaction_issue AS has_quality_issues,
        (has_delivery_issue OR has_stockout_issue) AS has_operational_issues,
        (has_promo_dependency OR has_freight_burden) AS has_economic_issues,
        total_issues
    FROM `olist-portfolio-491906.olist_dbt_marts.mart_customer_value_growth`
    WHERE lifecycle_stage LIKE '%_at_risk'
""")

total_at_risk = len(at_risk_customer_df)
silent_churn_df = at_risk_customer_df[at_risk_customer_df['total_issues'] == 0]
silent_churn_count = len(silent_churn_df)
identifiable_df = at_risk_customer_df[at_risk_customer_df['total_issues'] > 0]
identifiable_count = len(identifiable_df)
pct_silent_churn = silent_churn_count / total_at_risk * 100
pct_identifiable = identifiable_count / total_at_risk * 100

quality_issues = set(identifiable_df[identifiable_df['has_quality_issues']]['customer_id'])
operational_issues = set(identifiable_df[identifiable_df['has_operational_issues']]['customer_id'])
economic_issues = set(identifiable_df[identifiable_df['has_economic_issues']]['customer_id'])

# Co-occurrence calculations for the insight panel
quality_and_operational = quality_issues & operational_issues
quality_and_economic = quality_issues & economic_issues
operational_and_economic = operational_issues & economic_issues
all_three = quality_issues & operational_issues & economic_issues
any_overlap = quality_and_operational | quality_and_economic | operational_and_economic
overlap_pct = len(any_overlap) / identifiable_count * 100 if identifiable_count > 0 else 0

# SECTION 1: CONTEXT BOX
st.markdown(context_box(
    f"""Among <strong>{total_at_risk:,}</strong> at-risk customers (those overdue for their next purchase), 
    <strong>{identifiable_count:,} ({pct_identifiable:.1f}%)</strong> have at least one identifiable friction point 
    in their data &mdash; a concrete signal we can investigate and act on.
    <br><br>
    The remaining <strong>{silent_churn_count:,} ({pct_silent_churn:.1f}%)</strong> had successful deliveries 
    with no obvious complaints &mdash; <strong>silent churn</strong> with no clear intervention strategy.""",
    variant="warning"
), unsafe_allow_html=True)

# SECTION 2: VENN DIAGRAM - VISUALIZATION
fig = plt.figure(figsize=(14, 8), facecolor='white')
ax = fig.add_axes([0.02, 0.05, 0.96, 0.9])

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

# Color mapping — consistent with our semantic system
# Quality = amber (warning/experience), Operational = blue, Economic = lighter blue
venn.get_patch_by_id('100').set_color('#FBBF24')   # Quality only — amber
venn.get_patch_by_id('010').set_color('#93C5FD')   # Operational only — blue
venn.get_patch_by_id('001').set_color('#A7F3D0')   # Economic only — green-tint
venn.get_patch_by_id('110').set_color('#DDA5E8')   # Quality + Operational
venn.get_patch_by_id('101').set_color('#FDE68A')   # Quality + Economic
venn.get_patch_by_id('011').set_color('#BAE6FD')   # Operational + Economic
venn.get_patch_by_id('111').set_color('#E5D5F0')   # All three

for text in venn.set_labels:
    text.set_fontsize(13)
    text.set_weight('bold')
    text.set_color('#1F2937')

for text in venn.subset_labels:
    if text:
        text.set_fontsize(12)
        text.set_weight('bold')
        text.set_color('#374151')

# Silent churn circle (separate from the Venn)
silent_circle = Circle(xy=(1.7, 0), radius=0.75,
                        facecolor='#E5E7EB', edgecolor='none', alpha=0.9)
ax.add_patch(silent_circle)

ax.text(1.7, 0.5, '?', ha='center', va='center', fontsize=60, alpha=0.6,
        bbox=dict(boxstyle='circle', facecolor='#9CA3AF', alpha=0.3, edgecolor='none'))
ax.text(1.7, -0.05, f'{silent_churn_count:,} customers\n({pct_silent_churn:.1f}%)',
        ha='center', va='center', fontsize=13, weight='bold', color='#1F2937')
ax.text(1.7, -0.6, 'Silent Churn', ha='center', va='center',
        fontsize=14, weight='bold', color='#374151')
ax.text(1.7, -0.85, 'No identifiable data signals', ha='center', va='center',
        fontsize=10, style='italic', color='#6B7280')

fig.text(0.5, 0.97, f'Customer Issue Analysis: {total_at_risk:,} At-Risk Customers',
            ha='center', fontsize=16, weight='bold', color='#111827')
fig.text(0.5, 0.93, f'Identifiable Issues ({pct_identifiable:.1f}%) vs. Silent Churn ({pct_silent_churn:.1f}%)',
            ha='center', fontsize=12, color='#4B5563')

ax.set_xlim(-1.6, 2.8)
ax.set_ylim(-1.3, 1.3)
ax.axis('off')
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
st.pyplot(fig, use_container_width=True)

# SECTION 3: TABBED DEEP DIVES
tab_operational, tab_quality, tab_economic = st.tabs([
    f"Operational Failures ({len(operational_issues):,})",
    f"Quality/Experience ({len(quality_issues):,})",
    f"Economic Barriers ({len(economic_issues):,})"
])
# TAB 1: OPERATIONAL FAILURES
# OPERATIONAL FAILURES - LOAD DATA
with tab_operational:
    operational_failures_df = run_query("""
        WITH operational_orders AS (
            SELECT
                fo.order_id,
                fo.order_status,
                LOGICAL_AND(foi.met_shipping_deadline) AS all_met_shipping_deadline
            FROM `olist-portfolio-491906.olist_dbt_dims.dim_customers` dc
            LEFT JOIN `olist-portfolio-491906.olist_dbt_marts.mart_customer_value_growth` mcvg
                ON dc.customer_id = mcvg.customer_id
            JOIN `olist-portfolio-491906.olist_dbt_facts.fact_orders` fo
                ON dc.customer_key = fo.customer_key
            LEFT JOIN `olist-portfolio-491906.olist_dbt_facts.fact_order_items` foi
                ON fo.order_id = foi.order_id
            WHERE (mcvg.has_delivery_issue = TRUE OR mcvg.has_stockout_issue = TRUE)
                AND (fo.delivered_on_time = FALSE OR fo.order_status = 'unavailable') 
                AND fo.order_status IN ('delivered', 'unavailable')
                AND mcvg.lifecycle_stage LIKE '%_at_risk'
            GROUP BY fo.order_id, fo.order_status)
        SELECT
            SUM(CASE WHEN order_status = 'unavailable' THEN 1 ELSE 0 END) AS unavailable_orders,
            SUM(CASE WHEN all_met_shipping_deadline = TRUE THEN 1 ELSE 0 END) AS late_transit_orders,
            COUNT(*) AS total_orders
        FROM operational_orders
    """)

    unavailable_orders = int(operational_failures_df['unavailable_orders'].iloc[0])
    late_transit_orders = int(operational_failures_df['late_transit_orders'].iloc[0])
    total_op_orders = int(operational_failures_df['total_orders'].iloc[0])
    late_shipping_orders = total_op_orders - unavailable_orders - late_transit_orders

    seller_accountability = unavailable_orders + late_shipping_orders
    logistics_accountability = late_transit_orders

# OPERATIONAL FAILURES - VISUALIZE
    col1, col2 = st.columns([2, 1])

    with col1:
        labels = [
            f"Operational Failures<br>{total_op_orders:,} orders",
            f"Unavailable<br>{unavailable_orders:,} orders",
            f"Late Delivery<br>{late_shipping_orders + late_transit_orders:,} orders",
            f"Seller Accountability<br>{seller_accountability:,} orders<br>({seller_accountability/total_op_orders*100:.1f}%)",
            f"Logistics Accountability<br>{logistics_accountability:,} orders<br>({logistics_accountability/total_op_orders*100:.1f}%)"
        ]
        sources = [0, 0, 1, 2, 2]
        targets = [1, 2, 3, 3, 4]
        values = [
            unavailable_orders, 
            late_shipping_orders + late_transit_orders,
            unavailable_orders, 
            late_shipping_orders, 
            late_transit_orders
        ]

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=20, thickness=25,
                line=dict(color='white', width=2),
                label=labels,
                color=[COLORS["neutral"], COLORS["failure"], '#3B82F6',
                       COLORS["seller"], COLORS["logistics"]]
            ),
            link=dict(
                source=sources, target=targets, value=values,
                color=[
                    'rgba(220, 38, 38, 0.5)',
                    'rgba(59, 130, 246, 0.5)',
                    'rgba(220, 38, 38, 0.6)',
                    'rgba(220, 38, 38, 0.4)',
                    'rgba(29, 78, 216, 0.6)'
                ]
            ),
            textfont=dict(color='white', size=13, family='Inter, sans-serif'),
            hoverinfo='skip'
        )])

        fig.update_layout(
            title=dict(
                text="Operational Failures: Order-Level Accountability",
                font=dict(size=18, family="Inter, sans-serif", color='#111827'),
                x=0.5, xanchor='center'
            ),
            font=dict(size=12, family="Inter, sans-serif", color='#111827'),
            height=500, margin=dict(l=20, r=20, t=60, b=20),
            paper_bgcolor='white', plot_bgcolor='white'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        seller_pct = seller_accountability / total_op_orders * 100
        logistics_pct = logistics_accountability / total_op_orders * 100

        bars_html = (
            progress_bar("Seller Responsibility", seller_pct, seller_accountability, COLORS["seller"])
            + progress_bar("Logistics Responsibility", logistics_pct, logistics_accountability, COLORS["logistics"])
        )

        st.markdown(analysis_sidepanel(
            context=(
                "The chart separates operational failures into <strong>seller accountability</strong> "
                "(missed shipping deadlines, stockouts) vs. <strong>logistics accountability</strong> "
                "(delays after carrier handoff)."
            ),
            finding="",
            action=(
                f"<strong>Logistics ({logistics_pct:.0f}%):</strong> Escalate late-transit "
                f"and lost-package patterns to the Logistics team for carrier performance review."
                f"<br><br>"
                f"<strong>Seller ({seller_pct:.0f}%):</strong> Identify sellers with repeated "
                f"shipping deadline misses and stockouts. Enforce fulfillment SLAs "
                f"through penalties or suspension."
            ),
            border_color=COLORS["logistics"],
            extra_sections=bars_html
        ), unsafe_allow_html=True)

# TAB 2: QUALITY ISSUES
# QUALITY ISSUES - LOAD DATA
with tab_quality:
    low_review_df = run_query("""
        WITH quality_reviews AS (
            SELECT
                forv.review_id,
                forv.is_rating_only,
                mcvg.customer_id,
                forv.review_score
            FROM `olist-portfolio-491906.olist_dbt_facts.fact_order_reviews` forv
            JOIN `olist-portfolio-491906.olist_dbt_facts.fact_orders` fo 
                ON forv.order_id = fo.order_id 
            JOIN `olist-portfolio-491906.olist_dbt_dims.dim_customers` dc 
                ON fo.customer_key = dc.customer_key 
            JOIN `olist-portfolio-491906.olist_dbt_marts.mart_customer_value_growth` mcvg 
                ON dc.customer_id = mcvg.customer_id 
            WHERE mcvg.lifecycle_stage LIKE '%_at_risk'
                AND forv.review_score <= 3
                AND mcvg.has_satisfaction_issue = TRUE)
        SELECT 
            review_score,
            SUM(CASE WHEN is_rating_only = FALSE THEN 1 ELSE 0 END) AS with_content,
            SUM(CASE WHEN is_rating_only = TRUE THEN 1 ELSE 0 END) AS without_content,
            COUNT(*) AS total_reviews
        FROM quality_reviews
        GROUP BY review_score
    """)
    total_low_reviews = low_review_df['total_reviews'].sum()
    with_content_total = low_review_df['with_content'].sum()
    without_content_total = low_review_df['without_content'].sum()

    # POOR EXPERIENCE - VISUALIZE
    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure()

        # "With content" bars — darker, investigable
        fig.add_trace(go.Bar(
            name='With Review Content',
            x=low_review_df['review_score'],
            y=low_review_df['with_content'],
            marker=dict(
                color=[COLORS["failure"], COLORS["warning"], '#FCD34D'],
                line=dict(color='white', width=2)
            ),
            text=low_review_df['with_content'],
            texttemplate='%{text:,}',
            textposition='inside',
            hovertemplate='<b>%{x}-Star with message: %{y:,}</b><extra></extra>'
        ))
        
        # "Rating only" bars — lighter, not investigable
        fig.add_trace(go.Bar(
            name='Rating Only (No Content)',
            x=low_review_df['review_score'],
            y=low_review_df['without_content'],
            marker=dict(
                color=['#FEE2E2', '#FED7AA', '#FEF3C7'],
                line=dict(color='white', width=2)
            ),
            text=low_review_df['without_content'],
            texttemplate='%{text:,}',
            textposition='inside',
            hovertemplate='<b>%{x}-Star rating only: %{y:,}</b><extra></extra>'
        ))

        fig.update_layout(
            title=dict(
                text="Review Score Distribution: Investigability & Recovery Priority",
                font=dict(size=18, family="Inter, sans-serif", color='#111827'),
                x=0.5, xanchor='center'
            ),
            barmode='stack',
            xaxis=dict(
                title="Review Score",
                tickmode='array', tickvals=[1, 2, 3],
                ticktext=['1-Star<br>(Extremely<br>Dissatisfied)',
                          '2-Star<br>(Very<br>Dissatisfied)',
                          '3-Star<br>(Moderately<br>Dissatisfied)']
            ),
            yaxis=dict(title="Number of Reviews"),
            height=500, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=dict(size=12, family="Inter, sans-serif"),
            plot_bgcolor='white', paper_bgcolor='white'
        )

        # Annotation highlighting recovery priority
        three_star_with = low_review_df[low_review_df['review_score'] == 3]['with_content'].values
        if len(three_star_with) > 0:
            fig.add_annotation(
                x=3, y=three_star_with[0] / 2,
                text="Highest<br>Recovery<br>Priority",
                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2,
                arrowcolor=COLORS["success"], ax=50, ay=-50,
                font=dict(size=11, color=COLORS["success"], family="Inter, sans-serif"),
                bgcolor="rgba(5, 150, 105, 0.1)",
                bordercolor=COLORS["success"], borderwidth=2
            )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        pct_with = with_content_total / total_low_reviews * 100 if total_low_reviews > 0 else 0
        pct_without = 100 - pct_with

        bars_html = (
            progress_bar("With Content (Investigable)", pct_with, int(with_content_total), COLORS["success"])
            + progress_bar("Rating Only (No Signal)", pct_without, int(without_content_total), COLORS["neutral"])
        )

        st.markdown(analysis_sidepanel(
            context=(
                "The chart separates reviews "
                "<strong>with written content</strong> (analyzable for root causes) from "
                "<strong>rating-only</strong> (no diagnostic signal), "
                "quantifying how much material the Data Science team has to work with."
            ),
            finding="",
            action=(
                f"<strong>Recommended:</strong> Coordinate with Data Science team "
                f"for Portuguese text analysis on the {int(with_content_total):,} reviews "
                f"with content to categorize complaint themes before presenting "
                f"findings to Product and Operations."
            ),
            border_color=COLORS["warning"],
            extra_sections=bars_html
        ), unsafe_allow_html=True)

# TAB 3: ECONOMIC BARRIER 
# ECONOMIC BARRIER - PROMO DEPENDENCY - LOAD DATA
with tab_economic:
    st.markdown(chart_instruction_box(
        "Click any segment to zoom into that customer group. "
        "Click the <strong>center circle</strong> to zoom back out."
    ), unsafe_allow_html=True)
    
    promo_dependent_df = run_query("""
        WITH avg_nmv_percentiles AS (
            SELECT p50, p75, p95 FROM 
                (
                SELECT
                    PERCENTILE_CONT(avg_nmv_per_order, 0.5) OVER() AS p50,
                    PERCENTILE_CONT(avg_nmv_per_order, 0.75) OVER() AS p75,
                    PERCENTILE_CONT(avg_nmv_per_order, 0.95) OVER() AS p95 
                FROM `olist-portfolio-491906.olist_dbt_marts.mart_customer_value_growth`
                WHERE lifecycle_stage LIKE '%_at_risk'
                    AND has_promo_dependency = TRUE
                )
            LIMIT 1)
        SELECT 
            CASE
                WHEN avg_nmv_per_order < p50 THEN 'Standard'
                WHEN avg_nmv_per_order < p75 THEN 'Silver'
                WHEN avg_nmv_per_order < p95 THEN 'Gold'
                ELSE 'Premium'
            END AS avg_nmv_tier,
            COUNT(*) AS total_customers,
            ROUND(MIN(avg_nmv_per_order), 1) AS min_nmv,
            ROUND(MAX(avg_nmv_per_order), 1) AS max_nmv,
            ROUND(AVG(avg_nmv_per_order), 1) AS avg_nmv_in_tier
        FROM `olist-portfolio-491906.olist_dbt_marts.mart_customer_value_growth`
        CROSS JOIN avg_nmv_percentiles
        WHERE lifecycle_stage LIKE '%_at_risk'
            AND has_promo_dependency = TRUE
        GROUP BY avg_nmv_tier
    """)

    tier_colors = {
        'Standard': '#BFDBFE',
        'Silver':   '#60A5FA',
        'Gold':     '#2563EB',
        'Premium':  '#1E3A8A'
    }
    
    tier_strategies = {
        'Standard': 'Generic category voucher (5-10% discount)',
        'Silver':   'Targeted discount (10-15% off)',
        'Gold':     'Personalized offer (15% off + free shipping)',
        'Premium':  'Personal outreach + exclusive benefits'
    }

    total_promo_customers = int(promo_dependent_df['total_customers'].sum())
    promo_dependent_df['customer_pct'] = (promo_dependent_df['total_customers']/ total_promo_customers * 100).round(1)
    promo_dependent_df['tier_color'] = promo_dependent_df['avg_nmv_tier'].map(tier_colors)
    promo_dependent_df['tier_strategy'] = promo_dependent_df['avg_nmv_tier'].map(tier_strategies)

    promo_dependent_df['label'] = promo_dependent_df.apply(lambda r:
        f"<b>• {r['avg_nmv_tier']}</b>: {int(r['total_customers']):,} customers ({r['customer_pct']:.0f}%)<br>"
        f"<b>• Range</b>: R${r['min_nmv']:,.0f} - R${r['max_nmv']:,.0f}<br>"
        f"<b>• Recommended Offer</b>: {r['tier_strategy']}", axis=1
    )

# PROMO DEPENDENCY - VISUALIZE
    col1, col2 = st.columns([2, 1])

    with col1:
        fig = go.Figure(go.Treemap(
            labels=promo_dependent_df['label'],
            parents=[''] * len(promo_dependent_df),
            values=promo_dependent_df['total_customers'],
            marker=dict(
                colors=promo_dependent_df['tier_color'].tolist(),
                line=dict(color='white', width=4)
            ),
            textfont=dict(color='white', size=17, family='Inter, sans-serif'),
            textposition='middle left',
            hoverinfo='skip'
        ))

        fig.update_layout(
            title=dict(
                text='Promo-Dependent At-Risk Customers: Value Tier Segmentation',
                font=dict(size=18, family='Inter, sans-serif', color='#111827'),
                x=0.5, xanchor='center'
            ),
            height=500,
            margin=dict(l=10, r=10, t=60, b=10),
            paper_bgcolor='white'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        premium_rows = promo_dependent_df[promo_dependent_df['avg_nmv_tier'] == 'Premium']
        standard_rows = promo_dependent_df[promo_dependent_df['avg_nmv_tier'] == 'Standard']

        if not premium_rows.empty and not standard_rows.empty:
            premium_max = premium_rows.iloc[0]['max_nmv']
            standard_min = standard_rows.iloc[0]['min_nmv']
            ratio = round(premium_max / standard_min) if standard_min > 0 else 0
        else:
            premium_max = 0
            standard_min = 0
            ratio = 0

        # Build tier value range display
        tier_order = ['Standard', 'Silver', 'Gold', 'Premium']
        range_html = """<hr style="border:none; border-top:1px solid #E2E8F0; margin:15px 0;">
            <h4 style="margin:0 0 12px 0; color:#1E293B; font-size:1rem;">Tier Value Ranges</h4>"""

        for tier in tier_order:
            row = promo_dependent_df[promo_dependent_df['avg_nmv_tier'] == tier]
            if not row.empty:
                r = row.iloc[0]
                color = tier_colors.get(tier, '#64748B')
                text_color = '#1E3A8A' if tier == 'Standard' else 'white'
                range_html += (
                    f'<p style="margin:0 0 8px 0; font-size:0.85rem; color:#475569;">'
                    f'<strong style="color:{text_color}; background:{color}; padding:1px 6px; '
                    f'border-radius:3px;">{tier}</strong> '
                    f'R${r["min_nmv"]:,.0f} &ndash; R${r["max_nmv"]:,.0f} '
                    f'<span style="color:#94A3B8;">({int(r["total_customers"]):,} customers)</span>'
                    f'</p>'
                )

        st.markdown(analysis_sidepanel( 
            context=(
                "This segmentation groups promo-dependent customers into value tiers so that "
                "re-engagement campaigns can scale promotion investment "
                "proportionally &mdash; avoiding overspend on low-value "
                "customers or undervaluing high-value ones."
            ),
            finding="",
            action=(
                f"Present tier segmentation to Marketing team for discussion "
                f"on differentiated re-engagement campaigns per value tier."
            ),
            border_color=COLORS["economic"],
            extra_sections=range_html
        ), unsafe_allow_html=True)

# NAVIGATION FOOTER

one_time_new_count_df = run_query("""
    SELECT COUNT(DISTINCT customer_id) AS customer_count
    FROM `olist-portfolio-491906.olist_dbt_marts.mart_customer_lifecycle`
    WHERE lifecycle_stage = 'one_time_new'
""")
one_time_new_count = int(one_time_new_count_df['customer_count'].iloc[0])

st.divider()

col_footer_text, col_footer_link = st.columns([3, 1])

with col_footer_text:
    st.markdown(f"""
    <div>
        <p style="margin:0 0 4px 0; font-size:0.85rem; color:#059669; text-transform:uppercase; letter-spacing:0.05em; font-weight:700;">Next Step</p>
        <p style="margin:0 0 8px 0; font-size:0.95rem; color:#065F46; line-height:1.5;">
        There are {one_time_new_count:,} one-time new customers who need retention engagement before
        reclassifying as one-time at-risk.
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_footer_link:
    st.page_link(
        "pages/proactive_retention.py",
        label="Proactive Retention →"
    )
