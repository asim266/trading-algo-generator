"""
Configuration Manager for Trading Algo Generator
Supports config.ini (local dev) with environment variable overrides (production).
"""

import configparser
import os
import logging

logger = logging.getLogger(__name__)


def _env(key, fallback=None):
    """Get environment variable or return fallback."""
    return os.environ.get(key, fallback)


class Config:
    """Configuration manager - env vars take priority over config.ini"""

    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self._has_file = os.path.exists(self.config_file)
        if self._has_file:
            self.config.read(self.config_file)
            logger.info(f"Configuration loaded from {self.config_file}")
        else:
            logger.info("No config.ini found, using environment variables")

    def _get(self, section, key, fallback=None):
        """Get from env var (SECTION_KEY) first, then config.ini, then fallback."""
        env_key = f"{section.upper()}_{key.upper()}"
        env_val = _env(env_key)
        if env_val is not None:
            return env_val
        if self._has_file:
            return self.config.get(section, key, fallback=fallback)
        return fallback

    def _getint(self, section, key, fallback=0):
        val = self._get(section, key, fallback=str(fallback))
        return int(val)

    def _getfloat(self, section, key, fallback=0.0):
        val = self._get(section, key, fallback=str(fallback))
        return float(val)

    def _getbool(self, section, key, fallback=False):
        val = self._get(section, key, fallback=str(fallback))
        return str(val).lower() in ('true', '1', 'yes')

    # Moonshot API configuration
    def get_moonshot_api_key(self):
        return self._get('moonshot', 'api_key', '')

    def get_moonshot_base_url(self):
        return self._get('moonshot', 'base_url', 'https://api.moonshot.ai/v1')

    def get_moonshot_model(self):
        return self._get('moonshot', 'model', 'kimi-k2-thinking')

    def get_moonshot_code_model(self):
        return self._get('moonshot', 'code_model', 'kimi-k2-thinking')

    def get_moonshot_debug_model(self):
        return self._get('moonshot', 'debug_model', 'kimi-k2-thinking-turbo')

    def get_max_tokens_prompt(self):
        return self._getint('moonshot', 'max_tokens_prompt', 10000)

    def get_max_tokens_code(self):
        return self._getint('moonshot', 'max_tokens_code', 10000)

    def get_max_tokens_fix(self):
        return self._getint('moonshot', 'max_tokens_fix', 10000)

    # Code generation configuration
    def get_temperature_prompt(self):
        return self._getfloat('code_generation', 'temperature_prompt', 1.0)

    def get_temperature_code(self):
        return self._getfloat('code_generation', 'temperature_code', 1.0)

    def get_temperature_fix(self):
        return self._getfloat('code_generation', 'temperature_fix', 1.0)

    def get_max_fix_attempts(self):
        return self._getint('code_generation', 'max_fix_attempts', 5)

    def get_execution_timeout(self):
        return self._getint('code_generation', 'execution_timeout', 60)

    # Rate limit configuration
    def get_max_requests_per_day(self):
        return self._getint('rate_limit', 'max_requests_per_day', 2)

    # Flask configuration
    def get_flask_host(self):
        return self._get('flask', 'host', '0.0.0.0')

    def get_flask_port(self):
        return self._getint('flask', 'port', int(_env('PORT', '5000')))

    def get_flask_debug(self):
        return self._getbool('flask', 'debug', False)

    def get_flask_secret_key(self):
        return self._get('flask', 'secret_key', 'dev-secret-key')

    # File configuration
    def get_generated_code_file(self):
        return self._get('files', 'generated_code_file', 'generated_code.py')

    def get_final_code_file(self):
        return self._get('files', 'final_code_file', 'final_code.py')

    def get_attempt_code_prefix(self):
        return self._get('files', 'attempt_code_prefix', 'attempt_')

    def get_attempt_code_suffix(self):
        return self._get('files', 'attempt_code_suffix', '_code.py')

    # Safety configuration
    def is_timeout_enabled(self):
        return self._getbool('safety', 'enable_timeout', True)

    def is_cleanup_temp_files_enabled(self):
        return self._getbool('safety', 'cleanup_temp_files', True)

    def is_log_execution_enabled(self):
        return self._getbool('safety', 'log_execution', True)

    # Supabase configuration
    def get_supabase_url(self):
        return self._get('supabase', 'url', '')

    def get_supabase_key(self):
        return self._get('supabase', 'key', '')

    def get_supabase_storage_bucket(self):
        return self._get('supabase', 'storage_bucket', 'python-codes')


# Global configuration instance
_config_instance = None

def get_config():
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def reload_config():
    """Reload configuration from file"""
    global _config_instance
    _config_instance = Config()
    return _config_instance
