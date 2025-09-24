from openalgo_wrapper import QuietOpenAlgoAPI as api
import logging
import threading
import time
from typing import Callable, List, Dict, Optional

logger = logging.getLogger(__name__)

class OpenAlgoStreamClient:
    def __init__(self, api_key: str, rest_host: str = "http://127.0.0.1:5000",
                 ws_url: str = "ws://127.0.0.1:8765", on_data_callback: Optional[Callable] = None):
        """
        Initialize OpenAlgo streaming client using the official SDK
        """
        self.api_key = api_key
        self.rest_host = rest_host
        self.ws_url = ws_url
        self.on_data_callback = on_data_callback
        self.client = None
        self.connected = False
        self.subscriptions = {
            'ltp': [],
            'quote': [],
            'depth': []
        }
        self.running = False
        self.thread = None

    def connect(self):
        """Connect to OpenAlgo WebSocket"""
        try:
            self.client = api(
                api_key=self.api_key,
                host=self.rest_host,
                ws_url=self.ws_url
            )
            self.client.connect()
            self.connected = True
            logger.info("Successfully connected to OpenAlgo WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OpenAlgo: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from OpenAlgo WebSocket"""
        try:
            if self.client and self.connected:
                # Unsubscribe from all active streams
                for stream_type, instruments in self.subscriptions.items():
                    if instruments:
                        if stream_type == 'ltp':
                            self.client.unsubscribe_ltp(instruments)
                        elif stream_type == 'quote':
                            self.client.unsubscribe_quote(instruments)
                        elif stream_type == 'depth':
                            self.client.unsubscribe_depth(instruments)

                self.client.disconnect()
                self.connected = False
                logger.info("Disconnected from OpenAlgo WebSocket")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    def on_ltp_update(self, data):
        """Process LTP updates"""
        try:
            # Handle nested data structure from WebSocket
            # Format: {"type": "market_data", "mode": 1, "data": {"ltp": 1424.0}}
            if isinstance(data, dict):
                # Check if data is nested
                if 'data' in data and isinstance(data['data'], dict):
                    ltp_value = data['data'].get('ltp')
                    symbol = data.get('symbol') or data['data'].get('symbol')
                    exchange = data.get('exchange') or data['data'].get('exchange')
                else:
                    # Fallback to direct access
                    ltp_value = data.get('ltp') or data.get('last_price') or data.get('price') or data.get('close')
                    symbol = data.get('symbol')
                    exchange = data.get('exchange')
            else:
                ltp_value = None
                symbol = None
                exchange = None

            processed_data = {
                'type': 'ltp',
                'symbol': symbol,
                'exchange': exchange,
                'ltp': ltp_value,
                'timestamp': data.get('timestamp', time.time())
            }

            # Log the raw data to debug
            if ltp_value is None:
                logger.warning(f"No LTP value found in data: {data}")

            if self.on_data_callback:
                self.on_data_callback(processed_data)

        except Exception as e:
            logger.error(f"Error processing LTP update: {e}")

    def on_quote_update(self, data):
        """Process Quote updates"""
        try:
            # Handle nested data structure from WebSocket
            # Format: {"type": "market_data", "mode": 2, "data": {...}}
            if isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], dict):
                    quote_data = data['data']
                    symbol = data.get('symbol') or quote_data.get('symbol')
                    exchange = data.get('exchange') or quote_data.get('exchange')
                else:
                    quote_data = data
                    symbol = data.get('symbol')
                    exchange = data.get('exchange')

                # Extract LTP from quote data - it might be in different fields
                ltp_value = (quote_data.get('ltp') or
                            quote_data.get('last_price') or
                            quote_data.get('close') or
                            quote_data.get('last') or
                            # If no LTP, use mid-point of bid-ask
                            ((quote_data.get('bid', 0) + quote_data.get('ask', 0)) / 2 if quote_data.get('bid') and quote_data.get('ask') else None))
            else:
                quote_data = {}
                ltp_value = None
                symbol = None
                exchange = None

            processed_data = {
                'type': 'quote',
                'symbol': symbol,
                'exchange': exchange,
                'ltp': ltp_value,  # Add LTP to quote data
                'bid': quote_data.get('bid'),
                'ask': quote_data.get('ask'),
                'bid_qty': quote_data.get('bid_qty'),
                'ask_qty': quote_data.get('ask_qty'),
                'volume': quote_data.get('volume'),
                'oi': quote_data.get('oi') or quote_data.get('open_interest'),
                'timestamp': data.get('timestamp', time.time())
            }

            # Log if we still don't have price data
            if ltp_value is None:
                logger.warning(f"No price found in quote data: {data}")

            if self.on_data_callback:
                self.on_data_callback(processed_data)

        except Exception as e:
            logger.error(f"Error processing Quote update: {e}")

    def on_depth_update(self, data):
        """Process Depth updates"""
        try:
            processed_data = {
                'type': 'depth',
                'symbol': data.get('symbol'),
                'exchange': data.get('exchange'),
                'depth': data.get('depth', []),
                'timestamp': data.get('timestamp', time.time())
            }

            if self.on_data_callback:
                self.on_data_callback(processed_data)

        except Exception as e:
            logger.error(f"Error processing Depth update: {e}")

    def subscribe_ltp(self, instruments: List[Dict]):
        """Subscribe to LTP stream"""
        if not self.connected:
            if not self.connect():
                logger.error("Failed to connect for LTP subscription")
                return False

        try:
            self.client.subscribe_ltp(instruments, on_data_received=self.on_ltp_update)
            self.subscriptions['ltp'] = instruments
            logger.info(f"Subscribed to LTP for {len(instruments)} instruments")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to LTP: {e}")
            return False

    def subscribe_quote(self, instruments: List[Dict]):
        """Subscribe to Quote stream"""
        if not self.connected:
            if not self.connect():
                logger.error("Failed to connect for Quote subscription")
                return False

        try:
            self.client.subscribe_quote(instruments, on_data_received=self.on_quote_update)
            self.subscriptions['quote'] = instruments
            logger.info(f"Subscribed to Quote for {len(instruments)} instruments")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to Quote: {e}")
            return False

    def subscribe_depth(self, instruments: List[Dict]):
        """Subscribe to Depth stream"""
        if not self.connected:
            if not self.connect():
                logger.error("Failed to connect for Depth subscription")
                return False

        try:
            self.client.subscribe_depth(instruments, on_data_received=self.on_depth_update)
            self.subscriptions['depth'] = instruments
            logger.info(f"Subscribed to Depth for {len(instruments)} instruments")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to Depth: {e}")
            return False

    def unsubscribe_ltp(self, instruments: List[Dict]):
        """Unsubscribe from LTP stream"""
        if self.connected and self.client:
            try:
                self.client.unsubscribe_ltp(instruments)
                self.subscriptions['ltp'] = []
                logger.info("Unsubscribed from LTP")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from LTP: {e}")

    def unsubscribe_quote(self, instruments: List[Dict]):
        """Unsubscribe from Quote stream"""
        if self.connected and self.client:
            try:
                self.client.unsubscribe_quote(instruments)
                self.subscriptions['quote'] = []
                logger.info("Unsubscribed from Quote")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from Quote: {e}")

    def unsubscribe_depth(self, instruments: List[Dict]):
        """Unsubscribe from Depth stream"""
        if self.connected and self.client:
            try:
                self.client.unsubscribe_depth(instruments)
                self.subscriptions['depth'] = []
                logger.info("Unsubscribed from Depth")
            except Exception as e:
                logger.error(f"Failed to unsubscribe from Depth: {e}")

    def start(self):
        """Start the client in a background thread"""
        if self.running:
            return

        self.running = True
        self.connect()

    def stop(self):
        """Stop the client"""
        self.running = False
        self.disconnect()

    def get_quote(self, symbol: str, exchange: str):
        """Get real-time quote for a symbol"""
        if self.client and self.connected:
            try:
                return self.client.quotes(symbol=symbol, exchange=exchange)
            except Exception as e:
                logger.error(f"Failed to get quote: {e}")
                return None
        return None

    def get_depth(self, symbol: str, exchange: str):
        """Get market depth for a symbol"""
        if self.client and self.connected:
            try:
                return self.client.depth(symbol=symbol, exchange=exchange)
            except Exception as e:
                logger.error(f"Failed to get depth: {e}")
                return None
        return None