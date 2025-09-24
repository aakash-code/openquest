from flask import Flask, render_template, request, jsonify, session
import json
import os
from datetime import datetime
import threading
from config_manager import ConfigManager
from questdb_client import QuestDBClient
from openalgo_client import OpenAlgoStreamClient

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize managers
config_manager = ConfigManager()
questdb_client = QuestDBClient()
stream_client = None

# Store real-time metrics
metrics = {
    'tick_rate': {},
    'last_update': {},
    'spreads': {},
    'imbalance': {},
    'total_ticks': 0,
    'active_symbols': 0,
    'connection_status': 'disconnected'
}

# Load MCX symbols
def load_mcx_symbols():
    symbols_file = os.path.join(os.path.dirname(__file__), 'docs', 'mcxsymbol.txt')
    if os.path.exists(symbols_file):
        with open(symbols_file, 'r') as f:
            return json.load(f)
    return []

MCX_SYMBOLS = load_mcx_symbols()

@app.route('/')
def index():
    config = config_manager.get_config()
    return render_template('index.html',
                         config=config,
                         metrics=metrics,
                         symbols=MCX_SYMBOLS)

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        data = request.json
        config_manager.update_config(data)

        # Restart WebSocket connection with new config
        global stream_client
        if stream_client:
            stream_client.stop()

        if data.get('enabled'):
            start_websocket_client(data)

        return jsonify({'status': 'success', 'message': 'Configuration updated'})

    return jsonify(config_manager.get_config())

@app.route('/metrics')
def get_metrics():
    return jsonify(metrics)

@app.route('/start_stream', methods=['POST'])
def start_stream():
    data = request.json
    stream_type = data.get('stream_type', 'ltp')
    symbols = data.get('symbols', MCX_SYMBOLS)

    config = config_manager.get_config()
    if not config.get('api_key'):
        return jsonify({'status': 'error', 'message': 'API key not configured'})

    global stream_client

    try:
        if not stream_client:
            stream_client = OpenAlgoStreamClient(
                api_key=config['api_key'],
                rest_host=config.get('rest_host', 'http://127.0.0.1:5000'),
                ws_url=config.get('ws_url', 'ws://127.0.0.1:8765'),
                on_data_callback=handle_websocket_data
            )
            stream_client.start()

        # Subscribe to streams based on type
        success = False
        if stream_type == 'ltp':
            success = stream_client.subscribe_ltp(symbols)
        elif stream_type == 'quote':
            success = stream_client.subscribe_quote(symbols)
        elif stream_type == 'depth':
            success = stream_client.subscribe_depth(symbols)

        if success:
            metrics['connection_status'] = 'connected'
            metrics['active_symbols'] = len(symbols)
            return jsonify({'status': 'success', 'message': f'Started {stream_type} stream for {len(symbols)} symbols'})
        else:
            metrics['connection_status'] = 'disconnected'
            return jsonify({'status': 'error', 'message': f'Failed to start {stream_type} stream'})

    except Exception as e:
        app.logger.error(f"Error starting stream: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    global stream_client
    if stream_client:
        stream_client.stop()
        stream_client = None
        metrics['connection_status'] = 'disconnected'
        return jsonify({'status': 'success', 'message': 'Stream stopped'})

    return jsonify({'status': 'error', 'message': 'No active stream'})

def handle_websocket_data(data):
    """Handle incoming WebSocket data"""
    try:
        # Update metrics
        symbol = data.get('symbol')
        if symbol:
            metrics['last_update'][symbol] = datetime.now().isoformat()

            # Update tick rate
            if symbol not in metrics['tick_rate']:
                metrics['tick_rate'][symbol] = 0
            metrics['tick_rate'][symbol] += 1
            metrics['total_ticks'] += 1

            # Calculate spread if bid/ask available
            if 'bid' in data and 'ask' in data:
                spread = data['ask'] - data['bid']
                metrics['spreads'][symbol] = spread

            # Store in QuestDB
            if 'ltp' in data:
                questdb_client.insert_ltp(symbol, data['ltp'])

            if 'bid' in data and 'ask' in data:
                questdb_client.insert_quote(
                    symbol=symbol,
                    bid=data['bid'],
                    ask=data['ask'],
                    spread=data.get('spread', data['ask'] - data['bid']),
                    volume=data.get('volume', 0),
                    open_interest=data.get('oi', 0)
                )

            if 'depth' in data:
                for level, depth_data in enumerate(data['depth']):
                    questdb_client.insert_depth(
                        symbol=symbol,
                        level=level,
                        bid=depth_data.get('bid', 0),
                        ask=depth_data.get('ask', 0),
                        bid_qty=depth_data.get('bid_qty', 0),
                        ask_qty=depth_data.get('ask_qty', 0)
                    )
    except Exception as e:
        app.logger.error(f"Error handling WebSocket data: {e}")

def start_websocket_client(config):
    """Start WebSocket client in background thread"""
    def run_ws():
        global stream_client
        stream_client = OpenAlgoStreamClient(
            api_key=config['api_key'],
            rest_host=config.get('rest_host', 'http://127.0.0.1:5000'),
            ws_url=config.get('ws_url', 'ws://127.0.0.1:8765'),
            on_data_callback=handle_websocket_data
        )
        stream_client.start()

        # Subscribe to all enabled streams for all MCX symbols
        if config.get('ltp_enabled'):
            stream_client.subscribe_ltp(MCX_SYMBOLS)
        if config.get('quote_enabled'):
            stream_client.subscribe_quote(MCX_SYMBOLS)
        if config.get('depth_enabled'):
            stream_client.subscribe_depth(MCX_SYMBOLS)

    thread = threading.Thread(target=run_ws, daemon=True)
    thread.start()

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'questdb_connected': questdb_client.is_connected(),
        'websocket_connected': metrics['connection_status'] == 'connected',
        'total_ticks': metrics['total_ticks']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)