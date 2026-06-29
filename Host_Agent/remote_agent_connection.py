# Necessary Imports------------------
import logging
import httpx
from a2a.client import A2AClient
from collections.abc import Callable
from a2a.types import (
    AgentCard,
    SendMessageRequest,
    SendMessageResponse,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
)
 
TaskCallbackArg=Task|TaskStatusUpdateEvent|TaskArtifactUpdateEvent
TaskUpdateCallback=Callable[[TaskCallbackArg,AgentCard],Task]
logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)
 
class RemoteAgentConnection:
    """A class to hold the connection to the remote agents."""
    def __init__(self,agent_card:AgentCard,agent_url:str):
        logger.info(f'agent_card: {agent_card}')
        logger.info(f'agent_url: {agent_url}')
        self.httpx_client=httpx.AsyncClient(timeout=300)
        self.agent_client=A2AClient(self.httpx_client,agent_card,url=agent_url)
        self.card=agent_card
    
    def get_agent(self)->AgentCard:
        return self.card
    
    # Method to Send a non-streaming message request to the Remote agent.
    async def send_message(self,message_request:SendMessageRequest)->SendMessageResponse:
        return await self.agent_client.send_message(message_request)