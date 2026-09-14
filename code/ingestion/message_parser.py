"""
BuyWise-AI Ingestion Message Parser Module
=========================================

This module provides parsing, deserialization, and message extraction capabilities
for event-driven data streaming architectures (e.g., Apache Kafka, RabbitMQ, Amazon SQS)
within the BuyWise-AI data ingestion pipeline.

Key Features:
-------------
- **Format Agnostic Parsing**: Supports JSON, Avro-like dictionaries, and string-encoded messages.
- **Message Normalization**: Standardizes raw streaming payloads into a unified `IngestionMessage` dataclass.
- **Header & Metadata Extraction**: Preserves message headers, timestamps, and origin routing details.
- **Validation & Dead-Letter Queue (DLQ) Prep**: Identifies corrupt or malformed messages for error routing.

Usage Example:
--------------
>>> from buywise_ai.ingestion.message_parser import MessageParser, MessageFormat
>>> raw_kafka_payload = b'{"event_id": "EVT-1001", "event_type": "USER_CLICK", "payload": {"item_id": "P-90"}}'
>>> parsed_msg = MessageParser.parse(raw_kafka_payload, format_type=MessageFormat.JSON)
>>> print(parsed_msg.event_id)
'EVT-1001'
>>> print(parsed_msg.payload['item_id'])
'P-90'
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

# Configure subpackage logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Enumerations and Data Structures
# ---------------------------------------------------------------------------

class MessageFormat(Enum):
    """Supported streaming message encoding formats."""
    JSON = auto()
    STRING = auto()
    DICTIONARY = auto()
    UNKNOWN = auto()


class MessageParsingStatus(Enum):
    """Processing state classifications for incoming streaming messages."""
    SUCCESS = auto()
    MALFORMED = auto()
    CORRUPTED = auto()
    MISSING_REQUIRED_FIELDS = auto()


@dataclass
class IngestionMessage:
    """Standardized representation of a parsed event streaming message.
    
    Attributes:
        event_id (str): Unique identifier for the streaming event.
        event_type (str): Classification tag of the message event (e.g., 'PURCHASE', 'VIEW').
        payload (Dict[str, Any]): Main data payload carried by the message.
        headers (Dict[str, str]): Key-value metadata headers from the streaming broker.
        timestamp (datetime): UTC timestamp when the message was generated or ingested.
        status (MessageParsingStatus): Parsing outcome status.
        errors (List[str]): List of parsing or validation error traces if status is not SUCCESS.
    """
    event_id: str
    event_type: str
    payload: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: MessageParsingStatus = MessageParsingStatus.SUCCESS
    errors: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exception Classes
# ---------------------------------------------------------------------------

class MessageParserError(Exception):
    """Base exception class for streaming message parser failures."""
    pass


class InvalidMessagePayloadError(MessageParserError):
    """Raised when message content cannot be decoded or deserialized."""
    def __init__(self, message: str, raw_payload: Any):
        super().__init__(message)
        self.raw_payload = raw_payload


class MissingMessageFieldError(MessageParserError):
    """Raised when a required structural field is missing from the message."""
    def __init__(self, message: str, missing_field: str):
        super().__init__(message)
        self.missing_field = missing_field


# ---------------------------------------------------------------------------
# Core Message Parser Implementation
# ---------------------------------------------------------------------------

class MessageParser:
    """Parser engine for extracting and standardizing event streaming messages."""

    REQUIRED_FIELDS: List[str] = ["event_id", "payload"]

    @classmethod
    def detect_format(cls, raw_data: Any) -> MessageFormat:
        """Detects the underlying format of an unparsed message payload.
        
        Args:
            raw_data (Any): Raw byte, string, or dictionary input payload.
            
        Returns:
            MessageFormat: Corresponding format enum value.
        """
        if isinstance(raw_data, dict):
            return MessageFormat.DICTIONARY
        if isinstance(raw_data, (bytes, str)):
            try:
                decoded = raw_data.decode("utf-8") if isinstance(raw_data, bytes) else raw_data
                decoded_trimmed = decoded.strip()
                if decoded_trimmed.startswith("{") and decoded_trimmed.endswith("}"):
                    return MessageFormat.JSON
                return MessageFormat.STRING
            except Exception:
                return MessageFormat.UNKNOWN
        return MessageFormat.UNKNOWN

    @classmethod
    def parse_json_bytes(cls, raw_bytes: bytes) -> Dict[str, Any]:
        """Deserializes JSON-encoded byte streams into Python dictionaries.
        
        Args:
            raw_bytes (bytes): UTF-8 encoded JSON bytes.
            
        Returns:
            Dict[str, Any]: Deserialized dictionary payload.
            
        Raises:
            InvalidMessagePayloadError: If decoding or JSON parsing fails.
        """
        try:
            decoded_str = raw_bytes.decode("utf-8")
            data = json.loads(decoded_str)
            if not isinstance(data, dict):
                raise InvalidMessagePayloadError("JSON payload root must be a key-value object.", raw_payload=raw_bytes)
            return data
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            logger.error(f"Failed to decode byte stream: {str(err)}")
            raise InvalidMessagePayloadError(f"Corrupted byte stream: {str(err)}", raw_payload=raw_bytes) from err

    @classmethod
    def parse_string_payload(cls, raw_str: str) -> Dict[str, Any]:
        """Parses plain string payloads into structured event dictionaries.
        
        Args:
            raw_str (str): Raw message string.
            
        Returns:
            Dict[str, Any]: Constructed dictionary.
        """
        try:
            return json.loads(raw_str)
        except json.JSONDecodeError:
            # Fallback wrapper for plain text non-JSON strings
            return {
                "event_id": f"GEN-{uuid4().hex[:8].upper()}",
                "event_type": "UNSTRUCTURED_TEXT",
                "payload": {"text_content": raw_str.strip()}
            }

    @classmethod
    def validate_message_structure(cls, data: Dict[str, Any]) -> List[str]:
        """Validates that mandatory fields are present in the parsed dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary to validate.
            
        Returns:
            List[str]: List of missing required field names, if any.
        """
        missing: List[str] = []
        for field_name in cls.REQUIRED_FIELDS:
            if field_name not in data or data[field_name] is None:
                missing.append(field_name)
        return missing

    @classmethod
    def parse(
        cls,
        raw_message: Union[bytes, str, Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None,
        format_type: Optional[MessageFormat] = None
    ) -> IngestionMessage:
        """Master method for parsing streaming messages into unified IngestionMessage objects.
        
        Args:
            raw_message (Union[bytes, str, Dict[str, Any]]): Incoming event message content.
            headers (Optional[Dict[str, str]]): Broker headers (e.g., Kafka headers).
            format_type (Optional[MessageFormat]): Explicit format override, if known.
            
        Returns:
            IngestionMessage: Normalized message object containing payload and diagnostic details.
        """
        headers = headers or {}
        detected_format = format_type or cls.detect_format(raw_message)

        try:
            if detected_format == MessageFormat.DICTIONARY and isinstance(raw_message, dict):
                data_dict = raw_message
            elif detected_format == MessageFormat.JSON and isinstance(raw_message, bytes):
                data_dict = cls.parse_json_bytes(raw_message)
            elif isinstance(raw_message, str):
                data_dict = cls.parse_string_payload(raw_message)
            else:
                raise InvalidMessagePayloadError(
                    f"Unsupported or unparseable format type: {detected_format.name}",
                    raw_payload=raw_message
                )

            # Check structure constraints
            missing_fields = cls.validate_message_structure(data_dict)
            if missing_fields:
                logger.warning(f"Message missing mandatory fields: {missing_fields}")
                return IngestionMessage(
                    event_id=data_dict.get("event_id", f"ERR-{uuid4().hex[:8].upper()}"),
                    event_type=data_dict.get("event_type", "UNKNOWN"),
                    payload=data_dict.get("payload", data_dict),
                    headers=headers,
                    status=MessageParsingStatus.MISSING_REQUIRED_FIELDS,
                    errors=[f"Missing required fields: {', '.join(missing_fields)}"]
                )

            # Construct clean message payload
            event_id = str(data_dict["event_id"])
            event_type = str(data_dict.get("event_type", "GENERIC_EVENT"))
            payload_content = data_dict["payload"] if isinstance(data_dict["payload"], dict) else {"data": data_dict["payload"]}

            return IngestionMessage(
                event_id=event_id,
                event_type=event_type,
                payload=payload_content,
                headers=headers,
                status=MessageParsingStatus.SUCCESS
            )

        except InvalidMessagePayloadError as err:
            logger.error(f"Message parsing error: {str(err)}")
            return IngestionMessage(
                event_id=f"FAIL-{uuid4().hex[:8].upper()}",
                event_type="CORRUPTED_PAYLOAD",
                payload={},
                headers=headers,
                status=MessageParsingStatus.CORRUPTED,
                errors=[str(err)]
            )
        except Exception as err:
            logger.critical(f"Unhandled exception during message parsing: {str(err)}")
            return IngestionMessage(
                event_id=f"CRIT-{uuid4().hex[:8].upper()}",
                event_type="FATAL_PARSER_ERROR",
                payload={},
                headers=headers,
                status=MessageParsingStatus.MALFORMED,
                errors=[f"Unhandled exception: {str(err)}"]
            )


# ---------------------------------------------------------------------------
# Explicit Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Data Models & Configs
    "MessageFormat",
    "MessageParsingStatus",
    "IngestionMessage",
    
    # Core Parser Class
    "MessageParser",
    
    # Exception Types
    "MessageParserError",
    "InvalidMessagePayloadError",
    "MissingMessageFieldError",
]
