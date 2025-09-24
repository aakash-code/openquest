#!/usr/bin/env python
"""
Test script to verify all connections
"""
import psycopg2
from datetime import datetime
import json

print("=" * 60)
print("Testing OpenQuest Connections")
print("=" * 60)

# Test QuestDB connection
print("\n1. Testing QuestDB connection...")
try:
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=8812,
        database='qdb',
        user='admin',
        password='quest'
    )
    cursor = conn.cursor()
    print("✓ QuestDB connected successfully")

    # Check for tables
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cursor.fetchall()
    print(f"✓ Found {len(tables)} tables")

    # Check tick count
    cursor.execute("SELECT count(*) FROM ticks_ltp")
    count = cursor.fetchone()[0]
    print(f"✓ Total ticks in database: {count}")

    # Check latest tick
    cursor.execute("""
        SELECT timestamp, symbol, ltp
        FROM ticks_ltp
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    latest = cursor.fetchone()
    if latest:
        print(f"✓ Latest tick: {latest[1]} @ {latest[2]} ({latest[0]})")
    else:
        print("✗ No ticks found in database")

    # Check unique symbols
    cursor.execute("SELECT DISTINCT symbol FROM ticks_ltp LIMIT 10")
    symbols = cursor.fetchall()
    print(f"✓ Active symbols: {', '.join([s[0] for s in symbols[:5]])}")

    conn.close()

except Exception as e:
    print(f"✗ QuestDB connection failed: {e}")

# Test API endpoint
print("\n2. Testing API endpoints...")
import requests

try:
    # Test main page
    response = requests.get("http://127.0.0.1:5001/")
    print(f"✓ Dashboard endpoint: {response.status_code}")

    # Test chart page
    response = requests.get("http://127.0.0.1:5001/chart")
    print(f"✓ Chart endpoint: {response.status_code}")

    # Test candles API
    response = requests.get("http://127.0.0.1:5001/api/candles/GOLDTEN31DEC25FUT?timeframe=1m&limit=5")
    data = response.json()
    if data['status'] == 'success':
        print(f"✓ Candles API: {data.get('count', 0)} candles returned")
        if data.get('candles'):
            latest_candle = data['candles'][-1]
            print(f"  Latest candle: Time={datetime.fromtimestamp(latest_candle['time'])}, Close={latest_candle['close']}")
    else:
        print(f"✗ Candles API error: {data}")

    # Test metrics
    response = requests.get("http://127.0.0.1:5001/metrics")
    metrics = response.json()
    print(f"✓ Metrics: {metrics.get('total_ticks', 0)} total ticks, {metrics.get('active_symbols', 0)} active symbols")

except Exception as e:
    print(f"✗ API test failed: {e}")

print("\n3. Checking configuration...")
import os
if os.path.exists('config.json'):
    with open('config.json', 'r') as f:
        config = json.load(f)
        print(f"✓ Config found: API key {'set' if config.get('api_key') else 'NOT SET'}")
        print(f"  LTP: {config.get('ltp_enabled', False)}, Quote: {config.get('quote_enabled', False)}, Depth: {config.get('depth_enabled', False)}")
else:
    print("✗ No config.json found")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)