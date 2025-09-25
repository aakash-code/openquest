"""
Test WebSocket data flow to identify why ticks_quote table is not updating
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

# Test instruments - using both MCX and NSE symbols
instruments = [
    {"exchange": "MCX", "symbol": "GOLDM25JANFUT"},
    {"exchange": "MCX", "symbol": "SILVERM25FEBFUT"},
    {"exchange": "NSE", "symbol": "RELIANCE"},
    {"exchange": "NSE", "symbol": "SBIN"}
]

# Track what data we receive
ltp_count = 0
quote_count = 0
ltp_data_samples = []
quote_data_samples = []

def on_ltp(data):
    global ltp_count, ltp_data_samples
    ltp_count += 1
    if len(ltp_data_samples) < 3:  # Keep first 3 samples
        ltp_data_samples.append(data)
    print(f"\n=== LTP Update #{ltp_count} ===")
    print(f"Raw data: {json.dumps(data, indent=2, default=str)}")

def on_quote(data):
    global quote_count, quote_data_samples
    quote_count += 1
    if len(quote_data_samples) < 3:  # Keep first 3 samples
        quote_data_samples.append(data)
    print(f"\n=== QUOTE Update #{quote_count} ===")
    print(f"Raw data: {json.dumps(data, indent=2, default=str)}")

    # Check for bid/ask presence
    if isinstance(data, dict):
        has_bid = 'bid' in data or ('data' in data and 'bid' in data.get('data', {}))
        has_ask = 'ask' in data or ('data' in data and 'ask' in data.get('data', {}))
        has_volume = 'volume' in data or ('data' in data and 'volume' in data.get('data', {}))
        print(f"Has bid: {has_bid}, Has ask: {has_ask}, Has volume: {has_volume}")

print("Connecting to OpenAlgo WebSocket...")
client.connect()

print("\n1. Testing LTP stream...")
client.subscribe_ltp(instruments, on_data_received=on_ltp)
time.sleep(5)
client.unsubscribe_ltp(instruments)

print(f"\nLTP Summary: Received {ltp_count} updates")
if ltp_data_samples:
    print("Sample LTP data structure:")
    print(json.dumps(ltp_data_samples[0], indent=2, default=str))

print("\n2. Testing Quote stream...")
client.subscribe_quote(instruments, on_data_received=on_quote)
time.sleep(5)
client.unsubscribe_quote(instruments)

print(f"\nQuote Summary: Received {quote_count} updates")
if quote_data_samples:
    print("Sample Quote data structure:")
    print(json.dumps(quote_data_samples[0], indent=2, default=str))

# Test REST API quotes endpoint
print("\n3. Testing REST API quotes endpoint...")
for inst in instruments[:2]:  # Test first 2 instruments
    try:
        quote = client.quotes(symbol=inst['symbol'], exchange=inst['exchange'])
        print(f"\nREST Quote for {inst['symbol']} ({inst['exchange']}):")
        print(json.dumps(quote, indent=2, default=str))
    except Exception as e:
        print(f"Error getting quote for {inst['symbol']}: {e}")

client.disconnect()

print("\n=== ANALYSIS ===")
print(f"Total LTP updates: {ltp_count}")
print(f"Total Quote updates: {quote_count}")

if quote_count == 0:
    print("\n⚠️ NO QUOTE DATA RECEIVED - This is why ticks_quote table is empty!")
    print("Possible reasons:")
    print("1. OpenAlgo server not sending quote data")
    print("2. Quote subscription not working")
    print("3. Data format issue")
else:
    print("\n✓ Quote data received but may have issues with bid/ask fields")

print("\n=== Data Structure Analysis ===")
if ltp_data_samples:
    print("LTP data fields:", list(ltp_data_samples[0].keys()) if isinstance(ltp_data_samples[0], dict) else "Not a dict")
if quote_data_samples:
    print("Quote data fields:", list(quote_data_samples[0].keys()) if isinstance(quote_data_samples[0], dict) else "Not a dict")