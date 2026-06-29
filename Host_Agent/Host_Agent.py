# Necessary Imports and Utility Functions--------------------------------
import asyncio
import json
import os
import uuid
import logging
import httpx
from dotenv import load_dotenv
from a2a.client import A2ACardResolver
from rich.pretty import pprint
from rich import print as cprint
from a2a.types import (
    AgentCard,
    Task,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
)
from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from remote_agent_connection import RemoteAgentConnection,TaskUpdateCallback
import os
 
load_dotenv()
 
logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)
 
def read_json_as_dict(filename: str)->dict:
    """
    Reads a JSON file and returns its content as a Python dictionary.
    """
    try:
        print(filename)
        with open(filename, 'r') as file:
            # Use json.load() to deserialize the file content into a Python object
            data_dict = json.load(file)
            return data_dict
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{filename}'. Check file formatting.")
        return None
 
def llmAWS():
    llm = LiteLlm( model='amazon.nova-lite-v1:0')
    return llm
"""
def llmCohere():
    llm=LiteLlm(model="command-a-03-2025")
    return llm
 
def llmOllama():
    OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE","http://127.0.0.1:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    llm = LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base = OLLAMA_API_BASE)
    return llm
"""
# Host (routing) Agent Implementation-------------------------------
class HostAgent:
    """The host agent.
    This is the agent responsible for choosing which remote agents to send the tasks to and coordinate their work."""
    def __init__(self,task_callback: TaskUpdateCallback |None=None):
        self.task_callback=task_callback
        self.remote_agent_connections:dict[str,RemoteAgentConnection]={}
        self.cards:dict[str,AgentCard]={}
        self.agents:str=""
 
    def list_remote_agents(self):
        """List all the available remote agents with their skills from their Agent Cards 
        Which can be used to delegate the task."""
        if not self.remote_agent_connections:
            return []
        else:
            remote_agent_info =[]
            for card in self.cards.values():
                logger.info(
                    'Found agent card: %s',card.model_dump(exclude_none=True)
                )
                # Fetching Agent Skills from Agent Card
                agent_skills = card.skills
                skills = []
                for skill in agent_skills:
                    skills.append({
                        "skill_title": skill.name,
                        "skill_description": skill.description,
                        "skill_example": skill.examples if skill.examples else "Not Mentioned",
                        "skill_tags": skill.tags if skill.tags else "Not Provided"
                    })
                # Creating Agent Information using Information from Agent Card
                # - To be used in the Root Instruction under 'Available Agents' header
                # - Which will give context to the Agnet's LLM to predict the right agent to delegate the Task to
                remote_agent_info.append(
                    {'name':card.name,'description':card.description,
                     'skills': skills}
                )
            return remote_agent_info
        
    async def _async_init_components(self,remote_agent_addresses:list[str])->None:
        """Asynchronous part of initialization.
        Fetching Remote Agent Cards and Creating A2A Clients"""
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as httpx_client:
            # Initialize A2ACardResolver
            for address in remote_agent_addresses:
                card_resolver= A2ACardResolver(
                    httpx_client=httpx_client,
                    base_url=address
                )
                try:
                    card=(
                        await card_resolver.get_agent_card()
                    )
                    remote_connection=RemoteAgentConnection(
                        agent_card=card,
                        agent_url=address
                    )
                    self.remote_agent_connections[card.name]=remote_connection
                    self.cards[card.name]=card
                except httpx.ConnectError as e:
                    logger.debug(
                        'ERROR: Failed to get agent card from %s: %s',
                        address,
                        e
                    )
                except Exception as e:
                    logger.debug(
                        'ERROR: Failed to initialize connection for  %s: %s',
                        address,
                        e
                    )
        print("Successfully fetched public agent cards")
        for agent_name,card in self.cards.items():
            print(agent_name)
            print("-"*100)
            pprint(card)
        agent_info =[]
        for agent_detail_dict in self.list_remote_agents():
            agent_info.append(json.dumps(agent_detail_dict))
        self.agents='\n'.join(agent_info)
 
    @classmethod
    async def create(
        task_callback: TaskUpdateCallback|None=None
    ) -> 'HostAgent':
        """Create and asynchronously initialize an instance of the host agent"""
        instance= HostAgent(task_callback)
        serverConfigFileName="host_agent/serverConfigs.json"
        a2aServerURLs=read_json_as_dict(serverConfigFileName)
        cprint("[bright_yellow]Server URLs:--------------------------------------[/bright_yellow]")
        pprint(a2aServerURLs)
        cprint("[bright_yellow]--------------------------------------------------[/bright_yellow]")
        remote_agent_addresses=a2aServerURLs.values()
        await instance._async_init_components(remote_agent_addresses)
        return instance
    
    def create_agent(self)->Agent:
        """Create an instance of an agent"""
        return Agent(
            model=llmAWS(),
            name='host_agent',
            instruction=self.root_instruction,
            before_model_callback=self.before_model_callback,
            description="""This agent orchestrates the decomposition of the user request into task that can be performed by the remote agents""",
            tools=[
                self.list_remote_agents,
                self.send_message,
            ]
        )
 
    def check_active_agent(self, context: ReadonlyContext):
        state = context.state
        if (
            'session_id' in state
            and 'session_active' in state
            and state['session_active']
            and 'agent' in state
        ):
            return {'active_agent': f'{state["active_agent"]}'}
        return {'active_agent': 'None'}
 
    def root_instruction(self, context: ReadonlyContext) -> str:
        """Generate the root instruction for the HostAgent."""
        current_agent = self.check_active_agent(context)
        return f"""
**Role:** You are an expert delegator that can delegate the user request to the appropriate specialized remote agents.
Discovery:
- You can use `list_remote_agents` to list the available remote agents you can use to delegate the task.
 
**Task Delegation:**
- For actionable requests, you can use `send_message` to interact with remote agents to take action, to assign actionable tasks to remote agents..
 
Be sure to include the remote agent name when you respond to the user.
Important:
# **Tool Reliance:** Strictly rely on available tools to address user requests. Do not generate responses based on assumptions. If information is insufficient, request clarification from the user.
# If you are not sure, please ask the user for more details.
# **Prioritize Recent Interaction:** Focus on the most recent parts of the conversation primarily when processing requests.
# **No Redundant Confirmations:** Do not ask remote agents for confirmation of information or actions.
# **Focused Information Sharing:** Provide remote agents with only relevant contextual information. Avoid extraneous details.
# **Transparent Communication:** Always present the complete and detailed response from the remote agent to the user.
# **Autonomous Agent Engagement:** Never seek user permission before engaging with remote agents. If multiple agents are required to fulfill a request, connect with them directly without requesting user preference or confirmation.
 
**Available Agents:**
{self.agents}
 
**Current Active agent:** {current_agent['active_agent']}
"""
    def before_model_callback(
        self, callback_context: CallbackContext, llm_request
    ):
        state = callback_context.state
        if 'session_active' not in state or not state['session_active']:
            if 'session_id' not in state:
                state['session_id'] = str(uuid.uuid4())
            state['session_active'] = True
 
    async def send_message(
            self,
            agent_name:str,
            message:str,
            tool_context:ToolContext
    ):
        """Sends a task either streaming (if supported) or non-streaming.
 
        This will send a message to the remote agent named agent_name, return the final Task Artifact or Message.
 
        Args:
          agent_name: The name of the agent to send the task to.
          message: The message to send to the agent for the task.
          tool_context: The tool context this method runs in.
 
        Yields:
          A dictionary of JSON data.
        """
       # pprint(tool_context.__dict__)
        if agent_name not in self.remote_agent_connections:
            raise ValueError(f"Agent{agent_name}not founnd. {message}")
        #pprint(tool_context.state.to_dict())
        state=tool_context.state
        state['active_agent']=agent_name
        client=self.remote_agent_connections[agent_name]
        if not client:
            raise ValueError(f'Client not available for {agent_name}')
        task_id=state.get('task_id',None)
        context_id=state.get('session_id',None)
        message_id=""
        metadata={}
        if 'input_message_metadata' in state:
            metadata.update(**state['input_message_metadata'])
            if 'message_id' in state['input_message_metadata']:
                message_id=state['input_message_metadata']['message_id']
        if not message_id:
            message_id=str(uuid.uuid4())
        # Checking Presence of Existing Context and Task IDs (if not, will be created)
        pprint({'context_id':context_id,
                'task_id':task_id,
                'message_id':message_id})
        payload={
            'message': {
                'role': 'user',
                'parts': [
                    {'type': 'text', 'text':message}
                ],
                'messageId': message_id,
            },
        }
        if task_id:
            payload['message']['taskId']=task_id
        if context_id:
            payload['message']['contextId']=context_id
        message_request=SendMessageRequest(
                        id=message_id, params=MessageSendParams.model_validate(payload)
                    )
        send_response=SendMessageResponse=await client.send_message(
            message_request=message_request
        )
        logger.info(
            'send_response',
            send_response.model_dump_json(exclude_none=True,indent=2)
        )
        if not isinstance(send_response.root,SendMessageSuccessResponse):
            logger.info('recived non successs response aborting the get task')
            return None
        if not isinstance(send_response.root.result,Task):
            logger.info('received non-task response. aborting get task')
            return None
        result=send_response.root.result
        if hasattr(result,'artifacts') and result.artifacts:
            artifact=result.artifacts[0]
        elif hasattr(result,'artifact') and result.artifact:
            artifact=result.artifact
        elif hasattr(result,'content') and result.content:
            logger.info('Successfully retrieved response from A2A server')
            content=result.content
            return content
        else:
            logger.warning("No content found in a2a server response")
            print("No response form a2a server")
            return None
        if artifact:
            if hasattr(artifact,'parts') and artifact.parts:
                part=artifact.parts[0]
                if hasattr(part,'root') and part.root:
                    content=part.root.text
                    logger.info("Successfully retrieved response form A2A server")
                    return content
        return content