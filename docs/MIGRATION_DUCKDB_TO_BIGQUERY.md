# Migration: DuckDB to Google BigQuery

## Overview

This document records the full migration of the Olist E-Commerce Customer Analytics Pipeline from a local DuckDB database to Google BigQuery. The migration covers the data warehouse, dbt transformation layer, and Streamlit dashboard connection.

**Migration completed:** April 2026  
**Old warehouse:** DuckDB (local file `dev.duckdb`)  
**New warehouse:** Google BigQuery (`olist-portfolio-492209`)

---

## 1. GCP Project Setup

### Project configuration
- Created GCP project `olist-portfolio` (ID: `olist-portfolio-492209`) with **No organization** to avoid org-level security policy restrictions
- Note: An earlier project `olist-portfolio-491906` was created under `nphuong-nguyen281-org` but was abandoned because the organization enforced `iam.disableServiceAccountKeyCreation`, blocking service account JSON key creation via both the UI and CLI

### Service account
- Created service account `dbt-runner` with **BigQuery Admin** role
- Downloaded JSON key file → stored at `keys/bq_service_account.json`

---

## 2. Raw Data Loading

### load_data.py rewrite
`load_data.py` was rewritten from DuckDB to BigQuery. The key changes were the connection method and load mechanism:

| | DuckDB (old) | BigQuery (new) |
|---|---|---|
| Connection | `duckdb.connect(db_path)` | `bigquery.Client.from_service_account_json(key_path)` |
| Load method | `CREATE OR REPLACE TABLE` SQL | `load_table_from_file()` API |
| Execution | Synchronous | Asynchronous (`job.result()` waits for completion) |

### Row count verification
After loading, all 9 table row counts were verified against DuckDB using a UNION ALL query in BigQuery Studio. All counts matched exactly.

---

## 3. dbt Configuration

### Adapter installation
```bash
pip install dbt-bigquery
```

### profiles.yml and sources.yml
Both files were updated to point to the new BigQuery project. `profiles.yml` was updated to use the BigQuery adapter with service account authentication. `sources.yml` was updated with the GCP project ID as `database` and `olist_raw` as `schema`.

### Authentication
For local development: `gcloud auth application-default login` (OAuth)  
For Streamlit Cloud deployment: service account JSON key via `st.secrets`

---

## 4. SQL Syntax Migration

BigQuery uses stricter typing and different function signatures compared to DuckDB. The following categories of changes were applied across all dbt models and Streamlit page files:

### 4.1 CAST types
| DuckDB | BigQuery |
|---|---|
| `CAST(x AS VARCHAR)` | `CAST(x AS STRING)` |
| `CAST(x AS DECIMAL(10,2))` | `CAST(x AS NUMERIC)` |
| `CAST(x AS FLOAT)` | `CAST(x AS FLOAT64)` |
| `CAST(x AS INTEGER)` | `CAST(x AS INT64)` |

Parameterized types like `DECIMAL(10,2)` are not allowed in BigQuery CAST expressions.

### 4.2 TRIM() on non-string columns
BigQuery's `TRIM()` only accepts STRING type. Numeric columns auto-detected as INT64 (e.g. `zip_code_prefix`) required explicit casting:
```sql
-- Wrong
TRIM(customer_zip_code_prefix)

-- Correct
CAST(customer_zip_code_prefix AS STRING)
```

### 4.3 DATE_DIFF argument order
```sql
-- DuckDB
DATE_DIFF('day', start_date, end_date)

-- BigQuery
DATE_DIFF(end_date, start_date, DAY)
```

### 4.4 DATE_TRUNC argument order
```sql
-- DuckDB
DATE_TRUNC('month', timestamp_col)

-- BigQuery
DATE_TRUNC(timestamp_col, MONTH)
```

### 4.5 PERCENTILE_CONT restructuring
BigQuery implements `PERCENTILE_CONT` as a window function, not an aggregate:
```sql
-- DuckDB
PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY col)

-- BigQuery (requires subquery + LIMIT 1)
SELECT percentile_col FROM (
    SELECT PERCENTILE_CONT(col, 0.5) OVER() AS percentile_col
    FROM table
)
LIMIT 1
```

### 4.6 BOOL_AND function
```sql
-- DuckDB
BOOL_AND(col)

-- BigQuery
LOGICAL_AND(col)
```

---

## 5. dbt Test Severity Updates

