import asyncio
import websockets
import json
import logging
from typing import Callable, List, Dict
from threading import Thread

logger = logging.getLogger(__name__)

class OpenAlgoWebSocketClient:
    def __init__(self, api_key: str, ws_url: str = "ws://127.0.0.1:8765", on_data_callback: Callable = None):
        self.api_key = api_key
        self.ws_url = ws_url
        self.on_data_callback = on_data_callback
        self.websocket = None
        self.running = False
        self.loop = None
        self.thread = None
        self.subscriptions = {
            'ltp': [],
            'quote': [],
            'depth': []
        }

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.ws_url)

            # Authenticate
            auth_message = {
                "type": "auth",
                "api_key": self.api_key
            }
            await self.websocket.send(json.dumps(auth_message))

            response = await self.websocket.recv()
            auth_response = json.loads(response)

            if auth_response.get("status") not in ["authenticated", "success"]:
                raise Exception(f"Authentication failed: {auth_response}")

            logger.info("Successfully connected and authenticated to OpenAlgo WebSocket")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False

    async def subscribe_stream(self, stream_type: str, instruments: List[Dict]):
        if not self.websocket:
            logger.error("WebSocket not connected")
            return False

        try:
            subscribe_message = {
                "type": "subscribe",
                "stream": stream_type,
                "instruments": instruments
            }
            await self.websocket.send(json.dumps(subscribe_message))

            # Store subscription for reconnection
            self.subscriptions[stream_type] = instruments

            logger.info(f"Subscribed to {stream_type} for {len(instruments)} instruments")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {stream_type}: {e}")
            return False

    async def unsubscribe_stream(self, stream_type: str, instruments: List[Dict]):
        if not self.websocket:
            return False

        try:
            unsubscribe_message = {
                "type": "unsubscribe",
                "stream": stream_type,
                "instruments": instruments
            }
            await self.websocket.send(json.dumps(unsubscribe_message))

            # Update subscriptions
            self.subscriptions[stream_type] = []

            logger.info(f"Unsubscribed from {stream_type}")
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {stream_type}: {e}")
            return False

    async def listen(self):
        while self.running:
            try:
                if not self.websocket:
                    await self.connect()
                    await self.resubscribe_all()

                message = await self.websocket.recv()
                data = json.loads(message)

                # Process data based on type
                if data.get("type") == "ltp":
                    self.process_ltp_data(data)
                elif data.get("type") == "quote":
                    self.process_quote_data(data)
                elif data.get("type") == "depth":
                    self.process_depth_data(data)
                elif data.get("type") == "error":
                    logger.error(f"Error from server: {data.get('message')}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, attempting to reconnect...")
                self.websocket = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in WebSocket listener: {e}")
                await asyncio.sleep(1)

    async def resubscribe_all(self):
        for stream_type, instruments in self.subscriptions.items():
            if instruments:
                await self.subscribe_stream(stream_type, instruments)

    def process_ltp_data(self, data):
        processed_data = {
            'type': 'ltp',
            'symbol': data.get('symbol'),
            'exchange': data.get('exchange'),
            'ltp': data.get('ltp'),
            'timestamp': data.get('timestamp')
        }

        if self.on_data_callback:
            self.on_data_callback(processed_data)

    def process_quote_data(self, data):
        processed_data = {
            'type': 'quote',
            'symbol': data.get('symbol'),
            'exchange': data.get('exchange'),
            'bid': data.get('bid'),
            'ask': data.get('ask'),
            'bid_qty': data.get('bid_qty'),
            'ask_qty': data.get('ask_qty'),
            'volume': data.get('volume'),
            'oi': data.get('oi'),
            'timestamp': data.get('timestamp')
        }

        if self.on_data_callback:
            self.on_data_callback(processed_data)

    def process_depth_data(self, data):
        processed_data = {
            'type': 'depth',
            'symbol': data.get('symbol'),
            'exchange': data.get('exchange'),
            'depth': data.get('depth', []),
            'timestamp': data.get('timestamp')
        }

        if self.on_data_callback:
            self.on_data_callback(processed_data)

    def subscribe_ltp(self, instruments: List[Dict]):
        if not self.loop or not self.running:
            self.start()
            import time
            time.sleep(0.5)  # Give the event loop time to start

        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.subscribe_stream('ltp', instruments),
                self.loop
            )

    def subscribe_quote(self, instruments: List[Dict]):
        if not self.loop or not self.running:
            self.start()
            import time
            time.sleep(0.5)  # Give the event loop time to start

        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.subscribe_stream('quote', instruments),
                self.loop
            )

    def subscribe_depth(self, instruments: List[Dict]):
        if not self.loop or not self.running:
            self.start()
            import time
            time.sleep(0.5)  # Give the event loop time to start

        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self.subscribe_stream('depth', instruments),
                self.loop
            )

    def unsubscribe_ltp(self, instruments: List[Dict]):
        asyncio.run_coroutine_threadsafe(
            self.unsubscribe_stream('ltp', instruments),
            self.loop
        )

    def unsubscribe_quote(self, instruments: List[Dict]):
        asyncio.run_coroutine_threadsafe(
            self.unsubscribe_stream('quote', instruments),
            self.loop
        )

    def unsubscribe_depth(self, instruments: List[Dict]):
        asyncio.run_coroutine_threadsafe(
            self.unsubscribe_stream('depth', instruments),
            self.loop
        )

    def start(self):
        if self.running:
            return

        self.running = True

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.listen())

        self.thread = Thread(target=run_loop, daemon=True)
        self.thread.start()
        logger.info("WebSocket client started")

    def stop(self):
        self.running = False

        if self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.websocket.close(),
                self.loop
            )

        if self.loop:
            self.loop.stop()

        logger.info("WebSocket client stopped")

    def run(self):
        self.start()
        try:
            while self.running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()