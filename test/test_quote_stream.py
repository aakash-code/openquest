"""
Test why ticks_quote table is not updating
Check if quote stream is actually receiving data with bid/ask/volume
"""

from openalgo import api
import time
import json
from datetime import datetime

# Initialize OpenAlgo client
client = api(
    api_key="7999cab44119b8f0dc4834f925b80fc3977a2fef8a2d88449baf9322e984d9f9",
    host="http://127.0.0.1:5000",
    ws_url="ws://127.0.0.1:8765"
)

# Use correct NSE symbols
instruments = [
    {"exchange": "NSE", "symbol": "RELIANCE"},
    {"exchange": "NSE", "symbol": "SBIN"},
    {"exchange": "NSE", "symbol": "INFY"},
    {"exchange": "NSE", "symbol": "TCS"}
]

print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST")
print("=" * 60)

# Track received data
quote_data_received = []
quote_with_bid_ask = 0
quote_with_volume = 0

def on_quote(data):
    global quote_data_received, quote_with_bid_ask, quote_with_volume

    quote_data_received.append(data)

    # Analyze data structure
    has_bid = False
    has_ask = False
    has_volume = False
    bid_value = None
    ask_value = None
    volume_value = None

    if isinstance(data, dict):
        # Check for nested data structure
        if 'data' in data and isinstance(data['data'], dict):
            actual_data = data['data']
            has_bid = 'bid' in actual_data and actual_data['bid'] is not None
            has_ask = 'ask' in actual_data and actual_data['ask'] is not None
            has_volume = 'volume' in actual_data and actual_data['volume'] is not None
            bid_value = actual_data.get('bid')
            ask_value = actual_data.get('ask')
            volume_value = actual_data.get('volume')
        else:
            # Direct data
            has_bid = 'bid' in data and data['bid'] is not None
            has_ask = 'ask' in data and data['ask'] is not None
            has_volume = 'volume' in data and data['volume'] is not None
            bid_value = data.get('bid')
            ask_value = data.get('ask')
            volume_value = data.get('volume')

    if has_bid and has_ask:
        quote_with_bid_ask += 1

    if has_volume:
        quote_with_volume += 1

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Quote Update:")
    print(f"Symbol: {data.get('symbol', 'Unknown')}")
    print(f"Bid: {bid_value} (present: {has_bid})")
    print(f"Ask: {ask_value} (present: {has_ask})")
    print(f"Volume: {volume_value} (present: {has_volume})")

    if len(quote_data_received) == 1:
        print("\nFirst quote raw data structure:")
        print(json.dumps(data, indent=2, default=str))

try:
    print("\nConnecting to OpenAlgo WebSocket...")
    client.connect()

    print("\nSubscribing to Quote stream for NSE symbols...")
    client.subscribe_quote(instruments, on_data_received=on_quote)

    print("\nListening for 10 seconds...")
    time.sleep(10)

    print("\nUnsubscribing...")
    client.unsubscribe_quote(instruments)

finally:
    client.disconnect()
    print("\n" + "=" * 60)

print("\nSUMMARY:")
print(f"Total quote updates received: {len(quote_data_received)}")
print(f"Quotes with both bid and ask: {quote_with_bid_ask}")
print(f"Quotes with volume data: {quote_with_volume}")

if len(quote_data_received) == 0:
    print("\n*** PROBLEM IDENTIFIED ***")
    print("No quote data is being received from WebSocket!")
    print("\nPossible reasons:")
    print("1. Market is closed (NSE trading hours: 9:15 AM - 3:30 PM IST)")
    print("2. OpenAlgo server is not streaming quote data")
    print("3. WebSocket connection issues")

    # Try REST API as fallback
    print("\nTesting REST API quotes endpoint as fallback...")
    for inst in instruments[:2]:
        try:
            quote = client.quotes(symbol=inst['symbol'], exchange=inst['exchange'])
            print(f"\nREST Quote for {inst['symbol']}:")
            if 'data' in quote:
                print(f"  LTP: {quote['data'].get('ltp')}")
                print(f"  Bid: {quote['data'].get('bid')}")
                print(f"  Ask: {quote['data'].get('ask')}")
                print(f"  Volume: {quote['data'].get('volume')}")
        except Exception as e:
            print(f"Error: {e}")

elif quote_with_bid_ask == 0:
    print("\n*** PROBLEM IDENTIFIED ***")
    print("Quote data is received but missing bid/ask values!")
    print("This is why ticks_quote table remains empty.")
    print("\nThe insert condition in app.py:186-194 requires both bid AND ask.")

else:
    print("\n✓ Quote data with bid/ask is being received properly.")
    print("Check if app.py is running and connected to handle this data.")

# Show sample data structure if available
if quote_data_received and len(quote_data_received) > 0:
    print("\n\nSample quote data keys:")
    sample = quote_data_received[0]
    if isinstance(sample, dict):
        print("Top level keys:", list(sample.keys()))
        if 'data' in sample and isinstance(sample['data'], dict):
            print("Data level keys:", list(sample['data'].keys()))