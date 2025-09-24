#!/usr/bin/env python
"""
Verify that timestamp fix is working correctly
"""
import requests
import json
from datetime import datetime

print("Testing timestamp fix for candles API...")
print("=" * 60)

# Get candle data
response = requests.get("http://127.0.0.1:5001/api/candles/GOLD03OCT25FUT?timeframe=1m&limit=5")
data = response.json()

if data['status'] == 'success' and data['candles']:
    print(f"Got {len(data['candles'])} candles")
    print("\nAnalyzing timestamps:")
    print("-" * 40)

    for candle in data['candles'][:3]:  # Check first 3 candles
        unix_ts = candle['time']

        # Convert to datetime
        dt_utc = datetime.utcfromtimestamp(unix_ts)
        dt_local = datetime.fromtimestamp(unix_ts)

        print(f"\nCandle timestamp: {unix_ts}")
        print(f"  As UTC:   {dt_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  As Local: {dt_local.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  OHLC: {candle['open']:.2f} / {candle['high']:.2f} / {candle['low']:.2f} / {candle['close']:.2f}")
        print(f"  Volume: {candle['volume']}")

    # Check current time
    current_time = datetime.now()
    current_unix = int(current_time.timestamp())
    latest_candle_time = data['candles'][-1]['time'] if data['candles'] else 0

    print(f"\nTime comparison:")
    print(f"  Current time:     {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Current Unix:     {current_unix}")
    print(f"  Latest candle:    {latest_candle_time}")
    print(f"  Difference:       {current_unix - latest_candle_time} seconds")

    if abs(current_unix - latest_candle_time) < 300:  # Within 5 minutes
        print("\n✅ Timestamps appear correct (within 5 minutes of current time)")
    else:
        time_diff_hours = (current_unix - latest_candle_time) / 3600
        print(f"\n⚠️ Timestamp issue detected! Off by {time_diff_hours:.1f} hours")
        if abs(time_diff_hours - 5.5) < 0.5:
            print("   This looks like the IST offset issue (5.5 hours)")
else:
    print("No candle data available")