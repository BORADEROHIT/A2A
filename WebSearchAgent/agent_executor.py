##-----------------Imports-----------------
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.utils import new_task
from a2a.utils.message import new_agent_text_message
from rich.pretty import pprint
from rich import print as cprint
import logging
import uuid
from a2a.types import (
    InternalError,
    Part,
    TextPart,
    TaskState,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from WebSearchAgent import WebsearchAgent
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
class WebSearchAgentExecutor(AgentExecutor):
    """Websearch Remote Agent Implementation."""
    def __init__(self):
        self.agent = WebsearchAgent()
    
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        # Checking if Context Exists ------------------------------------------
        pprint(context)
        if not context:
            print("no context found!")
            raise ServerError(error=InvalidRequestError())
        
        # Getting the Message (query) sent from the A2A Client ----------------
        query = context.get_user_input()
        
        task = context.current_task
        # Printing Details of incoming A2A Communication Request from Client
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
        # Invoking the Agent with the received query -----------------------------
        try:
            # For Non-Streaming Implementation:
            #----------------------------------------------------------------
            #result = self.agent.invoke(query, task.context_id)
            #is_task_complete = result['is_task_complete']
            #if is_task_complete:
            #   await updater.add_artifact(
            #               [Part(root=TextPart(text=result['content']))],
            #                name='websearch_result',)
            #   await updater.complete()
            # ---------------------------------------------------------------

            # For Streaming Implementation:
            #----------------------------------------------------------------
            async for item in self.agent.stream(query, task.context_id):
                is_task_complete = item['is_task_complete']
                cprint("[cyan1]Agent Response--------------------------------[/cyan1]")
                pprint(item)
                if not is_task_complete:
                    await updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item['content'],
                            task.context_id,
                            task.id,
                        ),
                    )
                else:
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='websearch_result',
                    )
                    await updater.complete()
                    break
        except Exception as e:
            logger.error(f'An error occurred while getting the response: {e}')
            raise
        
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        raise ServerError(error=UnsupportedOperationError())