"""
BuyWise-AI Data Ingestion Subpackage
===================================

This module serves as the primary entry point for the BuyWise-AI data ingestion layer.
It centralizes data fetching, ingestion pipelines, schema validation, and custom exception handling.

Key Features:
-------------
- Unified interface for ingesting e-commerce catalog data, customer reviews, and streaming events.
- Strict schema enforcement via validation utilities.
- Standardized logging and exception mechanisms tailored for data pipeline stability.

Usage Example:
--------------
>>> from buywise_ai.ingestion import (
...     ProductCatalogIngestor,
...     ReviewDataIngestor,
...     IngestionConfig,
...     IngestionStatus
... )
>>> config = IngestionConfig(source_url="https://api.buywise.ai/v1/products", batch_size=500)
>>> ingestor = ProductCatalogIngestor(config=config)
>>> result = ingestor.run()
>>> print(result.status)
IngestionStatus.SUCCESS
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum, auto

# Configure subpackage logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Core Constants and Configuration Classes
# ---------------------------------------------------------------------------

class IngestionStatus(Enum):
    """Enumeration representing the operational status of an ingestion job."""
    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    PARTIAL_SUCCESS = auto()
    FAILED = auto()


@dataclass(frozen=True)
class IngestionConfig:
    """Configuration data structure for controlling ingestion behavior.
    
    Attributes:
        source_url (str): Target API endpoint or storage path.
        batch_size (int): Number of items to process per chunk (default: 100).
        max_retries (int): Maximum retry attempts upon failure (default: 3).
        timeout (int): Request timeout in seconds (default: 30).
    """
    source_url: str
    batch_size: int = 100
    max_retries: int = 3
    timeout: int = 30


@dataclass
class IngestionSummary:
    """Summary of the execution details of an ingestion run.
    
    Attributes:
        status (IngestionStatus): Final execution state.
        records_processed (int): Count of successfully ingested records.
        failed_records (int): Count of records that failed processing.
        errors (List[str]): List of error messages captured during execution.
    """
    status: IngestionStatus
    records_processed: int = 0
    failed_records: int = 0
    errors: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class IngestionError(Exception):
    """Base exception class for all errors originating from the ingestion layer."""
    pass


class ValidationError(IngestionError):
    """Raised when incoming data fails schema or contract validation."""
    def __init__(self, message: str, invalid_records: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.invalid_records = invalid_records or []


class ConnectionError(IngestionError):
    """Raised when data source endpoints are unreachable or time out."""
    pass


# ---------------------------------------------------------------------------
# Base & Concrete Ingestor Interfaces
# ---------------------------------------------------------------------------

class BaseIngestor:
    """Abstract Base Class (ABC) for all BuyWise-AI data ingestors."""
    
    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Ensures input configuration contains valid parameters."""
        if not self.config.source_url:
            raise ValueError("The 'source_url' must not be empty.")
        if self.config.batch_size <= 0:
            raise ValueError("'batch_size' must be a positive integer.")

    def fetch_raw_data(self) -> List[Dict[str, Any]]:
        """Retrieves raw data payload from the source. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement fetch_raw_data()")

    def validate_schema(self, data: List[Dict[str, Any]]) -> bool:
        """Validates raw data payload against the expected data schema."""
        raise NotImplementedError("Subclasses must implement validate_schema()")

    def run(self) -> IngestionSummary:
        """Executes the full ingestion workflow: Fetch -> Validate -> Load."""
        logger.info(f"Starting ingestion process for source: {self.config.source_url}")
        try:
            raw_data = self.fetch_raw_data()
            if self.validate_schema(raw_data):
                # Placeholder for loading/saving data to internal storage
                return IngestionSummary(
                    status=IngestionStatus.SUCCESS,
                    records_processed=len(raw_data)
                )
            else:
                raise ValidationError("Raw payload failed schema validation.")
        except Exception as err:
            logger.error(f"Ingestion failed: {str(err)}")
            return IngestionSummary(
                status=IngestionStatus.FAILED,
                errors=[str(err)]
            )


class ProductCatalogIngestor(BaseIngestor):
    """Ingestor dedicated to retrieving product catalog datasets."""

    def fetch_raw_data(self) -> List[Dict[str, Any]]:
        # Mock fetch implementation for pipeline tests
        logger.debug(f"Fetching product data in batches of {self.config.batch_size}...")
        return [{"product_id": "P1001", "name": "Smart Watch", "price": 199.99}]

    def validate_schema(self, data: List[Dict[str, Any]]) -> bool:
        required_keys = {"product_id", "name", "price"}
        return all(required_keys.issubset(item.keys()) for item in data)


class ReviewDataIngestor(BaseIngestor):
    """Ingestor dedicated to capturing and streaming customer reviews."""

    def fetch_raw_data(self) -> List[Dict[str, Any]]:
        # Mock fetch implementation for pipeline tests
        logger.debug(f"Fetching review payload from {self.config.source_url}...")
        return [{"review_id": "R501", "product_id": "P1001", "rating": 5, "comment": "Great product!"}]

    def validate_schema(self, data: List[Dict[str, Any]]) -> bool:
        required_keys = {"review_id", "product_id", "rating"}
        return all(required_keys.issubset(item.keys()) for item in data)


# ---------------------------------------------------------------------------
# Explicit Module Exports (__all__)
# ---------------------------------------------------------------------------

__all__: List[str] = [
    # Data Models & Configs
    "IngestionConfig",
    "IngestionSummary",
    "IngestionStatus",
    
    # Ingestor Engine Classes
    "BaseIngestor",
    "ProductCatalogIngestor",
    "ReviewDataIngestor",
    
    # Exceptions
    "IngestionError",
    "ValidationError",
    "ConnectionError",
]

__version__ = "1.0.0"
__author__ = "BuyWise-AI Engineering Team"
