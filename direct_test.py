#!/usr/bin/env python
"""
Direct test of OpenAlgo API and data insertion
"""
from openalgo import api
import psycopg2
import time
import json
import os

print("Direct test of OpenAlgo streaming...")

# Connect to QuestDB
conn = psycopg2.connect(
    host='127.0.0.1',
    port=8812,
    database='qdb',
    user='admin',
    password='quest'
)
cursor = conn.cursor()

# Get config
with open('config.json', 'r') as f:
    config = json.load(f)
    api_key = config.get('api_key')

# Initialize API directly
client = api(
    api_key=api_key,
    host="http://127.0.0.1:5000",
    ws_url="ws://127.0.0.1:8765"
)

# Direct callback that inserts data
def data_callback(data):
    print(f"Received: {data}")

    # Handle nested structure
    ltp = None
    symbol = None

    if isinstance(data, dict):
        if 'data' in data and isinstance(data['data'], dict):
            ltp = data['data'].get('ltp')
            symbol = data.get('symbol')
        else:
            ltp = data.get('ltp')
            symbol = data.get('symbol')

    if ltp and symbol:
        print(f"  Inserting {symbol}: {ltp}")
        try:
            cursor.execute(
                "INSERT INTO ticks_ltp (symbol, ltp, timestamp) VALUES (%s, %s, NOW())",
                (symbol, ltp)
            )
            conn.commit()
            print(f"  Inserted successfully!")
        except Exception as e:
            print(f"  Insert error: {e}")
    else:
        print(f"  No LTP found in data")

# Connect and subscribe to Quote (might have more data than just LTP)
client.connect()
print("Subscribing to Quote stream...")
client.subscribe_quote([{"exchange": "MCX", "symbol": "GOLDTEN31DEC25FUT"}],
                       on_data_received=data_callback)

print("Streaming for 10 seconds...")
time.sleep(10)

# Check results
cursor.execute("SELECT count(*) FROM ticks_ltp WHERE ltp IS NOT NULL")
valid_count = cursor.fetchone()[0]
print(f"\nValid records after test: {valid_count}")

cursor.execute("""
    SELECT symbol, ltp, timestamp
    FROM ticks_ltp
    WHERE ltp IS NOT NULL
    ORDER BY timestamp DESC
    LIMIT 5
""")
print("Latest valid records:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} at {row[2]}")

client.unsubscribe_quote([{"exchange": "MCX", "symbol": "GOLDTEN31DEC25FUT"}])
client.disconnect()
conn.close()
print("\nTest complete!")