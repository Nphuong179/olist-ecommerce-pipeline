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
│   │   │   ├── dim_customers.sql
│   │   │   ├── dim_sellers.sql
│   │   │   ├── dim_products.sql
│   │   │   └── dim_schema.yml
│   │   │
│   │   ├── facts/                         # Layer 3: Transactional facts
│   │   │   ├── fact_orders.sql
│   │   │   ├── fact_order_items.sql
│   │   │   ├── fact_order_payments.sql
│   │   │   ├── fact_order_reviews.sql
│   │   │   └── fact_schema.yml
│   │   │
│   │   └── marts/customers/               # Layer 4: Business analytics
│   │       ├── mart_customers_base.sql
│   │       ├── mart_customer_lifecycle.sql
│   │       ├── mart_customer_value_growth.sql
│   │       └── mart_customer_payment.sql
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

The pipeline follows **Kimball dimensional modeling** with four layers:

- **Staging (8 models)** - Type casting, renaming, null handling. No business logic.
- **Dimensions (3 models)** - Type 2 SCDs for customers and sellers (address history with validity periods), plus a product dimension with price metrics.
- **Facts (4 models)** - Order, item, payment, and review grains. All joined to dimensions via surrogate keys with point-in-time matching.
- **Marts (4 models)** - 30+ aggregated customer metrics feeding lifecycle classification, issue flagging, and payment segmentation.

## Dashboard

Five-page Streamlit + Plotly dashboard structured as a guided analytical narrative - see demo below.

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