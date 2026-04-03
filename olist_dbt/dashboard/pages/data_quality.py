import pandas as pd
import streamlit as st
from utils.db_connection import run_query
from utils.styles import (COLORS, context_box)

st.title('DATA QUALITY MONITOR')
st.markdown(context_box(
    f"""<strong style="font-size:1.05rem;">
        Automated pipeline health checks across the Olist data warehouse
        </strong>
        <br><br>
        This report surfaces data quality issues detected through <strong>180 dbt tests</strong> executed across the pipeline.
        Findings below are grouped by issue type, each identifying the impacted teams responsible for investigation.""",
        variant='info'
), unsafe_allow_html=True)

# Findings Metadata Distionary
findings_metadata = [
    {   'id': 1,
        'finding': 'Missing Initial Payment',
        'finding_group': 'Missing Records',
        'description': 'Orders missing their first payment. Payment sequence starts at 2',
        'severity': 'Error',
        'teams': 'Accounting, Engineering',
        'key': 'missing_initial_payment'
    },
    {   'id': 2,
        'finding': 'Invalid Payment Installment',
        'finding_group': 'Business Rule Violation',
        'description': 'Credit card payments recorded with zero installments',
        'severity': 'Error',
        'teams': 'Accounting, Engineering',
        'key': 'zero_installment_credit_payment'
    },
    {   'id': 3,
        'finding': 'Delivery Before Carrier',
        'finding_group': 'Timestamp Integrity',
        'description': 'Customer received order before carrier picked it up - logically impossible',
        'severity': 'Warning',
        'teams': 'Logistics, Engineering',
        'key': 'delivery_precede_carrier'
    },
    {   'id': 4,
        'finding': 'Carrier Before Purchase',
        'finding_group': 'Timestamp Integrity',
        'description': 'Carrier timestamp precedes purchase timestamp',
        'severity': 'Warning',
        'teams': 'Logistics, Engineering',
        'key': 'carrier_precede_purchase'
    },
    {   'id': 5,
        'finding': 'Estimated Delivery Before Approval',
        'finding_group': 'Timestamp Integrity',
        'description': 'Estimated Delivery Timestamp precedes approval timestamp',
        'severity': 'Error',
        'teams': 'Engineering',
        'key': 'estimated_delivery_precede_approval'
    },
    {   'id': 6,
        'finding': 'Review Created Before Purchase',
        'finding_group': 'Timestamp Integrity',
        'description': 'Review created timestamp precedes purchase timestamp',
        'severity': 'Error',
        'teams': 'Customer Experience, Engineering',
        'key': 'review_precede_purchase'
    },
    {   'id': 7,
        'finding': 'Missing Delivery Timestamp',
        'finding_group': 'Missing Records',
        'description': 'Missing delivery timestamp for delivered orders',
        'severity': 'Error',
        'teams': 'Accounting, Engineering',
        'key': 'missing_delivery_timestamp'}
]

# EXTRACT DATA
missing_initial_payment_df = run_query("""
    SELECT 
        order_id,
        payment_transaction_number,
        payment_type,
        payment_value
    FROM `olist-portfolio-492209.olist_dbt_facts.fact_order_payments`
    WHERE order_id IN (
        SELECT
            order_id
        FROM `olist-portfolio-492209.olist_dbt_facts.fact_order_payments`
        GROUP BY order_id
        HAVING MIN(payment_transaction_number) <> 1)
    ORDER BY order_id ASC, payment_transaction_number ASC
""")

zero_installment_credit_payment_df = run_query("""
    SELECT 
        order_id,
        payment_type,
        payment_installments,
        payment_value
    FROM `olist-portfolio-492209.olist_dbt_facts.fact_order_payments` WHERE order_id IN (
        SELECT order_id
        FROM `olist-portfolio-492209.olist_dbt_facts.fact_order_payments`
        WHERE payment_type = 'credit_card'
            AND payment_installments < 1)
""")

