#!/usr/bin/env python
"""
Test to understand the chart timestamp issue
"""
import requests
from datetime import datetime
import pytz

print("Testing chart timestamp issue...")
print("=" * 60)

# Get candle data from API
r = requests.get('http://127.0.0.1:5001/api/candles/GOLDM05FEB26FUT?timeframe=1m&limit=1')
data = r.json()

if data['candles']:
    candle = data['candles'][0]
    unix_ts = candle['time']

    print(f"1. From API:")
    print(f"   Unix timestamp: {unix_ts}")
    print(f"   As UTC:   {datetime.utcfromtimestamp(unix_ts).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   As Local: {datetime.fromtimestamp(unix_ts).strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n2. Current time:")
    print(f"   Local:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   UTC:      {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n3. The problem:")
    print(f"   We're storing IST timestamps in DB")
    print(f"   Chart expects UTC timestamps")
    print(f"   Need to subtract 19800 seconds (5.5 hours) from our timestamps")

    # Calculate corrected timestamp
    ist_offset = 19800  # 5.5 hours in seconds
    corrected_ts = unix_ts - ist_offset

    print(f"\n4. Solution:")
    print(f"   Original timestamp: {unix_ts}")
    print(f"   Corrected (UTC):    {corrected_ts}")
    print(f"   Will display as:    {datetime.fromtimestamp(corrected_ts).strftime('%Y-%m-%d %H:%M:%S')} in chart")

else:
    print("No candle data available")