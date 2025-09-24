#!/usr/bin/env python
"""
Test script to understand timestamp issues
"""
import psycopg2
from datetime import datetime
import pytz
import time

print("=" * 60)
print("Timestamp Analysis - Understanding the time zone issue")
print("=" * 60)

# Get current time in different formats
print("\n1. Current Time Analysis:")
print("-" * 40)

# Local time
local_time = datetime.now()
print(f"Local time (system):     {local_time.strftime('%Y-%m-%d %H:%M:%S')}")

# UTC time
utc_time = datetime.utcnow()
print(f"UTC time:                {utc_time.strftime('%Y-%m-%d %H:%M:%S')}")

# IST time
ist_tz = pytz.timezone('Asia/Kolkata')
ist_time = datetime.now(ist_tz)
print(f"IST time (explicit):     {ist_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Unix timestamp
unix_timestamp = int(time.time())
print(f"Unix timestamp:          {unix_timestamp}")
print(f"Unix timestamp as UTC:   {datetime.utcfromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Unix timestamp as local: {datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')}")

# Connect to QuestDB
print("\n2. QuestDB Data Analysis:")
print("-" * 40)

try:
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=8812,
        database='qdb',
        user='admin',
        password='quest'
    )
    cursor = conn.cursor()

    # Get the latest timestamps from database
    cursor.execute("""
        SELECT symbol, ltp, timestamp
        FROM ticks_ltp
        WHERE ltp IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 5
    """)

    results = cursor.fetchall()

    if results:
        print("Latest records from database:")
        for row in results:
            symbol, ltp, db_timestamp = row

            # The database timestamp
            print(f"\nSymbol: {symbol}")
            print(f"  Raw DB timestamp:      {db_timestamp}")
            print(f"  DB time string:        {db_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

            # Convert to unix timestamp
            unix_ts = int(db_timestamp.timestamp())
            print(f"  As Unix timestamp:     {unix_ts}")

            # Check what this looks like in different timezones
            utc_from_db = datetime.utcfromtimestamp(unix_ts)
            local_from_db = datetime.fromtimestamp(unix_ts)

            print(f"  Interpreted as UTC:    {utc_from_db.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  Interpreted as local:  {local_from_db.strftime('%Y-%m-%d %H:%M:%S')}")

            # Calculate offset
            offset_hours = (local_from_db - utc_from_db).total_seconds() / 3600
            print(f"  Local offset from UTC: {offset_hours:.1f} hours")

            break  # Just analyze one record in detail
    else:
        print("No records with valid LTP found")

    # Check what NOW() returns in QuestDB
    cursor.execute("SELECT NOW()")
    db_now = cursor.fetchone()[0]
    print(f"\n3. QuestDB NOW() Analysis:")
    print("-" * 40)
    print(f"QuestDB NOW():           {db_now}")
    print(f"Local system time:       {datetime.now()}")
    print(f"UTC time:                {datetime.utcnow()}")

    # Compare
    db_now_unix = int(db_now.timestamp())
    local_now_unix = int(time.time())
    diff_seconds = db_now_unix - local_now_unix
    print(f"\nTime difference (DB - Local): {diff_seconds} seconds")

    conn.close()

except Exception as e:
    print(f"Database error: {e}")

print("\n4. Solution:")
print("-" * 40)
print("The issue is that QuestDB stores timestamps in UTC by default.")
print("When we fetch data, we need to:")
print("1. Keep the Unix timestamp as-is (it's already UTC)")
print("2. The chart library expects Unix timestamps in seconds")
print("3. The chart will then apply the IST timezone for display")

print("\n5. Test Data for Chart:")
print("-" * 40)
# Create a sample timestamp for testing
test_time = datetime.now()
test_unix = int(test_time.timestamp())
print(f"Current time:            {test_time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Unix timestamp for chart: {test_unix}")
print(f"This should display as:   {test_time.strftime('%Y-%m-%d %H:%M:%S')} in the chart")