from google.cloud import bigquery
from pathlib import Path
def main():
    # Get the project directory 
    project_root = Path(__file__).parent.parent
    data_dir = project_root/'data'/'raw'
    key_path = project_root / 'keys' / 'bq_service_account.json'
    PROJECT_ID = 'olist-portfolio-492209'
    DATASET_ID = 'olist_raw'
    client = bigquery.Client.from_service_account_json(str(key_path))
    csv_files = list(data_dir.glob('*.csv'))
    for csv_file in csv_files:
        table_name = csv_file.stem.replace('olist_', '').replace('_dataset', '')
        table_id = f'{PROJECT_ID}.{DATASET_ID}.{table_name}'
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=1,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )

        with open(csv_file, 'rb') as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
            job.result()
if __name__ == '__main__':
    main()