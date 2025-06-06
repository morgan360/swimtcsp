##!/usr/bin/env python3
import pymysql


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

    # 👇 You can put sync logic here or call sync_terms_from_remote()
    # Example placeholder:
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM wp_tcsp_terms")  # Replace with real table
        row_count = cursor.fetchone()
        print(f"📦 Remote DB has {row_count[0]} term records.")

    conn.close()

except Exception as e:
    print(f"❌ Connection failed: {e}")