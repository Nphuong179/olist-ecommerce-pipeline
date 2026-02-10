import duckdb
from pathlib import Path

def get_connection():
    db_path = Path(__file__).parent.parent.parent/"dev.duckdb"
    conn = duckdb.connect(str(db_path), read_only=True)
    return conn

def run_query(query):
    conn = get_connection()
    df = conn.execute(query).df()
    conn.close()
    return df