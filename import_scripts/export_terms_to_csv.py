#!/usr/bin/env python3
import os
import csv
import pymysql

def export_terms_to_csv():
    print("[STEP] Starting export_terms_to_csv")

    # Get absolute path to import_csv/
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"[DEBUG] BASE_DIR = {BASE_DIR}")

    output_dir = os.path.join(BASE_DIR, 'import_csv')
    os.makedirs(output_dir, exist_ok=True)
    print(f"[DEBUG] output_dir = {output_dir}")

    csv_path = os.path.join(output_dir, 'terms.csv')
    print(f"[DEBUG] csv_path = {csv_path}")

    try:
        print("[STEP] Connecting to remote MySQL...")
        conn = pymysql.connect(
            host='osmium.webhostingireland.ie',
            port=3306,
            user='t567715',
            password='0bjs8Pz55Q',
            database='t567715_wp_tcsp'
        )
        print("✅ Connected to MySQL")

        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            print("[STEP] Executing SELECT...")
            cursor.execute("SELECT * FROM mor_terms WHERE term_id != 0")
            rows = cursor.fetchall()
            print(f"[STEP] Retrieved {len(rows)} rows")

        with open(csv_path, "w", newline='', encoding='utf-8') as f:
            print("[STEP] Writing to CSV...")
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        print(f"✅ Exported {len(rows)} rows to {csv_path}")
        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

# Call the function if run as script
if __name__ == "__main__":
    export_terms_to_csv()
