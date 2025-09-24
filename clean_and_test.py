#!/usr/bin/env python
"""
Clean NULL data and test data extraction
"""
import psycopg2
from openalgo import api
import time
import os
import json

print("Cleaning and testing data...")

# Connect to QuestDB
conn = psycopg2.connect(
    host='127.0.0.1',
    port=8812,
    database='qdb',
    user='admin',
    password='quest'
)
cursor = conn.cursor()

# Check NULL LTP records (QuestDB doesn't support DELETE)
print("\n1. Checking NULL LTP records...")
cursor.execute("SELECT count(*) FROM ticks_ltp WHERE ltp IS NULL")
null_count = cursor.fetchone()[0]
print(f"  Found {null_count} NULL records")
# Note: QuestDB doesn't support DELETE - would need to drop and recreate table

# Test OpenAlgo data extraction
print("\n2. Testing OpenAlgo data extraction...")
print("  (This will capture a few ticks to see the data format)")

# Get config
import json
if os.path.exists('config.json'):
    with open('config.json', 'r') as f:
        config = json.load(f)
        api_key = config.get('api_key')
else:
    print("  No config found, using test mode")
    api_key = "test"

if api_key and api_key != "test":
    # Initialize API
    client = api(
        api_key=api_key,
        host="http://127.0.0.1:5000",
        ws_url="ws://127.0.0.1:8765"
    )

    # Test callback to see data structure
    def test_callback(data):
        print(f"  Received raw data: {data}")
        # Handle nested data structure
        if isinstance(data, dict):
            if 'data' in data and isinstance(data['data'], dict):
                ltp = data['data'].get('ltp')
                print(f"  Found nested LTP: {ltp}")
            else:
                ltp = data.get('ltp') or data.get('last_price') or data.get('close') or data.get('price')
                print(f"  Extracted direct LTP: {ltp}")
        else:
            ltp = None
            print(f"  Data is not a dict: {type(data)}")

    try:
        # Connect and subscribe to one symbol
        client.connect()
        client.subscribe_ltp([{"exchange": "MCX", "symbol": "GOLDTEN31DEC25FUT"}],
                            on_data_received=test_callback)

        # Wait for a few seconds to capture data
        print("  Waiting for data (5 seconds)...")
        time.sleep(5)

        client.unsubscribe_ltp([{"exchange": "MCX", "symbol": "GOLDTEN31DEC25FUT"}])
        client.disconnect()
    except Exception as e:
        print(f"  Error: {e}")

# Check if we have valid data now
print("\n3. Checking for valid data after test...")
cursor.execute("SELECT count(*) FROM ticks_ltp WHERE ltp IS NOT NULL")
valid_count = cursor.fetchone()[0]
print(f"  Valid LTP records: {valid_count}")

if valid_count > 0:
    cursor.execute("""
        SELECT symbol, min(ltp), max(ltp), count(*)
        FROM ticks_ltp
        WHERE ltp IS NOT NULL
        GROUP BY symbol
        LIMIT 5
    """)
    print("  Sample valid data:")
    for row in cursor.fetchall():
        print(f"    {row[0]}: {row[3]} ticks, range {row[1]}-{row[2]}")

conn.close()
print("\nTest complete!")