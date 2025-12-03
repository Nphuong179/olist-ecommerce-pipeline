import duckdb
from pathlib import Path

def main():
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    data_dir = project_root/'data'/'raw'
    db_path = project_root/'olist_dbt'/'dev.duckdb'

    csv_files = list(data_dir.glob('*.csv'))
    conn = duckdb.connect(db_path)
    for csv_file in csv_files:
        table_name = csv_file.stem.replace('_dataset','')

        print(f"Loading {table_name} into DuckDB....")
        conn.execute(f"""
            CREATE OR REPLACE TABLE {table_name} AS
            SELECT * FROM read_csv_auto('{csv_file}')
                     """)
        
    conn.close()
    print("All table loaded successfully")

if __name__ == "__main__":
    main()