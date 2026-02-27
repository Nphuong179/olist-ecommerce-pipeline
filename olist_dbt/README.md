# Olist E-Commerce Data Warehouse

A complete ELT data pipeline demonstrating dimensional modeling, data quality testing, and analytics engineering best practices using dbt and DuckDB.

## 🎯 Project Overview

This project transforms raw Brazilian e-commerce data (Olist dataset) into a production-ready data warehouse following Kimball dimensional modeling methodology. The pipeline implements a three-layer architecture (staging → dimensional → fact) with comprehensive data quality testing and documentation.

**Key Highlights:**
- 99,000+ orders across 3 years of marketplace transactions
- Type 2 Slowly Changing Dimensions tracking customer and seller address history
- 8 documented data quality findings with business impact analysis
- 180 automated data quality tests achieving 85% pass rate

## 🛠️ Technology Stack

- **Transformation:** dbt (data build tool)
- **Database:** DuckDB (embedded analytical database)
- **Testing:** dbt_utils package for advanced data quality validation
- **Version Control:** Git/GitHub
- **Language:** SQL

## 📊 Data Architecture
```
staging/          # Data cleaning and standardization (8 models)
  ├── stg_customers
  ├── stg_orders
  ├── stg_order_items
  ├── stg_order_payments
  └── ...

dimensional/      # Type 2 SCD dimensions (3 models)
  ├── dim_customers      # Customer address history
  ├── dim_products       # Product attributes and metrics
  └── dim_sellers        # Seller address history

facts/           # Transactional fact tables (4 models)
  ├── fact_orders
  ├── fact_order_items
  ├── fact_order_payments
  └── fact_order_reviews
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- pip (Python package manager)


## 📈 Key Findings

Comprehensive data quality analysis uncovered 8 critical issues documented in [`docs/DATA_QUALITY_FINDINGS.md`](docs/DATA_QUALITY_FINDINGS.md):

1. **Missing Payment Transactions** - 83 orders missing initial payment records
2. **Invalid Timestamp Sequences** - 100+ orders with logistics timestamp errors
3. **Stock-Out Orders Not Canceled** - 8 customers charged for unavailable products (critical business impact)
4. And 5 additional findings...

These findings demonstrate real-world data quality challenges and their business impacts on revenue recognition, customer experience, and operational metrics.

## 📁 Project Structure
```
olist-elt-pipeline/
├── olist_dbt/              # dbt project
│   ├── models/
│   │   ├── staging/
│   │   ├── dimensional/
│   │   └── facts/
│   ├── tests/
│   └── dbt_project.yml
├── data/                   # Raw CSV files
├── docs/                   # Documentation
│   └── DATA_QUALITY_FINDINGS.md
├── scripts/               # Data loading scripts
├── dev.duckdb            # DuckDB database file
└── README.md
```

## 🎓 Learning Outcomes

This project demonstrates proficiency in:
- **Dimensional Modeling:** Kimball methodology with Type 2 SCDs
- **Data Quality Engineering:** Comprehensive testing framework with dbt_utils
- **Business Analysis:** Translating data issues into business impact
- **SQL Proficiency:** Complex transformations, window functions, CTEs
- **Analytics Engineering:** Modern data stack patterns and best practices

## 📝 Dataset Information

**Source:** [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

**Coverage:** 
- 99,441 orders from 2016-2018
- 32,951 products across 73 categories
- 3,095 sellers operating across Brazil
- 100,000+ customer records

## 🤝 Contact

**Your Name**  
📧 your.email@example.com  
💼 [LinkedIn](https://linkedin.com/in/yourprofile)  
🐙 [GitHub](https://github.com/yourusername)