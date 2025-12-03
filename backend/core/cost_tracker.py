"""
Cost Tracker for LLM Usage
Monitors and logs API costs in real-time
"""

from typing import Dict, Optional
from datetime import datetime
from loguru import logger
import json


class CostTracker:
    """Track LLM API costs"""

    # Pricing per 1M tokens (January 2025)
    PRICING = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    }

    def __init__(self):
        self.total_cost = 0.0
        self.requests = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.model_usage = {}

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for a request"""

        # Get pricing for model (default to gpt-4o-mini if not found)
        pricing = self.PRICING.get(model, self.PRICING["gpt-4o-mini"])

        # Calculate cost (per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        return total_cost

    def track_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        user_id: Optional[str] = None
    ):
        """Track a single request"""

        cost = self.calculate_cost(model, input_tokens, output_tokens)

        # Update totals
        self.total_cost += cost
        self.requests += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Track per model
        if model not in self.model_usage:
            self.model_usage[model] = {
                "requests": 0,
                "cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0
            }

        self.model_usage[model]["requests"] += 1
        self.model_usage[model]["cost"] += cost
        self.model_usage[model]["input_tokens"] += input_tokens
        self.model_usage[model]["output_tokens"] += output_tokens

        # Log
        logger.info(
            f"💰 LLM Cost: ${cost:.6f} | Model: {model} | "
            f"Tokens: {input_tokens}→{output_tokens} | "
            f"Total: ${self.total_cost:.4f}"
        )

        return cost

    def get_stats(self) -> Dict:
        """Get cost statistics"""
        return {
            "total_cost": round(self.total_cost, 4),
            "total_requests": self.requests,
            "average_cost_per_request": round(
                self.total_cost / max(self.requests, 1), 6
            ),
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "model_breakdown": self.model_usage
        }

    def estimate_monthly_cost(self, requests_per_day: int = 100) -> float:
        """Estimate monthly cost based on average"""
        if self.requests == 0:
            return 0.0

        avg_cost = self.total_cost / self.requests
        monthly = avg_cost * requests_per_day * 30
        return round(monthly, 2)


# Global tracker instance
cost_tracker = CostTracker()
