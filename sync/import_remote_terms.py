#!/usr/bin/env python3
import os
import csv
import pymysql

# ----------------------------
# Output directory and file path
# ----------------------------
output_dir = "sync"
os.makedirs(output_dir, exist_ok=True)
csv_file_path = os.path.join(output_dir, "mor_terms.csv")

# ----------------------------
# Connect to Hosting Ireland MySQL
# ----------------------------
try:
    conn = pymysql.connect(
        host='osmium.webhostingireland.ie',
        port=3306,
        user='t567715',
        password='0bjs8Pz55Q',
        database='t567715_wp_tcsp'
    )
    print("✅ Connection successful!")

    # ----------------------------
    # Query and export to CSV
    # ----------------------------
    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute("SELECT * FROM mor_terms")
        rows = cursor.fetchall()

        if rows:
            with open(csv_file_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            print(f"✅ Exported {len(rows)} records to {csv_file_path}")
        else:
            print("⚠️ No records found in mor_terms.")

    conn.close()

except Exception as e:
    print(f"❌ Connection failed: {e}")
