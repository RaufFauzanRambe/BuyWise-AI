"""
BuyWise-AI Ingestion Request Parser Module
=========================================

This module provides data extraction, parsing, and payload sanitization utilities
for incoming e-commerce requests within the BuyWise-AI ingestion layer.

Key Components:
---------------
- RequestFormat (Enum)         : Supported payload content types (JSON, CSV, Form Data, Query Params).
- ParsedPayload (Data Class)   : Standardized container holding normalized request data.
- RequestParser (Core Engine)  : Robust engine capable of extracting structured dictionary payloads 
                                 from raw HTTP requests, byte streams, and URL queries.

Usage Example:
--------------
>>> from buywise_ai.ingestion.request_parser import RequestParser, RequestFormat
>>> raw_json = '{"product_id": "P-101", "price": "29.99", "tags": "tech, gadget"}'
>>> parsed_data = RequestParser.parse_payload(raw_json, content_type=RequestFormat.JSON)
>>> print(parsed_data.cleaned_data)
{'product_id': 'P-101', 'price': 29.99, 'tags': ['tech', 'gadget']}
"""

import json
import csv
import io
import logging
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse

# Configure logger for request parsing operations
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Enumerations and Data Models
# ---------------------------------------------------------------------------

class RequestFormat(Enum):
    """Enumeration of supported payload content formats."""
    JSON = auto()
    CSV = auto()
    FORM_URLENCODED = auto()
    QUERY_PARAMS = auto()
    UNKNOWN = auto()


class RequestParserError(Exception):
    """Base exception class for errors encountered during request parsing."""
    pass


class PayloadParsingError(RequestParserError):
    """Raised when raw request payload fails format decoding or parsing."""
    def __init__(self, message: str, raw_payload: Optional[Any] = None):
        super().__init__(message)
        self.raw_payload = raw_payload


class UnsupportedFormatError(RequestParserError):
    """Raised when an unrecognized or unsupported Content-Type is provided."""
    pass


