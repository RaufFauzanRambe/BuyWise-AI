"""
BuyWise-AI Data Schemas and Validation Layer
============================================

This module defines Pydantic schemas, data transfer objects (DTOs), and validation
contracts across the BuyWise-AI platform. It ensures strict type safety, data integrity,
and structural verification for incoming API requests, ingestion payloads, and outgoing
recommendation model predictions.

Key Schema Categories:
----------------------
- User & Context Schemas       : Authentication and user preference contracts.
- Product Catalog Schemas     : Product details, pricing, and inventory payloads.
- Ingestion & Event Schemas    : Ingested review events and batch catalog streams.
- Model Inference Schemas      : Request and response interfaces for AI agents/models.
- Generic Response Wrappers   : Standardized API response containers.

Usage Example:
--------------
>>> from buywise_ai.schemas import ProductCreateSchema, RecommendationRequestSchema
>>> product = ProductCreateSchema(
...     sku="PROD-98765",
...     name="Wireless Noise-Canceling Headphones",
...     category="Electronics",
...     price=199.99,
...     stock_quantity=50
... )
>>> request = RecommendationRequestSchema(
...     user_id="USR-1002",
...     top_k=5,
...     category_preference=["Electronics", "Accessories"]
... )
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated


# ---------------------------------------------------------------------------
# Core Enumerations
# ---------------------------------------------------------------------------

class CurrencyCode(str, Enum):
    """Supported ISO 4217 currency codes across the platform."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    IDR = "IDR"
    JPY = "JPY"


class ReviewSentiment(str, Enum):
    """Sentiment classification tags for customer product reviews."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class OrderStatus(str, Enum):
    """Lifecycle status for user order queries."""
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Generic API Response Wrappers
# ---------------------------------------------------------------------------

T = TypeVar("T")


class APIResponseWrapper(BaseModel, Generic[T]):
    """Standardized API response structure wrapping payload outputs.
    
    Attributes:
        success (bool): Operational status of the request execution.
        message (str): Human-readable status or summary message.
        data (Optional[T]): Type-generic payload containing returned data structures.
        errors (Optional[List[str]]): List of execution error descriptions if failed.
        timestamp (datetime): UTC timestamp when the response was generated.
    """
    success: bool = True
    message: str = "Operation executed successfully."
    data: Optional[T] = None
    errors: Optional[List[str]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        arbitrary_types_allowed=True
    )


class PaginationMeta(BaseModel):
    """Metadata container for paginated list endpoints."""
    page: int = Field(ge=1, default=1, description="Current page number (1-indexed).")
    page_size: int = Field(ge=1, le=500, default=50, description="Items per page.")
    total_records: int = Field(ge=0, description="Total count of matching records.")
    total_pages: int = Field(ge=0, description="Total pages available.")


class PaginatedResponseWrapper(APIResponseWrapper[List[T]], Generic[T]):
    """Generic response wrapper specifically formatted for paginated queries."""
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# User & Preference Schemas
# ---------------------------------------------------------------------------

class UserProfileBase(BaseModel):
    """Base payload defining common user profile attributes."""
    username: Annotated[str, StringConstraints(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")]
    email: EmailStr
    full_name: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = True


class UserProfileCreate(UserProfileBase):
    """Payload requirement for creating a new user entity."""
    password_hash: str = Field(min_length=8, description="Hashed authentication credential string.")


class UserProfileResponse(UserProfileBase):
    """Data object returned upon retrieving user details."""
    user_id: str = Field(default_factory=lambda: f"USR-{uuid4().hex[:8].upper()}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


class UserPreferencesSchema(BaseModel):
    """Structured preferences used to personalize AI product recommendations."""
    preferred_categories: List[str] = Field(default_factory=list, description="Target item categories.")
    price_min: Optional[float] = Field(default=0.0, ge=0.0)
    price_max: Optional[float] = Field(default=None, ge=0.0)
    favorite_brands: List[str] = Field(default_factory=list)
    exclude_out_of_stock: bool = True

    @model_validator(mode="after")
    def validate_price_bounds(self) -> "UserPreferencesSchema":
        """Ensures that price_max is strictly greater than price_min when provided."""
        if self.price_max is not None and self.price_min is not None:
            if self.price_max < self.price_min:
                raise ValueError("price_max must be greater than or equal to price_min.")
        return self


# ---------------------------------------------------------------------------
# Product Catalog Schemas
# ---------------------------------------------------------------------------

class ProductBaseSchema(BaseModel):
    """Base structural model representing an e-commerce catalog product."""
    sku: Annotated[str, StringConstraints(min_length=3, max_length=30, pattern=r"^[A-Z0-9_-]+$")]
    name: str = Field(min_length=1, max_length=150, description="Commercial name of the product.")
    description: Optional[str] = Field(default=None, max_length=2000)
    category: str = Field(min_length=1, max_length=80)
    brand: str = Field(min_length=1, max_length=80)
    price: float = Field(gt=0.0, description="Retail unit price.")
    currency: CurrencyCode = CurrencyCode.USD
    stock_quantity: int = Field(ge=0, description="Available inventory count.")
    image_urls: List[HttpUrl] = Field(default_factory=list)


class ProductCreateSchema(ProductBaseSchema):
    """Request DTO used to ingest or register new products into the catalog."""
    tags: List[str] = Field(default_factory=list, description="Search and filtering keywords.")


class ProductUpdateSchema(BaseModel):
    """Patch update DTO allowing partial fields modification for products."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    price: Optional[float] = Field(default=None, gt=0.0)
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    is_available: Optional[bool] = None


