import duckdb
from pathlib import Path
print("FILE IS BEING READ!")
def main():
    # Get the project directory 
    project_root = Path(__file__).parent.parent
    data_dir = project_root/'data'/'raw'
    db_path = project_root/'olist_dbt'/'dev.duckdb'

    csv_files = list(data_dir.glob('*.csv'))
    conn = duckdb.connect(db_path)
    for csv_file in csv_files:
        file_name = csv_file.stem.replace('olist_','raw_').replace('_dataset','')
        conn.execute(f"""
            CREATE OR REPLACE TABLE {file_name} AS
            SELECT * FROM read_csv_auto('{csv_file}')
                    """)
        
    conn.close()
    print("All table loaded successfully")

if __name__ == "__main__":
    main()