class ParsedPayload:
    """Standardized output structure holding extracted and cleaned payload data.
    
    Attributes:
        raw_content (Any): The original unparsed input content.
        cleaned_data (Dict[str, Any]): Dictionary containing normalized keys and typed values.
        format_type (RequestFormat): Recognized payload format type.
        metadata (Dict[str, Any]): Parsing diagnostic metadata (e.g., key count, encoding).
    """

    def __init__(
        self,
        raw_content: Any,
        cleaned_data: Dict[str, Any],
        format_type: RequestFormat,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        self.raw_content = raw_content
        self.cleaned_data = cleaned_data
        self.format_type = format_type
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return (
            f"<ParsedPayload format={self.format_type.name} "
            f"keys_count={len(self.cleaned_data)}>"
        )


# ---------------------------------------------------------------------------
# Core Parser Engine Implementation
# ---------------------------------------------------------------------------

class RequestParser:
    """Utility engine for parsing, extracting, and sanitizing raw request payloads."""

    @staticmethod
    def detect_format(content_type_header: str) -> RequestFormat:
        """Determines the RequestFormat based on an incoming HTTP Content-Type header.
        
        Args:
            content_type_header (str): Raw Content-Type string (e.g., 'application/json').
            
        Returns:
            RequestFormat: Matched payload format enumeration.
        """
        if not content_type_header:
            return RequestFormat.UNKNOWN

        header = content_type_header.lower().strip()
        if "application/json" in header:
            return RequestFormat.JSON
        elif "text/csv" in header or "application/csv" in header:
            return RequestFormat.CSV
        elif "application/x-www-form-urlencoded" in header:
            return RequestFormat.FORM_URLENCODED
        else:
            return RequestFormat.UNKNOWN

    @classmethod
    def parse_json(cls, payload: Union[str, bytes]) -> Dict[str, Any]:
        """Parses raw JSON string or byte payloads into structured Python dictionaries.
        
        Args:
            payload (Union[str, bytes]): Raw JSON data string or bytes.
            
        Returns:
            Dict[str, Any]: Parsed key-value dictionary.
            
        Raises:
            PayloadParsingError: If input fails JSON parsing rules.
        """
        try:
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            data = json.loads(payload)
            if not isinstance(data, dict):
                raise PayloadParsingError("JSON root element must be an object/dictionary.", raw_payload=payload)
            return data
        except (json.JSONDecodeError, UnicodeDecodeError) as err:
            logger.error(f"JSON parsing failed: {str(err)}")
            raise PayloadParsingError(f"Failed to parse JSON payload: {str(err)}", raw_payload=payload) from err

    @classmethod
    def parse_form_urlencoded(cls, payload: str) -> Dict[str, Any]:
        """Parses x-www-form-urlencoded request strings into unified dictionary maps.
        
        Args:
            payload (str): Form-encoded payload string.
            
        Returns:
            Dict[str, Any]: Extracted dictionary representation.
        """
        try:
            parsed = parse_qs(payload, keep_blank_values=True)
            # Flatten single item lists from parse_qs
            flattened: Dict[str, Any] = {}
            for key, val in parsed.items():
                flattened[key] = val[0] if len(val) == 1 else val
            return flattened
        except Exception as err:
            logger.error(f"Form-urlencoded parsing failed: {str(err)}")
            raise PayloadParsingError(f"Failed to parse form payload: {str(err)}", raw_payload=payload) from err

    @classmethod
    def parse_csv_row(cls, payload: str) -> Dict[str, Any]:
        """Parses single-row or multi-record CSV strings into dictionary payloads.
        
        Args:
            payload (str): CSV formatted string containing header and records.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the first CSV record.
        """
        try:
            f = io.StringIO(payload.strip())
            reader = csv.DictReader(f)
            records = list(reader)
            if not records:
                return {}
            return dict(records[0])
        except Exception as err:
            logger.error(f"CSV payload parsing failed: {str(err)}")
            raise PayloadParsingError(f"Failed to parse CSV payload: {str(err)}", raw_payload=payload) from err

    @classmethod
    def parse_url_query_params(cls, url_or_query: str) -> Dict[str, Any]:
        """Extracts and parses URL query string parameters into a dictionary.
        
        Args:
            url_or_query (str): Full URL string or raw query string.
            
        Returns:
            Dict[str, Any]: Extracted URL query parameters.
        """
        query_string = url_or_query
        if "://" in url_or_query or "?" in url_or_query:
            query_string = urlparse(url_or_query).query

        return cls.parse_form_urlencoded(query_string)

    @classmethod
    def sanitize_and_type_cast(cls, raw_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes keys, strips string values, and performs automatic standard type casting.
        
        Converts string representations of integers, floats, booleans, and comma-separated 
        lists into native Python types.
        
        Args:
            raw_dict (Dict[str, Any]): Unsanitized input dictionary.
            
        Returns:
            Dict[str, Any]: Cleaned and casted output dictionary.
        """
        cleaned: Dict[str, Any] = {}
        for key, value in raw_dict.items():
            # Standardize dictionary keys: trim whitespace and convert to lowercase
            clean_key = str(key).strip().lower()

            if isinstance(value, str):
                val_str = value.strip()
                
                # Numeric int casting
                if val_str.isdigit():
                    cleaned[clean_key] = int(val_str)
                # Numeric float casting
                elif cls._is_float(val_str):
                    cleaned[clean_key] = float(val_str)
                # Boolean casting
                elif val_str.lower() in ("true", "false"):
                    cleaned[clean_key] = val_str.lower() == "true"
                # Comma-separated tag list parsing
                elif "," in val_str:
                    cleaned[clean_key] = [item.strip() for item in val_str.split(",") if item.strip()]
                else:
                    cleaned[clean_key] = val_str
            else:
                cleaned[clean_key] = value

        return cleaned

    @staticmethod
    def _is_float(value: str) -> bool:
        """Helper method to check if a string represents a valid floating point number."""
        try:
            float(value)
            return "." in value
        except ValueError:
            return False

    @classmethod
    def parse_payload(
        cls,
        payload: Union[str, bytes],
        content_type: RequestFormat = RequestFormat.JSON,
        sanitize: bool = True
    ) -> ParsedPayload:
        """Master orchestrator method for extracting and parsing raw request data.
        
        Args:
            payload (Union[str, bytes]): Raw input payload content.
            content_type (RequestFormat): Specified format category of incoming payload.
            sanitize (bool): Enables automatic type casting and key normalization.
            
        Returns:
            ParsedPayload: Fully structured and normalized payload container object.
            
        Raises:
            UnsupportedFormatError: If an unknown or unhandled format type is requested.
            PayloadParsingError: If parsing execution fails.
        """
        logger.debug(f"Parsing incoming payload with format: {content_type.name}")

        if content_type == RequestFormat.JSON:
            raw_data = cls.parse_json(payload)
        elif content_type == RequestFormat.FORM_URLENCODED:
            raw_str = payload.decode("utf-8") if isinstance(payload, bytes) else payload
            raw_data = cls.parse_form_urlencoded(raw_str)
        elif content_type == RequestFormat.CSV:
            raw_str = payload.decode("utf-8") if isinstance(payload, bytes) else payload
            raw_data = cls.parse_csv_row(raw_str)
        elif content_type == RequestFormat.QUERY_PARAMS:
            raw_str = payload.decode("utf-8") if isinstance(payload, bytes) else payload
            raw_data = cls.parse_url_query_params(raw_str)
        else:
            raise UnsupportedFormatError(f"Unsupported payload format provided: {content_type}")

        final_data = cls.sanitize_and_type_cast(raw_data) if sanitize else raw_data

        return ParsedPayload(
            raw_content=payload,
            cleaned_data=final_data,
            format_type=content_type,
            metadata={
                "extracted_keys": list(final_data.keys()),
                "is_sanitized": sanitize
            }
        )


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    "RequestFormat",
    "ParsedPayload",
    "RequestParser",
    "RequestParserError",
    "PayloadParsingError",
    "UnsupportedFormatError",
]
