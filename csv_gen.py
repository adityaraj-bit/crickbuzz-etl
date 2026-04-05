import sqlite3
import csv
import os

DB_NAME = "cricket.db"
OUTPUT_DIR = "csv_exports"


def export_all_tables():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Get all table names (ignore sqlite internal tables)
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
    """)
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print("❌ No tables found in database")
        return

    for table in tables:
        export_table_to_csv(cursor, table)

    conn.close()
    print(f"✅ Export completed. Files saved in '{OUTPUT_DIR}/'")


def export_table_to_csv(cursor, table_name):
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    # Get column names
    column_names = [description[0] for description in cursor.description]

    file_path = os.path.join(OUTPUT_DIR, f"{table_name}.csv")

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow(column_names)

        # Write data
        writer.writerows(rows)

    print(f"✔ Exported: {table_name} ({len(rows)} rows)")


if __name__ == "__main__":
    export_all_tables()