"""
BuyWise-AI Autonomous Agent Framework
=====================================

This module provides the core AI agent architecture for the BuyWise-AI platform.
It defines agent abstractions, memory management, tool execution pipelines, and
conversational recommendation logic.

Key Classes:
------------
- AgentRole         : Enum defining operational modes (RECOMMENDER, ANALYST, ASSISTANT).
- AgentMemory       : In-memory store for maintaining context and conversation history.
- BaseAgent         : Abstract Base Class establishing the contract for all BuyWise-AI agents.
- ECommerceAgent    : Concrete implementation specializing in product recommendation and user intents.

Usage Example:
--------------
>>> from buywise_ai.agent import ECommerceAgent, AgentRole, AgentConfig
>>> config = AgentConfig(role=AgentRole.RECOMMENDER, model_name="gpt-4o-mini")
>>> agent = ECommerceAgent(config=config)
>>> response = agent.process_query(
...     user_id="USR_1002",
...     user_input="Looking for waterproof smartwatches under $200"
... )
>>> print(response.content)
"""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Union

# Configure logger for the agent framework
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# ---------------------------------------------------------------------------
# Enumerations and Configuration Data Models
# ---------------------------------------------------------------------------

class AgentRole(Enum):
    """Enumeration defining the specialized role of an agent instance."""
    RECOMMENDER = auto()
    ANALYST = auto()
    CUSTOMER_SUPPORT = auto()
    INVENTORY_BOT = auto()


class ActionType(Enum):
    """Enumeration representing the type of action taken by an agent."""
    FETCH_DATA = auto()
    GENERATE_RECOMMENDATION = auto()
    ASK_CLARIFICATION = auto()
    EXECUTE_TOOL = auto()
    FAIL = auto()


@dataclass
class AgentConfig:
    """Configuration structure controlling agent behavior and hyper-parameters.
    
    Attributes:
        role (AgentRole): Operational role assigned to the agent.
        model_name (str): Identifier for the underlying LLM/Model (default: "default-model").
        max_context_length (int): Maximum dialogue turns stored in active memory (default: 10).
        temperature (float): Sampling temperature for generation randomness (default: 0.7).
        timeout (int): Seconds allowed per action turnaround (default: 15).
    """
    role: AgentRole = AgentRole.RECOMMENDER
    model_name: str = "default-model"
    max_context_length: int = 10
    temperature: float = 0.7
    timeout: int = 15


@dataclass
class AgentResponse:
    """Standard output object returned by an agent after processing a query.
    
    Attributes:
        session_id (str): Unique session tracker string.
        action_type (ActionType): Categorization of the action taken.
        content (str): Textual response or decision summary generated for the user.
        metadata (Dict[str, Any]): Additional execution payloads (e.g., product IDs, metrics).
        errors (Optional[List[str]]): List of errors encountered during execution.
    """
    session_id: str
    action_type: ActionType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Memory Management Component
# ---------------------------------------------------------------------------

class AgentMemory:
    """In-memory contextual buffer for tracking interaction histories per user/session."""

    def __init__(self, max_history: int = 10) -> None:
        self.max_history = max_history
        self._buffer: List[Dict[str, str]] = []

    def add_interaction(self, role: str, message: str) -> None:
        """Appends a new conversation entry to the active context memory buffer.
        
        Args:
            role (str): Sender identifier ('user', 'agent', 'system').
            message (str): Text content of the interaction.
        """
        self._buffer.append({"role": role, "content": message})
        if len(self._buffer) > self.max_history:
            self._buffer.pop(0)  # Evict oldest entry

    def get_history(self) -> List[Dict[str, str]]:
        """Retrieves a copy of current conversation history."""
        return list(self._buffer)

    def clear(self) -> None:
        """Purges all entries from active memory."""
        self._buffer.clear()


# ---------------------------------------------------------------------------
# Exception Hierarchy
# ---------------------------------------------------------------------------

class AgentError(Exception):
    """Base exception class for errors occurring within the agent execution layer."""
    pass


class AgentExecutionError(AgentError):
    """Raised when an internal agent tool or reasoning step encounters a failure."""
    pass


class ContextOverflowError(AgentError):
    """Raised when memory inputs exceed allowed limits."""
    pass


