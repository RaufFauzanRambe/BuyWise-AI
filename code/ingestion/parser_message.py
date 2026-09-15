"""
Message Parser Module for BuyWise-AI Ingestion System.

This module processes incoming raw messages (e.g., from user interactions,
chatbots, or external integrations) and standardizes them into a structured format
for downstream BuyWise-AI processing pipelines.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Configure module logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class MessageParsingError(Exception):
    """Custom exception raised when message parsing fails."""
    pass


class MessageParser:
    """Parses and validates raw incoming payload messages into a structured schema."""

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the MessageParser.

        :param strict_mode: If True, raises exceptions on missing non-essential fields.
        """
        self.strict_mode = strict_mode

    def parse_raw_message(self, raw_data: Any) -> Dict[str, Any]:
        """
        Parses raw data (string or dict) into a unified message dictionary.

        :param raw_data: Raw payload in JSON string or dict format.
        :return: Standardized message dictionary.
        :raises MessageParsingError: If data cannot be parsed or lacks critical fields.
        """
        payload = self._load_json_if_needed(raw_data)
        
        # Validate critical fields
        user_id = payload.get("user_id") or payload.get("sender_id")
        content = payload.get("content") or payload.get("message")

        if not user_id or content is None:
            raise MessageParsingError("Missing required fields: 'user_id' or 'content'.")

        cleaned_text = self._sanitize_text(str(content))
        timestamp = self._parse_timestamp(payload.get("timestamp"))

        parsed_message = {
            "message_id": payload.get("message_id", self._generate_fallback_id(user_id)),
            "user_id": str(user_id),
            "text": cleaned_text,
            "channel": payload.get("channel", "unknown"),
            "timestamp": timestamp,
            "metadata": payload.get("metadata", {}),
            "extracted_entities": self._extract_basic_entities(cleaned_text),
        }

        logger.debug(f"Successfully parsed message for user: {user_id}")
        return parsed_message

    def _load_json_if_needed(self, raw_data: Any) -> Dict[str, Any]:
        """Converts raw JSON string input into a Python dictionary."""
        if isinstance(raw_data, str):
            try:
                return json.loads(raw_data)
            except json.JSONDecodeError as err:
                raise MessageParsingError(f"Invalid JSON string format: {err}")
        elif isinstance(raw_data, dict):
            return raw_data
        else:
            raise MessageParsingError(f"Unsupported payload type: {type(raw_data).__name__}")

    def _sanitize_text(self, text: str) -> str:
        """Cleans and standardizes input text string."""
        if not text:
            return ""
        # Remove excess whitespace and normalize spaces
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _parse_timestamp(self, ts_input: Optional[Any]) -> str:
        """Standardizes timestamp strings into ISO 8601 format in UTC."""
        if not ts_input:
            return datetime.now(timezone.utc).isoformat()

        if isinstance(ts_input, (int, float)):
            return datetime.fromtimestamp(ts_input, tz=timezone.utc).isoformat()

        if isinstance(ts_input, str):
            try:
                dt = datetime.fromisoformat(ts_input.replace("Z", "+00:00"))
                return dt.isoformat()
            except ValueError:
                logger.warning(f"Failed to parse timestamp string '{ts_input}'. Using current UTC time.")

        return datetime.now(timezone.utc).isoformat()

    def _extract_basic_entities(self, text: str) -> Dict[str, Any]:
        """Extracts basic purchasing intent keywords or references (e.g., price tags)."""
        prices = re.findall(r"\$\d+(?:\.\d{2})?", text)
        urls = re.findall(r"https?://\S+", text)

        return {
            "contains_price": len(prices) > 0,
            "found_prices": prices,
            "contains_url": len(urls) > 0,
            "urls": urls,
        }

    @staticmethod
    def _generate_fallback_id(user_id: Any) -> str:
        """Generates a fallback message ID if not provided."""
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"msg_{user_id}_{now_str}"


# Example usage
if __name__ == "__main__":
    parser = MessageParser()

    sample_raw_json = json.dumps({
        "sender_id": "usr_9876",
        "message": "Hey! Check out this laptop for $899.99 at https://example.com/item",
        "channel": "web_chat",
        "timestamp": "2026-09-15T10:00:00Z"
    })

    try:
        parsed_result = parser.parse_raw_message(sample_raw_json)
        print("Parsed Message Result:\n", json.dumps(parsed_result, indent=2))
    except MessageParsingError as error:
        print(f"Failed to parse message: {error}")
