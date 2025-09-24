#!/usr/bin/env python
"""
Test script to verify all connections
"""
import sys
import os
# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    print("[OK] QuestDB connected successfully")

    # Check for tables
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cursor.fetchall()
    print(f"[OK] Found {len(tables)} tables")

    # Check tick count
    cursor.execute("SELECT count(*) FROM ticks_ltp")
    count = cursor.fetchone()[0]
    print(f"[OK] Total ticks in database: {count}")

    # Check latest tick
    cursor.execute("""
        SELECT timestamp, symbol, ltp
        FROM ticks_ltp
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    latest = cursor.fetchone()
    if latest:
        print(f"[OK] Latest tick: {latest[1]} @ {latest[2]} ({latest[0]})")
    else:
        print("[FAIL] No ticks found in database")

    # Check unique symbols
    cursor.execute("SELECT DISTINCT symbol FROM ticks_ltp LIMIT 10")
    symbols = cursor.fetchall()
    print(f"[OK] Active symbols: {', '.join([s[0] for s in symbols[:5]])}")

    conn.close()

except Exception as e:
    print(f"[FAIL] QuestDB connection failed: {e}")

# Test API endpoint
print("\n2. Testing API endpoints...")
import requests

try:
    # Test main page
    response = requests.get("http://127.0.0.1:5001/")
    print(f"[OK] Dashboard endpoint: {response.status_code}")

    # Test chart page
    response = requests.get("http://127.0.0.1:5001/chart")
    print(f"[OK] Chart endpoint: {response.status_code}")

    # Test candles API
    response = requests.get("http://127.0.0.1:5001/api/candles/GOLDTEN31DEC25FUT?timeframe=1m&limit=5")
    data = response.json()
    if data['status'] == 'success':
        print(f"[OK] Candles API: {data.get('count', 0)} candles returned")
        if data.get('candles'):
            latest_candle = data['candles'][-1]
            print(f"  Latest candle: Time={datetime.fromtimestamp(latest_candle['time'])}, Close={latest_candle['close']}")
    else:
        print(f"[FAIL] Candles API error: {data}")

    # Test metrics
    response = requests.get("http://127.0.0.1:5001/metrics")
    metrics = response.json()
    print(f"[OK] Metrics: {metrics.get('total_ticks', 0)} total ticks, {metrics.get('active_symbols', 0)} active symbols")

except Exception as e:
    print(f"[FAIL] API test failed: {e}")

print("\n3. Checking configuration...")
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.json')
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
        print(f"[OK] Config found: API key {'set' if config.get('api_key') else 'NOT SET'}")
        print(f"  LTP: {config.get('ltp_enabled', False)}, Quote: {config.get('quote_enabled', False)}, Depth: {config.get('depth_enabled', False)}")
else:
    print("[FAIL] No config.json found")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)