delivery_precede_carrier_df = run_query("""
    SELECT 
        order_id,
        order_status,
        order_delivered_carrier_timestamp,
        order_delivered_customer_timestamp,
        hours_in_transit 
    FROM `olist-portfolio-492209.olist_dbt_facts.fact_orders` where hours_in_transit < 0
""")

carrier_precede_purchase_df = run_query("""
    SELECT 
        order_id,
        order_status,
        order_purchase_timestamp,
        order_delivered_carrier_timestamp,
        hours_to_carrier 
    FROM `olist-portfolio-492209.olist_dbt_facts.fact_orders`
    WHERE hours_to_carrier < 0
""")

estimated_delivery_precede_approval_df = run_query("""
    SELECT 
        order_id,
        order_status,
        order_approved_timestamp,
        order_estimated_delivery_date
    FROM `olist-portfolio-492209.olist_dbt_facts.fact_orders`
    WHERE order_estimated_delivery_date < order_approved_timestamp
""")

review_precede_purchase_df = run_query("""
    SELECT 
        fore.order_id,
        fore.review_id,
        fore.review_created_timestamp,
        fo.order_purchase_timestamp
    FROM `olist-portfolio-492209.olist_dbt_facts.fact_orders` fo
    JOIN `olist-portfolio-492209.olist_dbt_facts.fact_order_reviews` fore
        ON fo.order_id = fore.order_id
    WHERE TIMESTAMP_DIFF(fore.review_created_timestamp, fo.order_purchase_timestamp, DAY) < 0
""")

missing_delivery_timestamp_df = run_query("""
    SELECT
        order_id,
        order_status,
        order_purchase_timestamp,
        order_delivered_carrier_timestamp,
        order_delivered_customer_timestamp 
    FROM `olist-portfolio-492209.olist_dbt_facts.fact_orders`
    WHERE order_status = 'delivered'
        AND order_delivered_customer_timestamp IS NULL
""")

# Count Data
record_counts = {
    'missing_initial_payment': len(missing_initial_payment_df),
    'zero_installment_credit_payment': len(zero_installment_credit_payment_df),
    'delivery_precede_carrier': len(delivery_precede_carrier_df),
    'carrier_precede_purchase': len(carrier_precede_purchase_df),
    'estimated_delivery_precede_approval': len(estimated_delivery_precede_approval_df),
    'review_precede_purchase': len(review_precede_purchase_df),
    'missing_delivery_timestamp': len(missing_delivery_timestamp_df)
}

findings_metadata_df = pd.DataFrame(findings_metadata)
findings_metadata_df['Records'] = findings_metadata_df['key'].map(record_counts)
findings_metadata_df.drop(columns=['key'],inplace=True)
findings_metadata_df = findings_metadata_df.rename(columns={
    'id': '#',
    'finding': 'Finding',
    'finding_group': 'Finding Group',
    'description': 'Description',
    'severity': 'Severity',
    'teams': 'Impacted Teams'
})

def style_finding_group(val):
    styles_severity = {
        'Error':'color: #DC2626',
        'Warning': 'color: #F59E0B'
    }
    return styles_severity.get(val, '')

findings_metadata_df = findings_metadata_df.style.map(
    style_finding_group, subset=['Severity']
)

st.subheader('Data Issues Summary')
st.dataframe(findings_metadata_df, hide_index=True)

# TABS
tab_timestamp, tab_missing, tab_business = st.tabs([
    'Timestamp Integrity (4)',
    'Missing Records (2)',
    'Business Rule Violation (1)'
])

