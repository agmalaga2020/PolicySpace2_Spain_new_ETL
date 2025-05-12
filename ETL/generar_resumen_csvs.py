import os
import csv

def find_csv_files(root_dir):
    csv_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.csv'):
                rel_dir = os.path.relpath(dirpath, os.getcwd())
                rel_path = os.path.join(rel_dir, filename)
                csv_files.append(rel_path)
    return csv_files

def get_csv_header(csv_path):
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            return header
    except Exception:
        return []

def main():
    etl_dir = os.path.join(os.getcwd(), 'ETL')
    csv_files = find_csv_files(etl_dir)
    summary_rows = []
    max_cols = 0

    for csv_path in csv_files:
        header = get_csv_header(csv_path)
        row = [os.path.basename(csv_path), os.path.relpath(csv_path, os.getcwd())] + header
        summary_rows.append(row)
        if len(header) > max_cols:
            max_cols = len(header)

    # Prepare header for summary file
    summary_header = ['nombre_archivo', 'ruta_relativa'] + [f'col_{i+1}' for i in range(max_cols)]

    # Pad rows to have same number of columns
    for row in summary_rows:
        while len(row) < len(summary_header):
            row.append('')

    summary_csv_path = os.path.join('ETL', 'summary_csvs.csv')
    with open(summary_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(summary_header)
        writer.writerows(summary_rows)

if __name__ == '__main__':
    main()
