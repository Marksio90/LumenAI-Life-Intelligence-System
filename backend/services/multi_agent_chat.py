"""
Multi-Agent Chat System

Enables concurrent conversations with multiple AI agents simultaneously.
Each agent can have specialized capabilities and personality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from uuid import uuid4
from dataclasses import dataclass, field

from backend.core.websocket_manager import get_connection_manager
from backend.services.streaming_service import get_streaming_service
from backend.core.agent_registry import get_agent_registry

logger = logging.getLogger(__name__)


@dataclass
class AgentParticipant:
    """Represents an agent participating in a conversation."""
    agent_name: str
    agent_type: str
    capabilities: List[str]
    personality: Optional[str] = None
    is_active: bool = True
    message_count: int = 0
    last_message_at: Optional[datetime] = None


@dataclass
class MultiAgentConversation:
    """Represents a multi-agent conversation."""
    conversation_id: str
    user_id: str
    participants: Dict[str, AgentParticipant] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiAgentChatService:
    """
    Service for managing multi-agent conversations.

    Features:
    - Multiple agents in one conversation
    - Agent specialization and routing
    - Concurrent agent responses
    - Agent-to-agent communication
    - Context sharing between agents
    """

    def __init__(self):
        self.conversations: Dict[str, MultiAgentConversation] = {}
        self.connection_manager = get_connection_manager()
        self.streaming_service = get_streaming_service()
        self.agent_registry = get_agent_registry()
        logger.info("MultiAgentChatService initialized")

    async def create_conversation(
        self,
        user_id: str,
        agent_names: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new multi-agent conversation.

        Args:
            user_id: User creating the conversation
            agent_names: List of agent names to include
            metadata: Optional conversation metadata

        Returns:
            conversation_id: Unique conversation identifier
        """
        conversation_id = str(uuid4())

        # Get agent details from registry
        participants = {}
        for agent_name in agent_names:
            agents = self.agent_registry.get_agents_by_name(agent_name)
            if agents:
                agent = agents[0]
                participants[agent_name] = AgentParticipant(
                    agent_name=agent_name,
                    agent_type=agent.handler.__class__.__name__ if hasattr(agent, 'handler') else "unknown",
                    capabilities=[cap.name for cap in agent.capabilities] if hasattr(agent, 'capabilities') else [],
                    personality=metadata.get(f"{agent_name}_personality") if metadata else None
                )

        # Create conversation
        conversation = MultiAgentConversation(
            conversation_id=conversation_id,
            user_id=user_id,
            participants=participants,
            metadata=metadata or {}
        )

        self.conversations[conversation_id] = conversation

        # Notify user
        await self.connection_manager.send_to_user(user_id, {
            "type": "multi_agent.conversation.created",
            "conversation_id": conversation_id,
            "participants": [
                {
                    "agent_name": p.agent_name,
                    "agent_type": p.agent_type,
                    "capabilities": p.capabilities
                }
                for p in participants.values()
            ],
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(
            f"Multi-agent conversation created: id={conversation_id}, "
            f"user={user_id}, agents={agent_names}"
        )

        return conversation_id

    async def add_agent(
        self,
        conversation_id: str,
        agent_name: str
    ) -> bool:
        """
        Add an agent to an existing conversation.

        Args:
            conversation_id: Conversation identifier
            agent_name: Agent name to add

        Returns:
            Success status
        """
        if conversation_id not in self.conversations:
            logger.error(f"Conversation not found: {conversation_id}")
            return False

        conversation = self.conversations[conversation_id]

        if agent_name in conversation.participants:
            logger.warning(f"Agent already in conversation: {agent_name}")
            return False

        # Add agent
        agents = self.agent_registry.get_agents_by_name(agent_name)
        if agents:
            agent = agents[0]
            conversation.participants[agent_name] = AgentParticipant(
                agent_name=agent_name,
                agent_type=agent.handler.__class__.__name__ if hasattr(agent, 'handler') else "unknown",
                capabilities=[cap.name for cap in agent.capabilities] if hasattr(agent, 'capabilities') else []
            )

            # Notify
            await self.connection_manager.send_to_user(conversation.user_id, {
                "type": "multi_agent.agent.joined",
                "conversation_id": conversation_id,
                "agent_name": agent_name,
                "timestamp": datetime.utcnow().isoformat()
            })

            return True

        return False

    async def remove_agent(
        self,
        conversation_id: str,
        agent_name: str
    ) -> bool:
        """
        Remove an agent from a conversation.

        Args:
            conversation_id: Conversation identifier
            agent_name: Agent name to remove

        Returns:
            Success status
        """
        if conversation_id not in self.conversations:
            return False

        conversation = self.conversations[conversation_id]

        if agent_name in conversation.participants:
            conversation.participants[agent_name].is_active = False

            await self.connection_manager.send_to_user(conversation.user_id, {
                "type": "multi_agent.agent.left",
                "conversation_id": conversation_id,
                "agent_name": agent_name,
                "timestamp": datetime.utcnow().isoformat()
            })

            return True

        return False

    async def send_message(
        self,
        conversation_id: str,
        content: str,
        sender: str = "user",
        target_agent: Optional[str] = None,
        stream: bool = True
    ) -> Dict[str, Any]:
        """
        Send a message in a multi-agent conversation.

        Args:
            conversation_id: Conversation identifier
            content: Message content
            sender: Message sender (user or agent name)
            target_agent: Optional specific agent to respond
            stream: Whether to stream responses

        Returns:
            Response metadata
        """
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation not found: {conversation_id}")

        conversation = self.conversations[conversation_id]

        # Add message to history
        message = {
            "id": str(uuid4()),
            "sender": sender,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "target_agent": target_agent
        }
        conversation.messages.append(message)
        conversation.updated_at = datetime.utcnow()

        # Notify message received
        await self.connection_manager.send_to_user(conversation.user_id, {
            "type": "multi_agent.message.received",
            "conversation_id": conversation_id,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Determine which agents should respond
        responding_agents = []
        if target_agent and target_agent in conversation.participants:
            responding_agents = [target_agent]
        else:
            # All active agents can respond
            responding_agents = [
                name for name, participant in conversation.participants.items()
                if participant.is_active
            ]

        # Get responses from agents (optionally in parallel)
        responses = await self._get_agent_responses(
            conversation,
            content,
            responding_agents,
            stream
        )

        return {
            "conversation_id": conversation_id,
            "message_id": message["id"],
            "responding_agents": responding_agents,
            "responses": responses
        }

    async def _get_agent_responses(
        self,
        conversation: MultiAgentConversation,
        user_message: str,
        agent_names: List[str],
        stream: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get responses from multiple agents.

        Args:
            conversation: The conversation
            user_message: User's message
            agent_names: List of agents to get responses from
            stream: Whether to stream responses

        Returns:
            List of agent responses
        """
        # Prepare conversation context
        context_messages = [
            {"role": "user" if msg["sender"] == "user" else "assistant", "content": msg["content"]}
            for msg in conversation.messages[-10:]  # Last 10 messages
        ]

        responses = []

        if len(agent_names) == 1:
            # Single agent - simple response
            response = await self._get_single_agent_response(
                conversation,
                agent_names[0],
                context_messages,
                stream
            )
            responses.append(response)

        else:
            # Multiple agents - parallel responses
            tasks = [
                self._get_single_agent_response(
                    conversation,
                    agent_name,
                    context_messages,
                    stream
                )
                for agent_name in agent_names
            ]

            responses = await asyncio.gather(*tasks, return_exceptions=True)

        return responses

    async def _get_single_agent_response(
        self,
        conversation: MultiAgentConversation,
        agent_name: str,
        context_messages: List[Dict[str, str]],
        stream: bool = True
    ) -> Dict[str, Any]:
        """
        Get response from a single agent.

        Args:
            conversation: The conversation
            agent_name: Agent name
            context_messages: Conversation context
            stream: Whether to stream response

        Returns:
            Agent response metadata
        """
        participant = conversation.participants.get(agent_name)
        if not participant:
            return {"error": f"Agent not found: {agent_name}"}

        try:
            # Add agent personality to system message
            system_message = {
                "role": "system",
                "content": f"You are {agent_name}."
            }

            if participant.personality:
                system_message["content"] += f" {participant.personality}"

            messages = [system_message] + context_messages

            # Stream response
            if stream:
                full_response = ""
                async for chunk in self.streaming_service.stream_openai_completion(
                    user_id=conversation.user_id,
                    messages=messages,
                    model="gpt-4-turbo-preview"
                ):
                    full_response += chunk

                # Add agent response to conversation
                conversation.messages.append({
                    "id": str(uuid4()),
                    "sender": agent_name,
                    "content": full_response,
                    "timestamp": datetime.utcnow().isoformat()
                })

                # Update participant stats
                participant.message_count += 1
                participant.last_message_at = datetime.utcnow()

                return {
                    "agent_name": agent_name,
                    "content": full_response,
                    "streamed": True
                }

            else:
                # Non-streaming (for background/batch processing)
                # TODO: Implement non-streaming version
                return {
                    "agent_name": agent_name,
                    "content": "Non-streaming not yet implemented",
                    "streamed": False
                }

        except Exception as e:
            logger.error(f"Error getting response from {agent_name}: {e}")
            return {
                "agent_name": agent_name,
                "error": str(e)
            }

    async def agent_to_agent_message(
        self,
        conversation_id: str,
        from_agent: str,
        to_agent: str,
        content: str
    ):
        """
        Send a message from one agent to another.

        Args:
            conversation_id: Conversation identifier
            from_agent: Sending agent name
            to_agent: Receiving agent name
            content: Message content
        """
        if conversation_id not in self.conversations:
            return

        conversation = self.conversations[conversation_id]

        # Add message
        message = {
            "id": str(uuid4()),
            "sender": from_agent,
            "content": content,
            "target_agent": to_agent,
            "type": "agent_to_agent",
            "timestamp": datetime.utcnow().isoformat()
        }
        conversation.messages.append(message)

        # Notify user
        await self.connection_manager.send_to_user(conversation.user_id, {
            "type": "multi_agent.agent_message",
            "conversation_id": conversation_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_conversation(
        self,
        conversation_id: str
    ) -> Optional[MultiAgentConversation]:
        """Get conversation by ID."""
        return self.conversations.get(conversation_id)

    def get_user_conversations(
        self,
        user_id: str
    ) -> List[MultiAgentConversation]:
        """Get all conversations for a user."""
        return [
            conv for conv in self.conversations.values()
            if conv.user_id == user_id
        ]

    async def close_conversation(
        self,
        conversation_id: str
    ):
        """Close a multi-agent conversation."""
        if conversation_id in self.conversations:
            conversation = self.conversations[conversation_id]

            await self.connection_manager.send_to_user(conversation.user_id, {
                "type": "multi_agent.conversation.closed",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            del self.conversations[conversation_id]
            logger.info(f"Conversation closed: {conversation_id}")


# Global instance
_multi_agent_service = None


def get_multi_agent_service() -> MultiAgentChatService:
    """Get or create the global MultiAgentChatService instance."""
    global _multi_agent_service
    if _multi_agent_service is None:
        _multi_agent_service = MultiAgentChatService()
    return _multi_agent_service
