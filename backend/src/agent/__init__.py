"""Agent module for natural language analytics queries.

Translates user questions into semantic queries via LLM, executes them,
and generates narrative responses with optional chart specs.
"""

from src.agent.guardrails import RateLimitExceededError
from src.agent.models import AgentResponse, ChartSeries, ChartSpec
from src.agent.service import AgentError, AgentService

__all__ = [
    "AgentError",
    "AgentResponse",
    "AgentService",
    "ChartSeries",
    "ChartSpec",
    "RateLimitExceededError",
]
