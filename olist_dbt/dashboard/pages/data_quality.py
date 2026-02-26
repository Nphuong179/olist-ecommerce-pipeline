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
        'description': 'Orders missing their first payment. Payment sequence starts at 2',
        'severity': 'Error',
        'teams': 'Accounting, Engineering',
        'key': 'missing_initial_payment'
    },
    {   'id': 2,
        'finding': 'Invalid Payment Installment',
        'description': 'Credit card payments recorded with zero installments',
        'severity': 'Error',
        'teams': 'Accounting, Engineering',
        'key': 'zero_installment_credit_payment'
    },
    {   'id': 3,
        'finding': 'Delivery Before Carrier',
        'description': 'Customer received order before carrier picked it up - logically impossible',
        'severity': 'Warning',
        'teams': 'Logistics, Engineering',
        'key': 'delivery_precede_carrier'
    },
    {   'id': 4,
        'finding': 'Carrier Before Purchase',
        'description': 'Carrier timestamp precedes purchase timestamp',
        'severity': 'Warning',
        'teams': 'Logistics, Engineering',
        'key': 'carrier_precede_purchase'
    },
    {   'id': 5,
        'finding': 'Estimated Delivery Before Approval',
        'description': 'Estimated Delivery Timestamp precedes approval timestamp',
        'severity': 'Error',
        'teams': 'Engineering',
        'key': 'estimated_delivery_precede_approval'
    },
    {   'id': 6,
        'finding': 'Review Created Before Purchase',
        'description': 'Review created timestamp precedes purchase timestamp',
        'severity': 'Error',
        'teams': 'Customer Experience, Engineering',
        'key': 'review_precede_purchase'
    },
    {   'id': 7,
        'finding': 'Missing Delivery Timestamp',
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
    FROM dev.main_facts.fact_order_payments
    WHERE order_id IN (
        SELECT
            order_id
        FROM dev.main_facts.fact_order_payments
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
    FROM dev.main_facts.fact_order_payments WHERE order_id IN (
        SELECT order_id
        FROM dev.main_facts.fact_order_payments
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
    FROM dev.main_facts.fact_orders where hours_in_transit < 0
""")

carrier_precede_purchase_df = run_query("""
    SELECT 
        order_id,
        order_status,
        order_purchase_timestamp,
        order_delivered_carrier_timestamp,
        hours_to_carrier 
    FROM dev.main_facts.fact_orders 
    WHERE hours_to_carrier < 0
""")

estimated_delivery_precede_approval_df = run_query("""
    SELECT 
        order_id,
        order_status,
        order_approved_timestamp,
        order_estimated_delivery_date
    FROM dev.main_facts.fact_orders 
    WHERE order_estimated_delivery_date < order_approved_timestamp
""")

review_precede_purchase_df = run_query("""
    SELECT 
        fore.order_id,
        dc.customer_id,
        fore.review_created_timestamp,
        fo.order_purchase_timestamp
    FROM dev.main_facts.fact_orders fo
    JOIN dev.main_facts.fact_order_reviews fore
        ON fo.order_id = fore.order_id
    JOIN dev.main_dims.dim_customers dc 
        ON fo.customer_key = dc.customer_key
    WHERE DATE_DIFF('day',fo.order_purchase_timestamp, fore.review_created_timestamp) < 0
""")

missing_delivery_timestamp_df = run_query("""
    SELECT
        order_id,
        order_status,
        order_purchase_timestamp,
        order_delivered_carrier_timestamp,
        order_delivered_customer_timestamp 
    FROM dev.main_facts.fact_orders
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
    'description': 'Description',
    'severity': 'Severity',
    'teams': 'Impacted Teams'
})
st.subheader('Data Issues Summary')
st.dataframe(findings_metadata_df, hide_index=True)

# TABS
tab_timestamp, tab_missing, tab_business = st.tabs([
    'Timestamp Integrity (4)',
    'Missing Records (2)',
    'Business Rule Violation (1)'
])

with tab_timestamp:
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
        mime="text/csv"
    )
    st.dataframe(delivery_precede_carrier_df, hide_index=True)

    st.markdown(context_box(
        f"""<strong>Finding 4: Carrier Before Purchase</strong>
        &mdash; {len(carrier_precede_purchase_df)} orders.
        Carrier handoff before customer place the order &mdash; logically impossible.
        <br>
        <strong>Impacted teams:</strong> Logistics, Engineering""",
        variant="warning"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=carrier_precede_purchase_df.to_csv(index=False),
        file_name="carrier_before_purchase.csv",
        mime="text/csv"
    )
    st.dataframe(carrier_precede_purchase_df, hide_index=True)

    st.markdown(context_box(
        f"""<strong>Finding 5: Estimated Delivery Before Approval</strong>
        &mdash; {len(estimated_delivery_precede_approval_df)} orders.
        The order should be delivered before payment approval &mdash; logically impossible.
        <br>
        <strong>Impacted teams:</strong> Engineering""",
        variant="failure"
    ), unsafe_allow_html=True)
    st.download_button(
        label="Export to CSV",
        data=estimated_delivery_precede_approval_df.to_csv(index=False),
        file_name="estimated_delivery_before_approval.csv",
        mime="text/csv"
    )
    st.dataframe(estimated_delivery_precede_approval_df, hide_index=True)