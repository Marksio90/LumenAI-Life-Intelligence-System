"""
Agent Registry System with Load Balancing

Features:
- Auto-discovery of agents
- Dynamic routing based on capabilities
- Load balancing across agent instances
- Health monitoring
- Circuit breaker pattern
- Performance metrics
- Agent specialization framework
"""

import asyncio
from typing import Dict, List, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
from collections import defaultdict

from core.logging_config import get_logger

logger = get_logger(__name__)


class AgentStatus(str, Enum):
    """Agent health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    WEIGHTED = "weighted"


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    description: str
    confidence_score: float  # 0.0 to 1.0
    cost_tier: int  # 1=cheap, 5=expensive
    avg_latency_ms: float = 0.0


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    circuit_breaker_open: bool = False
    consecutive_failures: int = 0


@dataclass
class RegisteredAgent:
    """Registered agent with metadata"""
    name: str
    capabilities: List[AgentCapability]
    handler: Callable
    priority: int = 1
    max_concurrent_requests: int = 10
    timeout_seconds: float = 30.0
    tags: Set[str] = field(default_factory=set)
    status: AgentStatus = AgentStatus.HEALTHY
    metrics: AgentMetrics = field(default_factory=AgentMetrics)
    created_at: datetime = field(default_factory=datetime.utcnow)
    current_load: int = 0


class CircuitBreaker:
    """Circuit breaker for agent calls"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half_open
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if recovery timeout passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker entering half-open state")
                    self.state = "half_open"
                    self.half_open_calls = 0
                    return True
            return False

        if self.state == "half_open":
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self):
        """Record successful execution"""
        if self.state == "half_open":
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                logger.info("Circuit breaker closing after successful recoveries")
                self.state = "closed"
                self.failure_count = 0

    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == "half_open":
            logger.warning("Circuit breaker reopening after half-open failure")
            self.state = "open"
            self.half_open_calls = 0
        elif self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit breaker opening after {self.failure_count} failures")
            self.state = "open"


