#!/usr/bin/env python
"""
Quiet runner for OpenQuest that suppresses all print statements from OpenAlgo SDK
"""
import sys
import os
import io
import threading

class OutputSuppressor:
    """Context manager to suppress stdout"""
    def __init__(self):
        self.null = open(os.devnull, 'w')

    def __enter__(self):
        self.old_stdout = sys.stdout
        sys.stdout = self.null
        return self

    def __exit__(self, *args):
        sys.stdout = self.old_stdout
        self.null.close()

# Monkey patch print function for OpenAlgo module
import builtins
original_print = builtins.print

def silent_print(*args, **kwargs):
    """Print function that filters out OpenAlgo Quote messages"""
    message = ' '.join(str(arg) for arg in args)

    # Filter out unwanted messages
    if any(keyword in message for keyword in ['Quote MCX:', 'Subscribing to', 'Subscription response:', 'Unsubscribing from']):
        return  # Suppress these messages

    # Allow other messages
    original_print(*args, **kwargs)

# Replace the built-in print
builtins.print = silent_print

# Now import and run the app
if __name__ == '__main__':
    from app import app, socketio, candle_aggregator

    # Start candle aggregator
    candle_aggregator.start()

    print("=" * 60)
    print("OpenQuest Started - Real-Time Data Aggregation")
    print("Dashboard: http://127.0.0.1:5001")
    print("Charts: http://127.0.0.1:5001/chart")
    print("=" * 60)

    # Run with SocketIO
    socketio.run(
        app,
        debug=False,
        port=5001,
        host='127.0.0.1',
        use_reloader=False,
        log_output=True
    )