# Necessary Imports ------------------------------------------
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from agno.tools.mcp import MultiMCPTools
from a2a.utils import new_task
from rich.pretty import pprint
from rich import print as cprint
import logging
from a2a.types import (
    InternalError,
    Part,
    TextPart,
    TaskState,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from mcp_agent import McpAgent
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

 
# Connecting to MCP Servers and Fetching MCP-Server hosted Tools
async def get_mcp_tools():
        # Configuration for the MCP Servers
        multi_mcp_tools = MultiMCPTools(
            urls=["http://127.0.0.1:8111/mcptoolserver"],
            urls_transports= ['streamable-http']
        )
        
        #Connect to the Multiple MCP Servers
        await multi_mcp_tools.connect()
        return multi_mcp_tools

# Implementation of the Agent Executor that provides the MCP Server hosted Tools to the Agent
class MCPAgentExecutor(AgentExecutor):
    """Websearch Remote Agent Implementation."""
    def __init__(self):
        self.agent = None
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        # Checking if Context Exists ------------------------------------------
        if not context:
            raise ServerError(error=InvalidRequestError())
        
        # Getting the Message (query) sent from the A2A Client ----------------
        query = context.get_user_input()
        
        task = context.current_task
        cprint(f"[bright_yellow]{'='*20} Context Information {'='*30}[/bright_yellow]")
        cprint("[cyan1]Context Id:[/cyan1]",f"[green_yellow]{context.context_id}[/green_yellow]")
        cprint("[cyan1]query:[/cyan1]",f"[green_yellow]{query}[/green_yellow]")
        cprint("[cyan1]Task Id:[/cyan1]",f"[green_yellow]{context.task_id}[/green_yellow]")
        cprint("[cyan1]Context Task:[/cyan1]",f"[green_yellow]{task}[/green_yellow]")
        cprint("[cyan1]Context Message:[/cyan1]",f"[green_yellow]{context.message}[/green_yellow]")
        cprint(f"[bright_yellow]{'-'*70}[/bright_yellow]")
        
        # Creating a New Task if Task does not exists. And adding the same to the event queue.
        if not task:
            task = new_task(context.message)  # type: ignore
            await event_queue.enqueue_event(task)
        # Creating the Task Updater for the Current Task (Task Id) and Context (Context Id)---------
        # - Which adds the Task Updates (Status or concrete Artifacts - responses) to the Event Queue
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        # Invoking the Agent with the receieved query -----------------------------
        try:
            tools= await get_mcp_tools()
            agent=McpAgent([tools],"./")
            result= await agent.invoke(query,task.context_id)
            cprint("[cyan1]Agent Response--------------------------------[/cyan1]")
            pprint(result)
            is_task_complete = result['is_task_complete']
            if is_task_complete:
                await updater.add_artifact(
                        [Part(root=TextPart(text=result['content']))],
                        name='movie_product_search_result',
                    )
                await updater.complete()
        except Exception as e:
            logger.error(f'An error occurred while getting the response: {e}')
            raise
        finally:
            await tools.close()
            
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())
 



