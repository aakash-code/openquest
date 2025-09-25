import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class CandleAggregator:
    """Aggregates tick data into candles and streams updates"""

    def __init__(self, questdb_client):
        self.questdb = questdb_client
        self.current_candles = {}  # {symbol: {timeframe: candle_data}}
        self.subscribers = set()  # WebSocket connections subscribed to candle updates
        self.running = False
        self.thread = None

    def start(self):
        """Start the aggregator in a background thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_aggregator, daemon=True)
        self.thread.start()
        logger.info("Candle aggregator started")

    def stop(self):
        """Stop the aggregator"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Candle aggregator stopped")

    def _run_aggregator(self):
        """Main aggregation loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._aggregate_loop())

    async def _aggregate_loop(self):
        """Continuously aggregate candles"""
        while self.running:
            try:
                await self._update_all_candles()
                await asyncio.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                await asyncio.sleep(5)

    async def _update_all_candles(self):
        """Update candles for all active symbols"""
        # Get list of symbols with recent data
        symbols = self._get_active_symbols()

        for symbol in symbols:
            try:
                # Generate candles for different timeframes
                for timeframe in ['1m', '5m', '15m', '1h']:
                    candle = self._get_current_candle(symbol, timeframe)
                    if candle:
                        await self._broadcast_candle(symbol, timeframe, candle)
            except Exception as e:
                logger.error(f"Error updating candles for {symbol}: {e}")

    def _get_active_symbols(self) -> List[str]:
        """Get list of symbols with recent data"""
        try:
            # Query for symbols with data in last 5 minutes
            # QuestDB uses dateadd() function for time arithmetic
            query = """
            SELECT DISTINCT symbol
            FROM ticks_ltp
            WHERE timestamp > dateadd('m', -5, now())
            """
            self.questdb.cursor.execute(query)
            results = self.questdb.cursor.fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting active symbols: {e}")
            # Fallback to simpler query
            try:
                query = """
                SELECT DISTINCT symbol
                FROM ticks_ltp
                LIMIT 50
                """
                self.questdb.cursor.execute(query)
                results = self.questdb.cursor.fetchall()
                return [row[0] for row in results]
            except:
                return []

    def _get_current_candle(self, symbol: str, timeframe: str) -> Dict:
        """Get current candle for symbol and timeframe"""
        try:
            # Calculate time window for current candle
            now = datetime.now()  # Use local time

            if timeframe == '1m':
                start_time = now.replace(second=0, microsecond=0)
            elif timeframe == '5m':
                minutes = (now.minute // 5) * 5
                start_time = now.replace(minute=minutes, second=0, microsecond=0)
            elif timeframe == '15m':
                minutes = (now.minute // 15) * 15
                start_time = now.replace(minute=minutes, second=0, microsecond=0)
            elif timeframe == '1h':
                start_time = now.replace(minute=0, second=0, microsecond=0)
            else:
                start_time = now.replace(second=0, microsecond=0)

            # Query for OHLCV data in current window
            # Note: 'volume' column in ticks_ltp stores last_trade_quantity
            query = """
            SELECT
                min(timestamp) as time,
                first(ltp) as open,
                max(ltp) as high,
                min(ltp) as low,
                last(ltp) as close,
                COALESCE(sum(volume), 0) as trade_volume
            FROM ticks_ltp
            WHERE symbol = %s
                AND timestamp >= %s
                AND timestamp < now()
            """

            self.questdb.cursor.execute(query, (symbol, start_time))
            result = self.questdb.cursor.fetchone()

            if result and result[0]:  # Check if we have data
                return {
                    'time': int(start_time.timestamp()),
                    'open': float(result[1]) if result[1] else 0,
                    'high': float(result[2]) if result[2] else 0,
                    'low': float(result[3]) if result[3] else 0,
                    'close': float(result[4]) if result[4] else 0,
                    'volume': int(result[5]) if result[5] is not None else 0,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'complete': False  # Current candle is not complete
                }
            return None

        except Exception as e:
            logger.error(f"Error getting candle for {symbol} {timeframe}: {e}")
            return None

    def get_historical_candles(self, symbol: str, timeframe: str, limit: int = 500) -> List[Dict]:
        """Get historical candles from QuestDB"""
        try:
            # Map timeframe to interval
            interval_map = {
                '1m': '1 minute',
                '5m': '5 minutes',
                '15m': '15 minutes',
                '30m': '30 minutes',
                '1h': '1 hour',
                '1d': '1 day'
            }

            interval = interval_map.get(timeframe, '1 minute')

            # Calculate start time based on limit and timeframe
            if timeframe == '1m':
                start_time = datetime.now() - timedelta(minutes=limit)
            elif timeframe == '5m':
                start_time = datetime.now() - timedelta(minutes=limit * 5)
            elif timeframe == '15m':
                start_time = datetime.now() - timedelta(minutes=limit * 15)
            elif timeframe == '1h':
                start_time = datetime.now() - timedelta(hours=limit)
            else:
                start_time = datetime.now() - timedelta(days=1)

            # Get the most recent data from QuestDB
            # Use a subquery to get the latest ticks first
            query = """
            SELECT timestamp, ltp, volume
            FROM (
                SELECT timestamp, ltp, volume
                FROM ticks_ltp
                WHERE symbol = %s
                    AND ltp IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT %s
            ) sub
            ORDER BY timestamp ASC
            """

            # Get enough ticks to fill the requested candles
            ticks_needed = limit * 100 if timeframe == '1m' else limit * 500
            self.questdb.cursor.execute(query, (symbol, ticks_needed))
            results = self.questdb.cursor.fetchall()

            # Aggregate ticks into candles manually
            if results:
                # Group ticks by time period
                from collections import defaultdict

                candle_dict = defaultdict(list)

                # Determine time bucket size based on timeframe
                if timeframe == '1m':
                    bucket_seconds = 60
                elif timeframe == '5m':
                    bucket_seconds = 300
                elif timeframe == '15m':
                    bucket_seconds = 900
                elif timeframe == '30m':
                    bucket_seconds = 1800
                elif timeframe == '1h':
                    bucket_seconds = 3600
                else:
                    bucket_seconds = 60  # Default to 1 minute

                for row in results:
                    if row[0] and row[1]:
                        # The timestamp is already correct - Python's timestamp() gives UTC
                        timestamp = int(row[0].timestamp())
                        bucket = (timestamp // bucket_seconds) * bucket_seconds
                        price = float(row[1])
                        # Handle NULL volumes properly - treat as 0
                        volume = float(row[2]) if row[2] is not None else 0
                        candle_dict[bucket].append((timestamp, price, volume))

                # Create candles from grouped ticks
                candles = []
                for bucket_time in sorted(candle_dict.keys()):
                    tick_data = candle_dict[bucket_time]
                    if tick_data:
                        # Sort ticks within bucket by timestamp
                        tick_data.sort(key=lambda x: x[0])
                        prices = [price for _, price, _ in tick_data]
                        total_volume = sum(vol for _, _, vol in tick_data)
                        # Only add candle if all values are valid
                        if prices and len(prices) > 0:
                            candles.append({
                                'time': bucket_time,
                                'open': prices[0],
                                'high': max(prices),
                                'low': min(prices),
                                'close': prices[-1],
                                'volume': total_volume  # Sum of actual traded volumes
                            })

                return candles[-limit:] if len(candles) > limit else candles

            return []

        except Exception as e:
            logger.error(f"Error getting historical candles: {e}")
            # Fallback to simple query
            try:
                query = """
                SELECT
                    timestamp,
                    ltp as close,
                    COALESCE(volume, 0) as volume
                FROM ticks_ltp
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """
                self.questdb.cursor.execute(query, (symbol, limit))
                results = self.questdb.cursor.fetchall()

                # Create simple candles from ticks
                candles = []
                for row in reversed(results):
                    if row[0]:
                        candles.append({
                            'time': int(row[0].timestamp()),
                            'open': float(row[1]),
                            'high': float(row[1]),
                            'low': float(row[1]),
                            'close': float(row[1]),
                            'volume': int(row[2]) if row[2] is not None else 0  # Use actual volume from DB
                        })
                return candles
            except Exception as e2:
                logger.error(f"Fallback query also failed: {e2}")
                return []

    def subscribe(self, subscriber):
        """Subscribe to candle updates"""
        self.subscribers.add(subscriber)
        logger.info(f"Subscriber added. Total: {len(self.subscribers)}")

    def unsubscribe(self, subscriber):
        """Unsubscribe from candle updates"""
        self.subscribers.discard(subscriber)
        logger.info(f"Subscriber removed. Total: {len(self.subscribers)}")

    async def _broadcast_candle(self, symbol: str, timeframe: str, candle: Dict):
        """Broadcast candle update to all subscribers"""
        if not candle or not self.subscribers:
            return

        message = {
            'type': 'candle',
            'symbol': symbol,
            'timeframe': timeframe,
            'data': candle
        }

        # Store in current candles
        if symbol not in self.current_candles:
            self.current_candles[symbol] = {}
        self.current_candles[symbol][timeframe] = candle

        # Broadcast to subscribers (implement based on your WebSocket setup)
        # This would be connected to your WebSocket implementation