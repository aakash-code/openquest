import json
import os
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")

        # Return default configuration
        return {
            'api_key': '',
            'rest_host': 'http://127.0.0.1:5000',
            'ws_url': 'ws://127.0.0.1:8765',
            'questdb_host': 'http://127.0.0.1:9000',
            'questdb_port': 8812,
            'questdb_user': 'admin',
            'questdb_password': 'quest',
            'ltp_enabled': True,
            'quote_enabled': True,
            'depth_enabled': False,
            'enabled': False
        }

    def save_config(self) -> bool:
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_config(self) -> Dict[str, Any]:
        return self.config.copy()

    def update_config(self, updates: Dict[str, Any]) -> bool:
        self.config.update(updates)
        return self.save_config()

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        self.config[key] = value
        return self.save_config()

    def validate_config(self) -> tuple[bool, str]:
        """Validate configuration settings"""
        if not self.config.get('api_key'):
            return False, "API key is required"

        if not self.config.get('rest_host'):
            return False, "REST API host is required"

        if not self.config.get('ws_url'):
            return False, "WebSocket URL is required"

        # Check at least one stream is enabled
        streams = ['ltp_enabled', 'quote_enabled', 'depth_enabled']
        if not any(self.config.get(stream, False) for stream in streams):
            return False, "At least one stream must be enabled"

        return True, "Configuration is valid"

    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values"""
        self.config = {
            'api_key': '',
            'rest_host': 'http://127.0.0.1:5000',
            'ws_url': 'ws://127.0.0.1:8765',
            'questdb_host': 'http://127.0.0.1:9000',
            'questdb_port': 8812,
            'questdb_user': 'admin',
            'questdb_password': 'quest',
            'ltp_enabled': True,
            'quote_enabled': True,
            'depth_enabled': False,
            'enabled': False
        }
        return self.save_config()