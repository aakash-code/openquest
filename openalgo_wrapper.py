"""
Wrapper for OpenAlgo API that suppresses print statements
"""
import sys
import io
from contextlib import redirect_stdout
from openalgo import api as openalgo_api

class QuietOpenAlgoAPI:
    """Wrapper around OpenAlgo API that suppresses print statements"""

    def __init__(self, *args, **kwargs):
        # Create a string buffer to capture output
        self.buffer = io.StringIO()

        # Initialize the actual API
        with redirect_stdout(self.buffer):
            self.api = openalgo_api(*args, **kwargs)

    def __getattr__(self, name):
        """Proxy all attribute access to the wrapped API, suppressing output"""
        attr = getattr(self.api, name)

        if callable(attr):
            def wrapper(*args, **kwargs):
                with redirect_stdout(self.buffer):
                    result = attr(*args, **kwargs)
                # Clear buffer after each call
                self.buffer.truncate(0)
                self.buffer.seek(0)
                return result
            return wrapper
        return attr

    def connect(self):
        """Connect with output suppression"""
        with redirect_stdout(self.buffer):
            result = self.api.connect()
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result

    def disconnect(self):
        """Disconnect with output suppression"""
        with redirect_stdout(self.buffer):
            result = self.api.disconnect()
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result

    def subscribe_ltp(self, instruments, on_data_received=None):
        """Subscribe to LTP with output suppression"""
        # Wrap the callback to suppress its output
        def quiet_callback(data):
            with redirect_stdout(self.buffer):
                if on_data_received:
                    on_data_received(data)
            self.buffer.truncate(0)
            self.buffer.seek(0)

        with redirect_stdout(self.buffer):
            result = self.api.subscribe_ltp(instruments, on_data_received=quiet_callback)
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result

    def subscribe_quote(self, instruments, on_data_received=None):
        """Subscribe to Quote with output suppression"""
        # Wrap the callback to suppress its output
        def quiet_callback(data):
            with redirect_stdout(self.buffer):
                if on_data_received:
                    on_data_received(data)
            self.buffer.truncate(0)
            self.buffer.seek(0)

        with redirect_stdout(self.buffer):
            result = self.api.subscribe_quote(instruments, on_data_received=quiet_callback)
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result

    def subscribe_depth(self, instruments, on_data_received=None):
        """Subscribe to Depth with output suppression"""
        # Wrap the callback to suppress its output
        def quiet_callback(data):
            with redirect_stdout(self.buffer):
                if on_data_received:
                    on_data_received(data)
            self.buffer.truncate(0)
            self.buffer.seek(0)

        with redirect_stdout(self.buffer):
            result = self.api.subscribe_depth(instruments, on_data_received=quiet_callback)
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result

    def unsubscribe_ltp(self, instruments):
        """Unsubscribe from LTP with output suppression"""
        with redirect_stdout(self.buffer):
            result = self.api.unsubscribe_ltp(instruments)
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result

    def unsubscribe_quote(self, instruments):
        """Unsubscribe from Quote with output suppression"""
        with redirect_stdout(self.buffer):
            result = self.api.unsubscribe_quote(instruments)
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result

    def unsubscribe_depth(self, instruments):
        """Unsubscribe from Depth with output suppression"""
        with redirect_stdout(self.buffer):
            result = self.api.unsubscribe_depth(instruments)
        self.buffer.truncate(0)
        self.buffer.seek(0)
        return result