with tab_timestamp:
    # Finding 5: Estimated Before Approval
    st.markdown(context_box(
        f"""<strong>Finding 5: Estimated Delivery Before Approval</strong>
        &mdash; {len(estimated_delivery_precede_approval_df)} orders.
        Estimated delivery date already expired before payment was approved &mdash; promise was outdated at confirmation.
        <br>
        <strong>Impacted teams:</strong> Engineering""",
        variant="failure"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=estimated_delivery_precede_approval_df.to_csv(index=False),
        file_name="estimated_delivery_before_approval.csv",
        mime="text/csv",
        key="export_finding_5"
    )
    st.dataframe(estimated_delivery_precede_approval_df, hide_index=True)
    st.divider()

    # Finding 6: Review Before Purchase
    st.markdown(context_box(
        f"""<strong>Finding 6: Review Created Before Purchase</strong>
        &mdash; {len(review_precede_purchase_df)} orders.
        Review submission timestamp precedes order creation &mdash; logically impossible.
        <br>
        <strong>Impacted teams:</strong> Customer Experience, Engineering""",
        variant="failure"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=review_precede_purchase_df.to_csv(index=False),
        file_name="review_before_purchase.csv",
        mime="text/csv",
        key="export_finding_6"
    )
    st.dataframe(review_precede_purchase_df, hide_index=True)
    st.divider()

    # Finding 3: Delivery Before Carrier
    st.markdown(context_box(
        f"""<strong>Finding 3: Customer Delivery Before Carrier Handoff</strong>
        &mdash; {len(delivery_precede_carrier_df)} orders.
        Customer received order before carrier picked it up &mdash; logically impossible.
        <br>
        <strong>Impacted teams:</strong> Logistics, Engineering""",
        variant="warning"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=delivery_precede_carrier_df.to_csv(index=False),
        file_name="delivery_precede_carrier.csv",
        mime="text/csv",
        key="export_finding_3"
    )
    st.dataframe(delivery_precede_carrier_df, hide_index=True)
    st.divider()

    # Finding 4: Carrier Before Purchase
    st.markdown(context_box(
        f"""<strong>Finding 4: Carrier Before Purchase</strong>
        &mdash; {len(carrier_precede_purchase_df)} orders.
        Carrier handoff recorded before the order was placed &mdash; logically impossible.
        <br>
        <strong>Impacted teams:</strong> Logistics, Engineering""",
        variant="warning"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=carrier_precede_purchase_df.to_csv(index=False),
        file_name="carrier_before_purchase.csv",
        mime="text/csv",
        key="export_finding_4"
    )
    st.dataframe(carrier_precede_purchase_df, hide_index=True)

with tab_missing:
    # Finding 1: Missing Initial Payment
    st.markdown(context_box(
        f"""<strong>Finding 1: Missing Initial Payment</strong>
        &mdash; {len(missing_initial_payment_df)} orders.
        Orders missing the first payment transaction. Payment sequence start at 2.
        <br>
        <strong>Impacted teams:</strong> Accounting, Engineering""",
        variant="failure"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=missing_initial_payment_df.to_csv(index=False),
        file_name="missing_initial_payment.csv",
        mime="text/csv",
        key="export_finding_1"
    )
    st.dataframe(missing_initial_payment_df, hide_index=True)
    st.divider()

    # Finding 7: Missing Delivery Timestamp
    st.markdown(context_box(
        f"""<strong>Finding 7: Missing Delivery Timestamp</strong>
        &mdash; {len(missing_delivery_timestamp_df)} orders.
        Delivered orders missing delivery timestamp. Impossible to identify when the order was delivered.
        <br>
        <strong>Impacted teams:</strong> Accounting, Engineering""",
        variant="failure"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=missing_delivery_timestamp_df.to_csv(index=False),
        file_name="missing_delivery_timestamp.csv",
        mime="text/csv",
        key="export_finding_7"
    )
    st.dataframe(missing_delivery_timestamp_df, hide_index=True)

with tab_business:
    # Finding 2: Invalid Payment Installment 
    st.markdown(context_box(
        f"""<strong>Finding 2: Invalid Credit Payment Installment</strong>
        &mdash; {len(zero_installment_credit_payment_df)} orders.
        Credit card payments recorded with zero installments &mdash; logically impossible
        <br>
        <strong>Impacted teams:</strong> Accounting, Engineering""",
        variant="failure"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=zero_installment_credit_payment_df.to_csv(index=False),
        file_name="zero_installment_credit_payment.csv",
        mime="text/csv",
        key="export_finding_2"
    )
    st.dataframe(zero_installment_credit_payment_df, hide_index=True)