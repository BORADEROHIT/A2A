# Necessary Imports and Configurations--------------------------------
import asyncio
import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from Host_Agent import HostAgent
from langgraph.graph.state import CompiledStateGraph
from collections.abc import AsyncIterator
from pprint import pformat
from uuid import uuid4
import traceback
from rich.pretty import pprint
from rich import print as cprint
 
APP_NAME="LANGRAPH_A2A_App"
USER_ID='default_user'
SESSION_ID=uuid4().hex
 
class HostAgentExecutor:
    def __init__(
            self, 
            agent: CompiledStateGraph, 
            session_id: str, 
            app_name: str, 
            user_id:str
    ):
        self.agent = agent
        self.session_id = session_id
        self.app_name = app_name
        self.user_id = user_id
    
    async def stream(
            self, 
            query,
    ) -> str:
        inputs = {'messages': [HumanMessage(content=query)],'status':'submitted'}
        config = {'configurable': {'thread_id': self.session_id, 'user_id':self.user_id}}
        try:
            cprint(f"[bright_blue]Events: {'-'*50}[/bright_blue]")
            async for event in self.agent.astream(inputs,config=config,stream_mode='values'):
                cprint("[bright_yellow]Event Content: [/bright_yellow]",end="")
                event=event['messages'][-1]
                pprint(event)
                cprint("[bright_yellow]------------------------------------------------------------------[/bright_yellow]")
                if isinstance(event, AIMessage):
                    if hasattr(event,'tool_calls') and event.tool_calls:
                        formatted_call = f'```python\n{pformat(event.tool_calls[-1], indent=2, width=80)}\n```'
                        pprint(
                            {
                                'role':'assistant',
                                'content':f" **Tool Call: {event.tool_calls[-1]['name']}** \n{formatted_call}"
                            }
                        )
                    else:
                        final_response_text = ''
                        if hasattr(event,'content') and event.content:
                            final_response_text = event.content
                        if final_response_text:
                            pprint(
                                {
                                    "role":'assistant', "content":final_response_text
                                }
                            )
                            return final_response_text
                elif isinstance(event, ToolMessage):
                    if (hasattr(event, 'artifact') and event.artifact):
                        formatted_response_data = event.artifact
                    else:
                        formatted_response_data = event.content
                    formatted_response = f'```json\n{pformat(formatted_response_data, indent=2, width=80)}\n```'
                    pprint(
                        {
                            'role':'assistant',
                            'content':f" **Tool Response from {event.name}**\n{formatted_response}"
                        }
                    )
        except Exception as e:
            cprint(f"[bright_red]Error in get_response_from_agent (Type: {type(e)}): {e}[/bright_red]")
            return "An error occured while processing your request. Please check the server logs for details"

 
    #--- For Gradio Application
    async def stream_gr(
            self, 
            query: str,
            history: list[gr.ChatMessage],
    ) -> AsyncIterator[gr.ChatMessage]:
        inputs = {'messages': [HumanMessage(content=query)],'status':'submitted'}
        config = {'configurable': {'thread_id': self.session_id, 'user_id':self.user_id}}
        try:
            async for event in self.agent.astream(inputs,config=config,stream_mode='values'):
                event=event['messages'][-1]
                cprint("[bright_yellow]Event Content: [/bright_yellow]",end="")
                pprint(event)
                cprint("[bright_yellow]------------------------------------------------------------------[/bright_yellow]")
                if isinstance(event, AIMessage):
                    if hasattr(event,'tool_calls') and event.tool_calls:
                        formatted_call = f'```python\n{pformat(event.tool_calls[-1], indent=2, width=80)}\n```'
                        yield gr.ChatMessage(
                            role='assistant',
                            content=f" **Tool Call: {event.tool_calls[-1]['name']}** \n{formatted_call}"
                        )
                    else:
                        final_response_text = ''
                        if hasattr(event,'content') and event.content:
                            final_response_text = event.content
                        if final_response_text:
                            yield gr.ChatMessage(
                                role='assistant', 
                                content=final_response_text
                            )
                        break
                elif isinstance(event, ToolMessage):
                    if (hasattr(event, 'artifact') and event.artifact):
                        formatted_response_data = event.artifact
                    else:
                        formatted_response_data = event.content
                    formatted_response = f'```json\n{pformat(formatted_response_data, indent=2, width=80)}\n```'
                    yield gr.ChatMessage(
                        role='assistant',
                        content=f" **Tool Response from {event.name}**\n{formatted_response}"
                    )
        except Exception as e:
            print(f'Error in get_response_from_agent (Type: {type(e)}): {e}')
            traceback.print_exc()
            yield gr.ChatMessage(
                role='assistant',
                content='An error occurred while processing your request. Please check the server logs for details.',
            )


async def run():
    """Main Host Agent App."""
    routing_agent_instance=await HostAgent.create()
    agent = routing_agent_instance.create_agent()
    hostAgent = HostAgentExecutor(agent, SESSION_ID, APP_NAME, USER_ID)

async def main():
    """Main Host Agent App."""
    routing_agent_instance=await HostAgent.create()
    agent = routing_agent_instance.create_agent()
    hostAgent = HostAgentExecutor(agent,SESSION_ID,APP_NAME,USER_ID)
    with gr.Blocks(
       title='A2A Host Agent'
   ) as demo:
       gr.Image('./host_agent/images/a2alogo.png',
           width=100,
           height=100,
           scale=0,
           show_label=False,
           container=False,
       )
       gr.ChatInterface(
           hostAgent.stream_gr,
           title='A2A Host Agent',
           description='This assistant can help you with answers on any topic',
       )
    print('Launching Gradio interface...')
    demo.queue().launch(
        theme=gr.themes.Citrus(),
        allowed_paths=["."],
        server_name='127.0.0.1',
        server_port=8084,
    )
    print('Gradio application has been shut down.')

    while True:
        print("\n\n")
        cprint("[green_yellow]Please enter your query[/green_yellow]")
        user_input=input()
        if user_input.lower()=="exit":
            cprint('[green_yellow]bye-~[/green_yellow]')
            break
        else:
            response = await hostAgent.stream(user_input)
            cprint(f"AI:[cyan1] {response}[/cyan1]\n")
 
if __name__=="__main__":
    asyncio.run(main())
 