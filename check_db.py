#!/usr/bin/env python
"""
Check database structure and data
"""
import psycopg2

print("Checking QuestDB structure...")

conn = psycopg2.connect(
    host='127.0.0.1',
    port=8812,
    database='qdb',
    user='admin',
    password='quest'
)
cursor = conn.cursor()

# Check table structure
print("\n1. Table structure for ticks_ltp:")
cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'ticks_ltp'")
for col in cursor.fetchall():
    print(f"  - {col[0]}: {col[1]}")

# Check sample data
print("\n2. Sample data from ticks_ltp:")
cursor.execute("SELECT * FROM ticks_ltp LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row}")

# Check for NULL values
print("\n3. Checking for NULL ltps:")
cursor.execute("SELECT count(*) FROM ticks_ltp WHERE ltp IS NULL")
null_count = cursor.fetchone()[0]
print(f"  NULL ltp count: {null_count}")

cursor.execute("SELECT count(*) FROM ticks_ltp WHERE ltp IS NOT NULL")
valid_count = cursor.fetchone()[0]
print(f"  Valid ltp count: {valid_count}")

# Get symbols with valid data
print("\n4. Symbols with valid LTP data:")
cursor.execute("""
    SELECT symbol, count(*) as tick_count,
           min(ltp) as min_ltp, max(ltp) as max_ltp
    FROM ticks_ltp
    WHERE ltp IS NOT NULL
    GROUP BY symbol
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} ticks, range {row[2]}-{row[3]}")

conn.close()