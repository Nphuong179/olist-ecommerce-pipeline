import duckdb
from pathlib import Path
print("FILE IS BEING READ!")
def main():
    # Get the project directory
    project_root = Path(__file__).parent.parent
    data_dir = project_root/'data'/'raw'
    db_path = project_root/'olist_dbt'/'dev.duckdb'

    print("Checking paths")
    print(f"Project root: {project_root}")
    print(f"Data dir: {data_dir}")
    print(f"database path: {db_path}")
    print(f"Data dir exists {data_dir.exists()}")
    print(f"Data dir is dir {data_dir.is_dir()}")

    csv_files = list(data_dir.glob('*.csv'))
    print(f"Found {len(csv_files)} csv files")
    conn = duckdb.connect(db_path)
    for csv_file in csv_files:
        file_name = csv_file.stem.replace('_dataset','')
        print(f"Loading data from {file_name} into DuckDB")
        conn.execute(f"""
            CREATE OR REPLACE TABLE {file_name} AS
            SELECT * FROM read_csv_auto('{csv_file}')
                    """)
        
    conn.close()
    print("All table loaded successfully")

if __name__ == "__main__":
    main()