# Necessary Imports ------------------------------------------
from typing import Any
from rich.pretty import pprint
import asyncio
from dotenv import load_dotenv
from uuid import uuid4
from agno.db.sqlite import SqliteDb
from agno.agent import Agent, RunOutput
from agno.tools.mcp import MultiMCPTools
#from agno.models.cohere import Cohere
from agno.models.aws import AwsBedrock
#from agno.models.ollama import Ollama
load_dotenv()

def llmAws():
    return AwsBedrock(id="amazon.nova-lite-v1:0", 
                              aws_region="us-east-1", 
                              temperature=0.9)
 
  
# Defining the Movie and Stock Product Information Agent----------------------------------
class McpAgent:
 
    SUPPORTED_CONTENT_TYPES=['text','text/plain']
 
    def __init__(self,tools,path:str=''):
        self.model = llmAws()
        self.tools = tools
        self.agent = self.get_agent(path)
 
    def handle_erros(self,e:ValueError) ->str:
        return 'Invalid Input provided'
 
    def get_agent(self,path:str=''):
        instructions = """You are a helpful  assistant ,which can answer queries on products in stock and movies
        ## INSTRUCTIONS:
        # - Always use the provided tools to answer questions
        # - Provide well structured output, use lists, bullet point and tables as required.
        """
        agent= Agent(
            name="Movie and Stock Product Information Agent",
            description='Performs search on Movie and Stock Product databases to retrieve related information',
            model= self.model,
            tools= self.tools,
            markdown= True,
            instructions=[instructions],
            db= SqliteDb(session_table="agent_sessions",
                         db_file=f"{path}/agno_mcp_agent/agno_sessions/agno_agent_storage.db"),
            add_history_to_context=True,
            read_chat_history= True,
            num_history_runs=3,
        )
        return agent
    # ------ Implementation code continues------------------------



    #--- Invoke Method of the Movie and Stock Product Information Agent----------------------
    async def invoke(self, query, context_id) -> dict[str, Any]:
        print(query)
        response: RunOutput = await self.agent.arun(query,session_id=context_id)
        message = response.messages[-1].content
        pprint(response)
        status = response.status
        print(message, status)
        return {
                    'is_task_complete': True,
                    'content':message,
                }
    