# ---------------------------------------------------------------------------
# Abstract Base Agent Interface
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """Abstract Base Class (ABC) defining contract methods for all BuyWise-AI Agents."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.memory = AgentMemory(max_history=config.max_context_length)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @abstractmethod
    def plan(self, user_input: str) -> ActionType:
        """Determines the appropriate action strategy based on incoming prompt."""
        pass

    @abstractmethod
    def execute_action(self, action: ActionType, user_input: str) -> Dict[str, Any]:
        """Executes targeted action logic or tool calls."""
        pass

    @abstractmethod
    def process_query(self, user_id: str, user_input: str) -> AgentResponse:
        """Orchestrates end-to-end memory updating, planning, and execution."""
        pass


# ---------------------------------------------------------------------------
# Concrete Implementation: E-Commerce AI Agent
# ---------------------------------------------------------------------------

class ECommerceAgent(BaseAgent):
    """Concrete AI Agent focused on product search, recommendation, and user intent handling."""

    def plan(self, user_input: str) -> ActionType:
        """Evaluates user input keywords to select execution path."""
        cleaned = user_input.lower().strip()
        
        if not cleaned:
            return ActionType.FAIL
        elif any(keyword in cleaned for keyword in ["buy", "recommend", "looking for", "best"]):
            return ActionType.GENERATE_RECOMMENDATION
        elif any(keyword in cleaned for keyword in ["where is", "track", "status", "order"]):
            return ActionType.FETCH_DATA
        else:
            return ActionType.ASK_CLARIFICATION

    def execute_action(self, action: ActionType, user_input: str) -> Dict[str, Any]:
        """Runs domain-specific operations according to planned ActionType."""
        if action == ActionType.GENERATE_RECOMMENDATION:
            # Mock retrieval/recommendation output logic
            return {
                "response": "Based on your criteria, here are top recommendations: [Product A, Product B].",
                "recommended_ids": ["P101", "P102"],
                "confidence_score": 0.94
            }
        
        elif action == ActionType.FETCH_DATA:
            return {
                "response": "Fetching order status... Your item is currently in transit.",
                "order_id": "ORD-9921",
                "status": "IN_TRANSIT"
            }
            
        elif action == ActionType.ASK_CLARIFICATION:
            return {
                "response": "Could you please specify your preferred category or target budget range?",
                "needs_further_input": True
            }

        elif action == ActionType.FAIL:
            raise AgentExecutionError("Empty input received; cannot perform agent action planning.")
            
        else:
            raise NotImplementedError(f"Action type '{action}' is not supported.")

    def process_query(self, user_id: str, user_input: str) -> AgentResponse:
        """Full pipeline execution: updates memory, plans strategy, and generates response."""
        session_id = str(uuid.uuid4())[:8]
        self.logger.info(f"Processing query for user '{user_id}' [Session: {session_id}]")

        # 1. Update Context Memory
        self.memory.add_interaction(role="user", message=user_input)

        try:
            # 2. Plan Next Action
            action = self.plan(user_input)
            
            # 3. Execute Decision Core
            result = self.execute_action(action=action, user_input=user_input)
            
            # 4. Formulate Output
            content = result.get("response", "No payload generated.")
            self.memory.add_interaction(role="agent", message=content)

            return AgentResponse(
                session_id=session_id,
                action_type=action,
                content=content,
                metadata={
                    "user_id": user_id,
                    "model_used": self.config.model_name,
                    "execution_payload": result
                }
            )

        except AgentExecutionError as e:
            self.logger.error(f"Agent execution error caught: {str(e)}")
            return AgentResponse(
                session_id=session_id,
                action_type=ActionType.FAIL,
                content="I encountered an issue processing your request.",
                errors=[str(e)]
            )
        except Exception as e:
            self.logger.critical(f"Unhandled error in agent pipeline: {str(e)}")
            return AgentResponse(
                session_id=session_id,
                action_type=ActionType.FAIL,
                content="Critical agent error occurred.",
                errors=[f"Unhandled exception: {str(e)}"]
            )


# ---------------------------------------------------------------------------
# Module Exports
# ---------------------------------------------------------------------------

__all__ = [
    # Models & Config
    "AgentRole",
    "ActionType",
    "AgentConfig",
    "AgentResponse",
    "AgentMemory",
    
    # Exceptions
    "AgentError",
    "AgentExecutionError",
    "ContextOverflowError",
    
    # Core Classes
    "BaseAgent",
    "ECommerceAgent"
]
