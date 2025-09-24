# OpenQuest

Real-time data aggregation tool for OpenAlgo that streams MCX futures tick data into QuestDB.

## Overview

OpenQuest connects to OpenAlgo via REST and WebSocket APIs to stream real-time market data for MCX futures contracts. All tick-level data is stored in QuestDB for high-performance time-series analysis and backtesting.

## Features

- **Zero Configuration**: Configure everything through the web UI
- **Real-Time Streaming**: LTP, Quote, and Depth data streams
- **MCX Futures**: Automatic aggregation of all MCX futures symbols
- **Modern UI**: Supabase green/black theme with TailwindCSS and DaisyUI
- **Live Metrics**: Track tick rates, spreads, and connection status

## Prerequisites

- Python 3.11+
- QuestDB running at http://127.0.0.1:9000
- OpenAlgo running at http://127.0.0.1:5000 (REST) and ws://127.0.0.1:8765 (WebSocket)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/openquest.git
cd openquest
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start QuestDB (if not already running):
```bash
docker run -p 9000:9000 -p 8812:8812 questdb/questdb
```

## Usage

1. Run the application:
```bash
python run.py
```

2. Open your browser and navigate to:
```
http://127.0.0.1:5001
```

3. Configure your OpenAlgo connection:
   - Enter your OpenAlgo API key
   - Verify REST API and WebSocket URLs
   - Select which data streams to enable (LTP, Quote, Depth)

4. Click "Start Streaming" to begin data aggregation

## Database Schema

### ticks_ltp
- `timestamp` - Time of tick
- `symbol` - MCX futures symbol
- `ltp` - Last traded price

### ticks_quote
- `timestamp` - Time of quote
- `symbol` - MCX futures symbol
- `bid` - Best bid price
- `ask` - Best ask price
- `spread` - Bid-ask spread
- `volume` - Trading volume
- `open_interest` - Open interest

### ticks_depth
- `timestamp` - Time of depth update
- `symbol` - MCX futures symbol
- `level` - Orderbook level (0-4)
- `bid` - Bid price at level
- `ask` - Ask price at level
- `bid_qty` - Bid quantity
- `ask_qty` - Ask quantity

## API Endpoints

- `GET /` - Dashboard UI
- `GET/POST /config` - Configuration management
- `GET /metrics` - Real-time metrics
- `POST /start_stream` - Start data streaming
- `POST /stop_stream` - Stop data streaming
- `GET /health` - Health check

## License

GNU Affero General Public License v3.0 (AGPL-3.0)

## Support

For issues and feature requests, please open an issue on GitHub.