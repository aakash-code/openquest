from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import os
import sys
import io
from datetime import datetime
import threading
import logging
from config_manager import ConfigManager
from questdb_client import QuestDBClient
from openalgo_client import OpenAlgoStreamClient
from candle_aggregator import CandleAggregator

# Suppress stdout from OpenAlgo SDK
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set base level to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific loggers
logging.getLogger('openalgo_client').setLevel(logging.WARNING)  # Only warnings and errors
logging.getLogger('candle_aggregator').setLevel(logging.INFO)
logging.getLogger('questdb_client').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask request logs
logging.getLogger('openalgo').setLevel(logging.ERROR)  # Suppress OpenAlgo SDK debug output
logging.getLogger('urllib3').setLevel(logging.WARNING)  # Suppress urllib3 debug
logging.getLogger('engineio').setLevel(logging.WARNING)  # Suppress engineio debug
logging.getLogger('socketio').setLevel(logging.WARNING)  # Suppress socketio debug

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=False)

# Initialize managers
config_manager = ConfigManager()
questdb_client = QuestDBClient()
stream_client = None
candle_aggregator = CandleAggregator(questdb_client)

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
            if 'bid' in data and 'ask' in data and data['bid'] is not None and data['ask'] is not None:
                spread = data['ask'] - data['bid']
                metrics['spreads'][symbol] = spread

            # Data is already being streamed to charts via OpenAlgo WebSocket
            # No need for separate broadcasting

            # Store in QuestDB
            if 'ltp' in data and data['ltp'] is not None:
                success = questdb_client.insert_ltp(symbol, data['ltp'])
                if not success:
                    app.logger.warning(f"Failed to store LTP for {symbol}")

            if 'bid' in data and 'ask' in data and data['bid'] is not None and data['ask'] is not None:
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

@app.route('/chart')
def chart():
    return render_template('chart.html', symbols=MCX_SYMBOLS)

@app.route('/api/candles/<symbol>')
def get_candles(symbol):
    """Get aggregated candle data for a symbol from QuestDB"""
    timeframe = request.args.get('timeframe', '1m')
    limit = int(request.args.get('limit', 500))

    try:
        # Try to get aggregated candles first
        candles = candle_aggregator.get_historical_candles(symbol, timeframe, limit)

        # If no candles, try to get raw tick data and convert to candles
        if not candles:
            app.logger.info(f"No aggregated candles for {symbol}, fetching raw ticks")

            # Get raw ticks from QuestDB
            query = """
            SELECT timestamp, ltp
            FROM ticks_ltp
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """
            questdb_client.cursor.execute(query, (symbol, limit))
            ticks = questdb_client.cursor.fetchall()

            if ticks:
                # Convert ticks to simple candles
                candles = []
                for tick in reversed(ticks):
                    if tick[0] and tick[1]:
                        candles.append({
                            'time': int(tick[0].timestamp()),
                            'open': float(tick[1]),
                            'high': float(tick[1]),
                            'low': float(tick[1]),
                            'close': float(tick[1]),
                            'volume': 1
                        })
                app.logger.info(f"Created {len(candles)} candles from ticks")

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'timeframe': timeframe,
            'candles': candles,
            'count': len(candles)
        })

    except Exception as e:
        app.logger.error(f"Error fetching candles for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'symbol': symbol
        }), 500

# WebSocket events for real-time candle streaming
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    app.logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to candle stream'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    app.logger.info(f"Client disconnected: {request.sid}")

@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to candle updates for a symbol"""
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', '1m')

    if symbol:
        # Join room for this symbol-timeframe combination
        room = f"{symbol}_{timeframe}"
        join_room(room)

        app.logger.info(f"Client {request.sid} subscribed to {room}")

        # Send current candle immediately
        candle = candle_aggregator._get_current_candle(symbol, timeframe)
        if candle:
            emit('candle_update', {
                'symbol': symbol,
                'timeframe': timeframe,
                'candle': candle
            })

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Unsubscribe from candle updates"""
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', '1m')

    if symbol:
        room = f"{symbol}_{timeframe}"
        leave_room(room)
        app.logger.info(f"Client {request.sid} unsubscribed from {room}")

def broadcast_candle_update(symbol, timeframe, candle):
    """Broadcast candle update to subscribed clients"""
    room = f"{symbol}_{timeframe}"
    socketio.emit('candle_update', {
        'symbol': symbol,
        'timeframe': timeframe,
        'candle': candle
    }, room=room)

if __name__ == '__main__':
    # Start candle aggregator
    candle_aggregator.start()
    app.logger.info("=" * 60)
    app.logger.info("OpenQuest Started - Real-Time Data Aggregation")
    app.logger.info("Dashboard: http://127.0.0.1:5001")
    app.logger.info("Charts: http://127.0.0.1:5001/chart")
    app.logger.info("=" * 60)

    # Run with SocketIO in production mode with logging
    socketio.run(
        app,
        debug=False,  # Disable debug mode for production
        port=5001,
        host='127.0.0.1',
        use_reloader=False,  # Disable auto-reloader
        log_output=True  # Enable logging output
    )