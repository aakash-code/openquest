#!/usr/bin/env python
"""
OpenQuest - Real-Time Data Aggregation for OpenAlgo
"""

import os
import sys
import logging
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required services are accessible"""
    import requests
    import psycopg2

    checks = {
        'QuestDB': False,
        'OpenAlgo': False
    }

    # Check QuestDB
    try:
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=8812,
            database='qdb',
            user='admin',
            password='quest'
        )
        conn.close()
        checks['QuestDB'] = True
        logger.info("✓ QuestDB connection successful")
    except Exception as e:
        logger.warning(f"✗ QuestDB connection failed: {e}")
        logger.warning("  Please ensure QuestDB is running at http://127.0.0.1:9000")

    # Check OpenAlgo (optional at startup)
    try:
        response = requests.get('http://127.0.0.1:5000/api/v1/health', timeout=2)
        if response.status_code == 200:
            checks['OpenAlgo'] = True
            logger.info("✓ OpenAlgo REST API accessible")
    except:
        logger.info("  OpenAlgo not detected - configure in the dashboard when ready")

    return checks

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("OpenQuest - Real-Time Data Aggregation for OpenAlgo")
    logger.info("=" * 60)

    # Check dependencies
    logger.info("\nChecking services...")
    checks = check_dependencies()

    if not checks['QuestDB']:
        logger.error("\nQuestDB is required but not accessible.")
        logger.error("Please start QuestDB before running OpenQuest.")
        logger.error("Download: https://questdb.io/download/")
        sys.exit(1)

    # Start Flask application
    logger.info("\nStarting OpenQuest server...")
    logger.info("Dashboard: http://127.0.0.1:5001")
    logger.info("Press Ctrl+C to stop\n")

    try:
        # Import here to avoid circular import
        from app import socketio, candle_aggregator

        # Start candle aggregator
        candle_aggregator.start()
        logger.info("Candle aggregator started")

        # Run with SocketIO
        socketio.run(
            app,
            host='127.0.0.1',
            port=5001,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down OpenQuest...")
        candle_aggregator.stop()
        sys.exit(0)