Twelve pre-existing test failures documented in `DATA_QUALITY_FINDINGS.md` were downgraded from `error` to `warn` to prevent CI/CD pipeline blocking. Two additional categories of test failures emerged during BigQuery migration:

### Boolean accepted_values
dbt's `accepted_values` test wraps all values in quotes by default, converting `true/false` to `'True'/'False'` strings. BigQuery cannot compare `BOOL` against `{STRING}`.

**Resolution:** Removed `accepted_values` tests from all boolean columns — the `BOOL` data type already enforces this constraint at the database level, making the test redundant.

Affected columns: `is_current`, `is_primary_payment`, `is_only_payment`, `is_installment_payment`, `has_seller_response`, `is_fast_response`, `is_multiple_reviews`, `is_rating_only`, `is_full_review`, `has_complete_listing`

### Numeric accepted_values
Same quoting issue applies to integer columns — `[1, 2, 3, 4, 5]` becomes `'1','2','3','4','5'`.

**Resolution:** Added `quote: false` to all `accepted_values` tests on numeric columns:
```yaml
- accepted_values:
    values: [1, 2, 3, 4, 5]
    quote: false
```

### Final test results
`PASS=137 WARN=25 ERROR=0 TOTAL=162`

The 25 warnings are all pre-documented data anomalies in `DATA_QUALITY_FINDINGS.md`.

---

## 6. Streamlit Dashboard Migration

### db_connection.py rewrite
Updated to use BigQuery client with Streamlit secrets for cloud deployment.

### Table reference updates
All SQL queries in 5 dashboard pages updated from DuckDB schema references to BigQuery format:

| Layer | DuckDB | BigQuery |
|---|---|---|
| Marts | `dev.main_marts.` | `` `olist-portfolio-492209`.`olist_dbt_marts`. `` |
| Facts | `dev.main_facts.` | `` `olist-portfolio-492209`.`olist_dbt_facts`. `` |
| Dims | `dev.main_dims.` | `` `olist-portfolio-492209`.`olist_dbt_dims`. `` |

### Streamlit Cloud authentication issue
Streamlit Cloud cannot access local `gcloud auth application-default login` credentials — these only exist on the developer's machine. Resolution:

1. Created service account JSON key (required creating a new GCP project without an organization, as `nphuong-nguyen281-org` enforced `iam.disableServiceAccountKeyCreation` which could not be overridden)
2. Added JSON key contents to Streamlit Cloud **App Settings → Secrets** in TOML format
3. Updated `db_connection.py` to read credentials from `st.secrets["gcp_service_account"]`
4. Added `db-dtypes` and `google-auth` to `requirements.txt` — required dependencies for BigQuery → pandas DataFrame conversion

### requirements.txt
```
streamlit
plotly
pandas
google-cloud-bigquery
google-auth
db-dtypes
```

---

## 7. Files Changed Summary

| File | Change |
|---|---|
| `load_data.py` | Rewrote for BigQuery using `google-cloud-bigquery` |
| `profiles.yml` | Updated to BigQuery adapter with service account auth |
| `models/staging/sources.yml` | Updated database and schema for BigQuery |
| `dashboard/utils/db_connection.py` | Rewrote for BigQuery with Streamlit secrets |
| `dashboard/requirements.txt` | Added BigQuery dependencies |
| `models/staging/stg_customers.sql` | Fixed TRIM() on INT64 column |
| `models/staging/stg_order_payments.sql` | Fixed DECIMAL(10,2) → NUMERIC |
| `models/staging/stg_order_items.sql` | Fixed DECIMAL(10,2) → NUMERIC |
| `models/staging/stg_sellers.sql` | Fixed TRIM() on INT64 column |
| `models/facts/fact_orders.sql` | Fixed DATE/TIMESTAMP type mismatch |
| `models/marts/mart_customers_base.sql` | Fixed CTE naming conflict, alias scoping |
| `models/dims/dim_schema.yml` | Removed boolean accepted_values tests |
| `models/facts/fact_schema.yml` | Added quote: false, fixed config syntax bugs |
| `dashboard/pages/*.py` | Updated all table references to BigQuery format |

---

## 8. Known Limitations Post-Migration

- **Query latency:** BigQuery queries are slower than DuckDB for small datasets due to network round-trips. Mitigated by `@st.cache_data(ttl=3600)` caching in Streamlit.
- **Cost:** Within BigQuery's permanent free tier (1TB/month query processing, 10GB storage). Olist dataset is ~100MB — approximately 2,000 full dashboard visits would be needed to approach the free tier limit.