"""
BuyWise-AI Configuration Management Module
==========================================

This module handles application-wide configuration settings using environment variables,
type casting, default values, and strict validation checks.

Key Features:
-------------
- Loads sensitive runtime options via environment settings or `.env` files.
- Provides immutable configuration data structures for system components (Database, AI Models, Logging).
- Includes validation logic to prevent initialization with invalid parameter bounds.

Usage Example:
--------------
>>> from buywise_ai.config import AppConfig, ConfigLoader
>>> config = ConfigLoader.load_config()
>>> print(config.app_env)
'development'
>>> print(config.model.model_name)
'gpt-4o-mini'
"""

import os
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any

# Configure logger for configuration loader operations
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class EnvironmentOption(Enum):
    """Enumeration representing supported system execution environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevelOption(Enum):
    """Enumeration representing standard logging verbosity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# Configuration Data Structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatabaseConfig:
    """Database connectivity and connection pool configurations.
    
    Attributes:
        host (str): Database server hostname.
        port (int): Network port for connection (default: 5432).
        database_name (str): Database identifier name.
        username (str): Database authentication username.
        password (str): Database authentication password.
        max_connections (int): Maximum connection pool allocation size.
    """
    host: str = "localhost"
    port: int = 5432
    database_name: str = "buywise_db"
    username: str = "postgres"
    password: str = "postgres"
    max_connections: int = 20


@dataclass(frozen=True)
class ModelConfig:
    """Settings controlling AI model inference and execution boundaries.
    
    Attributes:
        model_name (str): Identifier string for target machine learning model.
        temperature (float): Controls response variability/creativity (range: 0.0 to 1.0).
        max_tokens (int): Maximum token budget per generation request.
        timeout (int): Request timeout period in seconds.
    """
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout: int = 30


@dataclass(frozen=True)
class AppConfig:
    """Master application configuration container holding system settings.
    
    Attributes:
        app_name (str): Title identifier of the application.
        app_env (EnvironmentOption): Current execution environment state.
        log_level (LogLevelOption): Standard logger severity threshold.
        db (DatabaseConfig): Nested database configurations.
        model (ModelConfig): Nested AI model configurations.
    """
    app_name: str = "BuyWise-AI Engine"
    app_env: EnvironmentOption = EnvironmentOption.DEVELOPMENT
    log_level: LogLevelOption = LogLevelOption.INFO
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    model: ModelConfig = field(default_factory=ModelConfig)


# ---------------------------------------------------------------------------
# Exception Classes
# ---------------------------------------------------------------------------

class ConfigurationError(Exception):
    """Base exception class raised when configuration values fail validation rules."""
    pass


# ---------------------------------------------------------------------------
# Configuration Loader
# ---------------------------------------------------------------------------

class ConfigLoader:
    """Utility class for reading environment variables and constructing AppConfig objects."""

    @staticmethod
    def _get_env_str(key: str, default: str) -> str:
        """Retrieves a string value from environment or returns default."""
        return os.getenv(key, default)

    @staticmethod
    def _get_env_int(key: str, default: int) -> int:
        """Retrieves an integer value from environment or returns default."""
        val = os.getenv(key)
        if val is None:
            return default
        try:
            return int(val)
        except ValueError:
            raise ConfigurationError(f"Environment variable '{key}' must be a valid integer. Got: '{val}'")

    @staticmethod
    def _get_env_float(key: str, default: float) -> float:
        """Retrieves a float value from environment or returns default."""
        val = os.getenv(key)
        if val is None:
            return default
        try:
            return float(val)
        except ValueError:
            raise ConfigurationError(f"Environment variable '{key}' must be a valid float. Got: '{val}'")

    @classmethod
    def load_config(cls) -> AppConfig:
        """Loads and validates application settings from environment configurations.
        
        Returns:
            AppConfig: Fully initialized and validated immutable config instance.
            
        Raises:
            ConfigurationError: If environment attributes fail parsing or validation bounds.
        """
        # Parse Environment string
        raw_env = cls._get_env_str("BUYWISE_ENV", "development").lower()
        try:
            app_env = EnvironmentOption(raw_env)
        except ValueError:
            app_env = EnvironmentOption.DEVELOPMENT
            logger.warning(f"Unrecognized environment '{raw_env}'. Defaulting to 'development'.")

        # Parse Logging level string
        raw_log_level = cls._get_env_str("LOG_LEVEL", "INFO").upper()
        try:
            log_level = LogLevelOption[raw_log_level]
        except KeyError:
            log_level = LogLevelOption.INFO
            logger.warning(f"Unrecognized log level '{raw_log_level}'. Defaulting to 'INFO'.")

        # Construct Database Configuration
        db_config = DatabaseConfig(
            host=cls._get_env_str("DB_HOST", "localhost"),
            port=cls._get_env_int("DB_PORT", 5432),
            database_name=cls._get_env_str("DB_NAME", "buywise_db"),
            username=cls._get_env_str("DB_USER", "postgres"),
            password=cls._get_env_str("DB_PASSWORD", "postgres"),
            max_connections=cls._get_env_int("DB_MAX_CONNECTIONS", 20)
        )

        # Construct Model Configuration
        model_config = ModelConfig(
            model_name=cls._get_env_str("AI_MODEL_NAME", "gpt-4o-mini"),
            temperature=cls._get_env_float("AI_TEMPERATURE", 0.7),
            max_tokens=cls._get_env_int("AI_MAX_TOKENS", 1024),
            timeout=cls._get_env_int("AI_TIMEOUT", 30)
        )

        # Master Config construction
        config = AppConfig(
            app_name=cls._get_env_str("APP_NAME", "BuyWise-AI Engine"),
            app_env=app_env,
            log_level=log_level,
            db=db_config,
            model=model_config
        )

        # Validate attributes
        cls.validate_config(config)

        return config

    @staticmethod
    def validate_config(config: AppConfig) -> None:
        """Validates bounds and logical rules for application options.
        
        Args:
            config (AppConfig): Configuration object to validate.
            
        Raises:
            ConfigurationError: If any parameter value falls outside permitted ranges.
        """
        if not (0.0 <= config.model.temperature <= 1.0):
            raise ConfigurationError(
                f"Invalid temperature setting: {config.model.temperature}. Must be between 0.0 and 1.0."
            )
        
        if config.model.max_tokens <= 0:
            raise ConfigurationError(
                f"Invalid max_tokens value: {config.model.max_tokens}. Must be a positive integer."
            )

        if config.db.port <= 0 or config.db.port > 65535:
            raise ConfigurationError(
                f"Invalid database port: {config.db.port}. Must be a valid network port (1-65535)."
            )


# ---------------------------------------------------------------------------
# Default Global Config Singleton Export
# ---------------------------------------------------------------------------

# Global instance for easy importing across the buywise_ai repository
try:
    current_config: AppConfig = ConfigLoader.load_config()
except ConfigurationError as err:
    logger.critical(f"Failed to load application configuration: {err}")
    raise SystemExit(1)


# Explicit module export definitions
__all__ = [
    "EnvironmentOption",
    "LogLevelOption",
    "DatabaseConfig",
    "ModelConfig",
    "AppConfig",
    "ConfigurationError",
    "ConfigLoader",
    "current_config"
]
