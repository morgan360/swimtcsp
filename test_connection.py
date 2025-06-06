import pymysql

try:
    conn = pymysql.connect(
        host='osmium.webhostingireland.ie',
        port=3306,
        user='t567715',
        password='0bjs8Pz55Q',
        database='t567715_wp_tcsp'
    )
    print("✅ Connection successful!")
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)

