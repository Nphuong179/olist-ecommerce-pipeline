# Olist E-Commerce Data Warehouse & Customer Analytics Dashboard

An end-to-end ELT pipeline transforming Brazilian e-commerce data into a dimensional data warehouse, paired with an interactive analytics dashboard that investigates a critical business problem: **why do over 94% of customers never return after their first purchase?**

Built with **dbt + DuckDB** for data transformations and **Streamlit + Plotly** for interactive visualization.

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Transformation | dbt (data build tool) | SQL-based modeling, testing, documentation |
| Database | DuckDB | Embedded analytical database, zero infrastructure |
| Dashboard | Streamlit + Plotly | Interactive visualization and analysis |
| Testing | dbt-utils | Advanced data quality validation (180 tests) |
| Version Control | Git / GitHub | Source control and portfolio publication |

## Project Architecture

```
olist_elt/
├── data/raw/                              # 9 source CSV files (Olist dataset)
├── docs/
│   └── DATA_QUALITY_FINDINGS.md           # 7 investigated data quality issues
├── scripts/
│   └── load_data.py                       # CSV → DuckDB ingestion
│
├── olist_dbt/
│   ├── models/
│   │   ├── staging/                       # Layer 1: Cleaning & standardization
│   │   ├── dims/                          # Layer 2: Dimensional models
│   │   │   ├── dim_customers.sql          # Type 2 SCD - address history
│   │   │   ├── dim_sellers.sql            # Type 2 SCD - address history
│   │   │   ├── dim_products.sql           # Product attributes & price metrics
│   │   │   └── dim_schema.yml
│   │   │
│   │   ├── facts/                         # Layer 3: Transactional facts
│   │   │   ├── fact_orders.sql            # Order-level aggregates
│   │   │   ├── fact_order_items.sql       # Item-level detail with shipping
│   │   │   ├── fact_order_payments.sql    # Payment transactions
│   │   │   ├── fact_order_reviews.sql     # Customer review behavior
│   │   │   └── fact_schema.yml
│   │   │
│   │   └── marts/customers/               # Layer 4: Business analytics
│   │       ├── mart_customers_base.sql    # 30+ aggregated customer metrics
│   │       ├── mart_customer_lifecycle.sql # Lifecycle stage classification
│   │       ├── mart_customer_value_growth.sql  # Issue flags & segments
│   │       └── mart_customer_payment.sql  # Payment behavior patterns
│   │
│   ├── dashboard/
│   │   ├── streamlit_app.py               # App entry point & navigation
│   │   ├── pages/
│   │   │   ├── overview.py                # Customer lifecycle distribution
│   │   │   ├── failed_acquisition.py      # Orders never delivered
│   │   │   ├── at_risk.py                 # Identifiable friction vs silent churn
│   │   │   ├── proactive_retention.py     # Conversion window & value targeting
│   │   │   └── data_quality.py            # Pipeline health monitoring
│   │   └── utils/
│   │       ├── db_connection.py           # DuckDB connection with caching
│   │       └── styles.py                  # Design system & reusable components
│   │
│   └── dbt_project.yml
│
└── README.md
```

## Data Architecture

The pipeline follows **Kimball dimensional modeling** methodology with four transformation layers:

### Staging Layer (8 models)

Standardizes raw source data: type casting, column renaming (e.g., `customer_unique_id` → `customer_id`), and null handling. No business logic - purely structural cleaning.

### Dimension Layer (3 models)

- **dim_customers** - Type 2 Slowly Changing Dimension tracking customer address changes over time. Each address version has `valid_from` / `valid_to` timestamps and an `is_current` flag, enabling point-in-time analysis of customer geography.
- **dim_sellers** - Type 2 SCD mirroring the customer pattern for seller address history.
- **dim_products** - Product attributes, physical dimensions, listing completeness flags, and historical price metrics including price variation classification.

### Fact Layer (4 models)

- **fact_orders** - Order-level grain.
- **fact_order_items** - Item-level grain. 
- **fact_order_payments** - Payment transaction grain.
- **fact_order_reviews** - Review-level grain.

All fact tables join to dimensions using **surrogate keys** with point-in-time validity matching, ensuring that each transaction references the correct dimensional record version.

### Mart Layer (4 customer models)

- **mart_customers_base** - Consolidates 30+ metrics per customer from all fact tables: order frequency, financial value, review behavior, payment preferences, shopping diversity, and fulfillment quality.
- **mart_customer_lifecycle** - Classifies each customer into lifecycle stages (new, at-risk, active, lapsed).
- **mart_customer_value_growth** - Flags five types of identifiable issues (satisfaction, delivery, stockout, promotion dependency, freight burden) and assigns actionable segments.
- **mart_customer_payment** - Segments customers by installment behavior, promotion sensitivity, and payment consistency.

## Dashboard

The dashboard is structured as a guided analytical narrative. Each page answers a specific business question and connects to the next:

### Analytics Section

**Overview** - Frames the customer lifecycle distribution. An interactive sunburst chart shows how 96,090 customers split across three action categories: Failed Acquisition, At-Risk, and Active & Growth.

**Failed Acquisition** - Traces every undelivered order to its responsible party (Platform, Seller, Logistics, or Customer) through an interactive icicle chart. Each accountability path includes investigation steps for the responsible team.

**At-Risk Customers** - Separates customers with identifiable issues from silent churn using a Venn diagram. Three tabbed deep dives analyze Operational Failures, Quality/Experience issues, and Economic Barriers.

**Proactive Retention** - Identifies customers still within the conversion window by analyzing the historical time distribution of second purchases among repeat customers.

### Data Quality Section

**Data Quality Monitor** - Dynamic pipeline health monitoring page designed for accounting and logistics teams. Surfaces 7 data quality issues detected through 180 dbt tests, with evidence tables queried directly from the database. Each finding includes affected records, impacted teams, and CSV export functionality for operational follow-up.

## Data Quality

The pipeline executes **180 dbt tests** across all layers. Seven data quality issues were investigated and documented in [`docs/DATA_QUALITY_FINDINGS.md`](docs/DATA_QUALITY_FINDINGS.md):

Each finding includes root cause analysis, business impact assessment, and recommended remediation steps.

### What I Have Learned

- **Kimball dimensional modelling** - four-layer architecture (staging -> demensional -> fact -> mart), understanding why each layer exists and what belongs where.
- **Type 2 Slowly Changing Dimensions with point-in-time joins** - tracking address history with validity periods, and correctly joining facts to the right dimension version using surrogate keys.
- **dbt as a transformation framework** - ref() for dependency management, schema YAML for combined documentation and testing, materialization strategies, and dbt_utils for advanced validation.
- **Strategic data quality testing** - tests with intentional severity levels and conditional WHERE clauses; investigating anomalies to root cause and documenting findings with business impact for responsible teams.
- **Designing dashboards around decisions, not descriptions** - every visualization should end with a concrete next step: which team should take action, what they look for. For example: the Failed Acquisition page doesn't just show orders got stuck, it traces each failure to the responsible team with specific investigation step.

## Dataset

This project uses the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), published on Kaggle. The dataset contains approximately 100,000 orders placed between September 2016 and August 2018 on the Olist marketplace, covering order status, pricing, payment, freight performance, customer location, product attributes, and customer reviews.

## Demo
<video src="https://github.com/user-attachments/assets/771501e6-ae06-48c6-a54b-8a4046c5f6cc" controls width="100%"></video>

## License

This project is built for educational and portfolio purposes using publicly available data.
    