class ProductResponseSchema(ProductBaseSchema):
    """Complete product payload returned by API lookup endpoints."""
    product_id: str = Field(default_factory=lambda: f"PROD-{uuid4().hex[:8].upper()}")
    rating_average: float = Field(ge=0.0, le=5.0, default=0.0, description="Calculated average rating score.")
    review_count: int = Field(ge=0, default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Ingestion & Review Event Schemas
# ---------------------------------------------------------------------------

class ReviewIngestionSchema(BaseModel):
    """Payload contract for customer reviews ingested from source systems."""
    review_id: str = Field(default_factory=lambda: f"REV-{uuid4().hex[:8].upper()}")
    product_id: str = Field(min_length=1, description="Target product SKU or ID.")
    user_id: str = Field(min_length=1, description="Reviewer account identifier.")
    rating: int = Field(ge=1, le=5, description="Integral star rating score from 1 to 5.")
    comment: str = Field(min_length=1, max_length=5000, description="User submitted text feedback.")
    verified_purchase: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("comment")
    @classmethod
    def sanitize_comment_text(cls, v: str) -> str:
        """Strips surrounding whitespace from incoming review comments."""
        return v.strip()


class BatchIngestionRequest(BaseModel):
    """Wrapper schema for streaming batch ingestion endpoints."""
    batch_id: UUID = Field(default_factory=uuid4)
    source_name: str = Field(min_length=1, description="Origin identifier of the data pipeline.")
    records: List[Dict[str, Any]] = Field(min_items=1, description="Raw dictionary record payloads.")


# ---------------------------------------------------------------------------
# AI Model Inference & Agent Schemas
# ---------------------------------------------------------------------------

class RecommendationRequestSchema(BaseModel):
    """Input payload passed into AI model inference pipelines."""
    user_id: str = Field(min_length=1, description="Target customer identifier.")
    top_k: int = Field(ge=1, le=100, default=10, description="Number of recommendations requested.")
    category_preference: Optional[List[str]] = Field(default=None)
    min_rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    context_session_id: Optional[str] = Field(default=None, description="Active session ID for contextual agents.")


class ScoredProductRecommendation(BaseModel):
    """Individual item score generated by candidate selection models."""
    product: ProductResponseSchema
    relevance_score: float = Field(ge=0.0, le=1.0, description="Normalized model prediction confidence.")
    explanation: Optional[str] = Field(default=None, description="Reasoning text generated for user transparency.")


class RecommendationResponseSchema(BaseModel):
    """Output payload generated by BuyWise-AI recommendation engines."""
    request_id: UUID = Field(default_factory=uuid4)
    user_id: str
    recommendations: List[ScoredProductRecommendation]
    model_version: str = Field(default="v1.0.0", description="Trained checkpoint or pipeline release version.")
    latency_ms: float = Field(ge=0.0, description="Processing duration in milliseconds.")


class AgentQuerySchema(BaseModel):
    """Request payload for multi-turn autonomous agent interactions."""
    session_id: str = Field(default_factory=lambda: f"SESS-{uuid4().hex[:6].upper()}")
    user_id: str
    prompt: str = Field(min_length=1, max_length=1000, description="User input phrase or request.")
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Explicit Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "CurrencyCode",
    "ReviewSentiment",
    "OrderStatus",
    # Generic Wrappers
    "APIResponseWrapper",
    "PaginationMeta",
    "PaginatedResponseWrapper",
    # User Schemas
    "UserProfileBase",
    "UserProfileCreate",
    "UserProfileResponse",
    "UserPreferencesSchema",
    # Product Schemas
    "ProductBaseSchema",
    "ProductCreateSchema",
    "ProductUpdateSchema",
    "ProductResponseSchema",
    # Ingestion Schemas
    "ReviewIngestionSchema",
    "BatchIngestionRequest",
    # AI/Agent Schemas
    "RecommendationRequestSchema",
    "ScoredProductRecommendation",
    "RecommendationResponseSchema",
    "AgentQuerySchema",
]