class AgentRegistry:
    """
    Central registry for all agents

    Features:
    - Agent registration and discovery
    - Capability-based routing
    - Load balancing strategies
    - Health monitoring
    - Circuit breaker pattern
    - Performance metrics
    """

    def __init__(
        self,
        load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_LOADED,
        health_check_interval: int = 60
    ):
        self.load_balancing_strategy = load_balancing_strategy
        self.health_check_interval = health_check_interval

        # Storage
        self.agents: Dict[str, RegisteredAgent] = {}
        self.capability_index: Dict[str, List[str]] = defaultdict(list)  # capability -> agent_names
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Round-robin counters
        self._round_robin_counters: Dict[str, int] = defaultdict(int)

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None

        logger.info(f"Agent registry initialized with {load_balancing_strategy.value} strategy")

    async def start(self):
        """Start background tasks"""
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Agent registry started")

    async def stop(self):
        """Stop background tasks"""
        if self._health_check_task:
            self._health_check_task.cancel()
        logger.info("Agent registry stopped")

    def register_agent(
        self,
        name: str,
        handler: Callable,
        capabilities: List[AgentCapability],
        priority: int = 1,
        max_concurrent_requests: int = 10,
        timeout_seconds: float = 30.0,
        tags: Optional[Set[str]] = None
    ) -> RegisteredAgent:
        """
        Register an agent

        Args:
            name: Unique agent name
            handler: Async callable for agent execution
            capabilities: List of agent capabilities
            priority: Higher priority agents are preferred
            max_concurrent_requests: Max concurrent requests
            timeout_seconds: Request timeout
            tags: Optional tags for filtering

        Returns:
            Registered agent
        """
        agent = RegisteredAgent(
            name=name,
            handler=handler,
            capabilities=capabilities,
            priority=priority,
            max_concurrent_requests=max_concurrent_requests,
            timeout_seconds=timeout_seconds,
            tags=tags or set()
        )

        self.agents[name] = agent
        self.circuit_breakers[name] = CircuitBreaker()

        # Index capabilities
        for capability in capabilities:
            self.capability_index[capability.name].append(name)

        logger.info(f"Registered agent: {name} with {len(capabilities)} capabilities")
        return agent

    def unregister_agent(self, name: str) -> bool:
        """Unregister an agent"""
        if name in self.agents:
            agent = self.agents[name]

            # Remove from capability index
            for capability in agent.capabilities:
                if name in self.capability_index[capability.name]:
                    self.capability_index[capability.name].remove(name)

            del self.agents[name]
            del self.circuit_breakers[name]

            logger.info(f"Unregistered agent: {name}")
            return True
        return False

    def get_agents_by_capability(
        self,
        capability: str,
        min_confidence: float = 0.0,
        tags: Optional[Set[str]] = None
    ) -> List[RegisteredAgent]:
        """
        Get agents by capability

        Args:
            capability: Capability name
            min_confidence: Minimum confidence score
            tags: Optional tag filter

        Returns:
            List of matching agents
        """
        agent_names = self.capability_index.get(capability, [])
        matching_agents = []

        for name in agent_names:
            agent = self.agents[name]

            # Check status
            if agent.status == AgentStatus.OFFLINE:
                continue

            # Check tags
            if tags and not agent.tags.intersection(tags):
                continue

            # Check confidence
            cap = next((c for c in agent.capabilities if c.name == capability), None)
            if cap and cap.confidence_score >= min_confidence:
                matching_agents.append(agent)

        # Sort by priority
        matching_agents.sort(key=lambda a: a.priority, reverse=True)

        return matching_agents

    def select_agent(
        self,
        capability: str,
        strategy: Optional[LoadBalancingStrategy] = None
    ) -> Optional[RegisteredAgent]:
        """
        Select best agent for capability using load balancing

        Args:
            capability: Required capability
            strategy: Load balancing strategy (uses default if not provided)

        Returns:
            Selected agent or None
        """
        agents = self.get_agents_by_capability(capability)

        if not agents:
            logger.warning(f"No agents found for capability: {capability}")
            return None

        strategy = strategy or self.load_balancing_strategy

        # Filter out agents that are at capacity or unhealthy
        available_agents = [
            agent for agent in agents
            if (agent.current_load < agent.max_concurrent_requests and
                agent.status in [AgentStatus.HEALTHY, AgentStatus.DEGRADED] and
                self.circuit_breakers[agent.name].can_execute())
        ]

        if not available_agents:
            logger.warning(f"No available agents for capability: {capability}")
            return None

        # Apply strategy
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            counter = self._round_robin_counters[capability]
            selected = available_agents[counter % len(available_agents)]
            self._round_robin_counters[capability] = counter + 1

        elif strategy == LoadBalancingStrategy.LEAST_LOADED:
            selected = min(available_agents, key=lambda a: a.current_load)

        elif strategy == LoadBalancingStrategy.WEIGHTED:
            # Weight by priority and inverse load
            def weight(agent: RegisteredAgent) -> float:
                load_factor = 1.0 / (agent.current_load + 1)
                return agent.priority * load_factor

            selected = max(available_agents, key=weight)

        else:  # RANDOM
            import random
            selected = random.choice(available_agents)

        return selected

    async def execute_agent(
        self,
        agent_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute agent with circuit breaker and metrics

        Args:
            agent_name: Agent to execute
            *args: Arguments for agent handler
            **kwargs: Keyword arguments for agent handler

        Returns:
            Agent result
        """
        agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {agent_name}")

        circuit_breaker = self.circuit_breakers[agent_name]

        # Check circuit breaker
        if not circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for agent: {agent_name}")
            raise RuntimeError(f"Circuit breaker open for agent: {agent_name}")

        # Track load
        agent.current_load += 1
        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                agent.handler(*args, **kwargs),
                timeout=agent.timeout_seconds
            )

            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            agent.metrics.total_requests += 1
            agent.metrics.successful_requests += 1
            agent.metrics.last_request_time = datetime.utcnow()
            agent.metrics.consecutive_failures = 0

            # Update average latency
            current_avg = agent.metrics.avg_latency_ms
            total = agent.metrics.total_requests
            agent.metrics.avg_latency_ms = (current_avg * (total - 1) + elapsed_ms) / total

            # Record success
            circuit_breaker.record_success()

            return result

        except Exception as e:
            # Update metrics
            agent.metrics.total_requests += 1
            agent.metrics.failed_requests += 1
            agent.metrics.consecutive_failures += 1

            # Record failure
            circuit_breaker.record_failure()

            # Update status
            if agent.metrics.consecutive_failures >= 3:
                agent.status = AgentStatus.DEGRADED
            if agent.metrics.consecutive_failures >= 5:
                agent.status = AgentStatus.UNHEALTHY

            logger.error(f"Agent execution failed: {agent_name} - {e}")
            raise

        finally:
            agent.current_load -= 1

    async def _health_check_loop(self):
        """Background health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on all agents"""
        for name, agent in self.agents.items():
            # Auto-recover if no recent failures
            if agent.metrics.consecutive_failures == 0:
                agent.status = AgentStatus.HEALTHY

            # Check if agent is responsive
            if agent.metrics.last_request_time:
                elapsed = datetime.utcnow() - agent.metrics.last_request_time
                if elapsed > timedelta(minutes=10):
                    agent.status = AgentStatus.DEGRADED

        logger.debug("Health check completed")

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_agents = len(self.agents)
        healthy = sum(1 for a in self.agents.values() if a.status == AgentStatus.HEALTHY)
        degraded = sum(1 for a in self.agents.values() if a.status == AgentStatus.DEGRADED)
        unhealthy = sum(1 for a in self.agents.values() if a.status == AgentStatus.UNHEALTHY)

        total_requests = sum(a.metrics.total_requests for a in self.agents.values())
        total_successful = sum(a.metrics.successful_requests for a in self.agents.values())

        return {
            "total_agents": total_agents,
            "healthy_agents": healthy,
            "degraded_agents": degraded,
            "unhealthy_agents": unhealthy,
            "total_requests": total_requests,
            "total_successful": total_successful,
            "success_rate": f"{(total_successful / total_requests * 100):.2f}%" if total_requests > 0 else "0%",
            "capabilities": len(self.capability_index)
        }


# Global registry instance
_agent_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get or create global agent registry"""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry
