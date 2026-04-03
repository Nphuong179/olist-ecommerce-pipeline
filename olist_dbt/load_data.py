from google.cloud import bigquery
from pathlib import Path
def main():
    # Get the project directory 
    project_root = Path(__file__).parent.parent
    data_dir = project_root/'data'/'raw'
    PROJECT_ID = 'olist-portfolio-491906'
    DATASET_ID = 'olist_raw'
    client = bigquery.Client(project=PROJECT_ID)
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