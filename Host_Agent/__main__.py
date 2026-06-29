# Necessary Imports and Utility Functions--------------------------------
import asyncio
import gradio as gr
from pydantic import BaseModel
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from Host_Agent import HostAgent
from collections.abc import AsyncIterator
from google.adk import Agent
from pprint import pformat
from uuid import uuid4
import traceback
from rich.pretty import pprint
from rich import print as cprint
 

class ResponseModel(BaseModel):
    role: str
    content: str
 
APP_NAME="GADK_A2A_App"
USER_ID='default_user'
SESSION_ID=uuid4().hex
 

def get_agent()->Agent:
    async def get_host_agent()->Agent:
        routing_agent_instance=await HostAgent.create()
        return routing_agent_instance.create_agent()
    try:
        return asyncio.run(get_host_agent())
    except RuntimeError as e:
        if 'asyncio.run() cannot be called from a running event loop' in str(e):
            print(f"""Warning Culd not initialise Routing agent with asyncio.run:{e}, 
            This can happen if an event loop is already running eg upyter. Consder initialising routingagent 
            within an async function on your application.""")
            raise
 

SESSION_SERVICE=InMemorySessionService()
ROUTING_AGENT_RUNNER=Runner(
    agent=get_agent(),
    app_name=APP_NAME,
    session_service=SESSION_SERVICE,
)

# For Gradio Application
async def get_response_from_agent_gr(
   message: str,
   history: list[gr.ChatMessage],
) -> AsyncIterator[gr.ChatMessage]:
   """Get response from host agent."""
   try:
       event_iterator: AsyncIterator[Event] = ROUTING_AGENT_RUNNER.run_async(
           user_id=USER_ID,
           session_id=SESSION_ID,
           new_message=types.Content(
               role='user', parts=[types.Part(text=message)]
           ),
       )
       async for event in event_iterator:
           if event.content and event.content.parts:
               for part in event.content.parts:
                   if part.function_call:
                       formatted_call = f'```python\n{pformat(part.function_call.model_dump(exclude_none=True), indent=2, width=80)}\n```'
                       yield gr.ChatMessage(
                           role='assistant',
                           content=f'🛠️ **Tool Call: {part.function_call.name}**\n{formatted_call}',
                       )
                   elif part.function_response:
                       response_content = part.function_response.response
                       if (isinstance(response_content, dict) and 'response' in response_content):
                           formatted_response_data = response_content['response']
                       else:
                           formatted_response_data = response_content
                       formatted_response = f'```json\n{pformat(formatted_response_data, indent=2, width=80)}\n```'
                       yield gr.ChatMessage(
                           role='assistant',
                           content=f'⚡ **Tool Response from {part.function_response.name}**\n{formatted_response}',
                       )
           if event.is_final_response():
               final_response_text = ''
               if event.content and event.content.parts:
                   final_response_text = ''.join(
                       [p.text for p in event.content.parts if p.text]
                   )
               elif event.actions and event.actions.escalate:
                   final_response_text = f'Agent escalated: {event.error_message or "No specific message."}'
               if final_response_text:
                   yield gr.ChatMessage(
                       role='assistant', 
                       content=final_response_text
                   )
               break
   except Exception as e:
       print(f'Error in get_response_from_agent (Type: {type(e)}): {e}')
       traceback.print_exc()
       yield gr.ChatMessage(
           role='assistant',
           content='An error occurred while processing your request. Please check the server logs for details.',
       )
 


async def get_response_from_agent(message:str)->str:
    '''Get response from host agent'''
    try:
        event_iterator:AsyncIterator[Event]=ROUTING_AGENT_RUNNER.run_async(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=types.Content(
                role='user',parts=[types.Part(text=message)]
            )
        )
        cprint(f"[bright_blue]Events: {'-'*60}[/bright_blue]")
        async for event in event_iterator:
            if event.content and event.content.parts:
                cprint("[bright_yellow]Event: Host Agent Streaming Response ================================= [/bright_yellow]")
                pprint(event.content)
                cprint("[green_yellow]Formatted UI Response---------------------------------------------------[/green_yellow]")
                for part in event.content.parts:
                    if part.function_call:
                        formatted_call =f"```python\n{pformat(part.function_call.model_dump(exclude_none=True),indent=2,width=80)}\n```"
                        response = {
                                'role':'assistant',
                                'content':f" **Tool Call: {part.function_call.name}** \n{formatted_call}"
                            }
                        response = ResponseModel(**response)
                        pprint(response)
                        cprint("[bright_yellow]======================================================================[/bright_yellow]")
                        print()
                    elif part.function_response:
                        response_content=part.function_response.response
                        if (isinstance(response_content,dict)and 'response' in response_content):
                            formatted_response_data=response_content['response']
                        else:
                            formatted_response_data=response_content
                        formatted_response=f"```json\n{pformat(formatted_response_data,indent=2,width=80)}n```"
                        response = {
                                'role':'assistant',
                                'content':f" **Tool Response from {part.function_response.name}**\n{formatted_response}"
                            }
                        response = ResponseModel(**response)
                        pprint(response)
                        cprint("[bright_yellow]======================================================================[/bright_yellow]")
                        print()
            if event.is_final_response():
                final_response_text=''
                if event.content and event.content.parts:
                    final_response_text=''.join([p.text for p in event.content.parts if p.text])
                elif event.actions and event.actions.escalate:
                    final_response_text=f"Agent escalated: {event.error_message or 'No specific message'}"
                if final_response_text:
                    response = {
                            "role":'assistant', "content":final_response_text
                        }
                    response = ResponseModel(**response)
                    pprint(response)
                    cprint("[bright_yellow]======================================================================[/bright_yellow]")
                    print()
                    return final_response_text
                break
    except Exception as e:
        cprint(f"[bright_red]Error in get_response_from_agent (Type: {type(e)}): {e}[/bright_red]")
        print()
        return "An error occured while processing your request. Please check the server logs for details"


# UI Loop:--------------------------------
async def main():
    '''Main Host Agent App.'''
    print("Creating ADK Session...")
    await SESSION_SERVICE.create_session(
        app_name=APP_NAME,user_id=USER_ID,session_id=SESSION_ID
    )
    print("ADK session created successfully")
    while True:
        print("\n\n")
        cprint("[green_yellow]Please enter your query[/green_yellow]")
        user_input=input()
        if user_input.lower()=="exit":
            cprint('[green_yellow]bye-~[/green_yellow]')
            break
        else:
            response = await get_response_from_agent(user_input)
            cprint(f"AI:[cyan1] {response}[/cyan1]\n")




# GUI using Gradio
async def run():
    """Main gradio app."""
    print('Creating ADK session...')
    await SESSION_SERVICE.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print('ADK session created successfully.')
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
            get_response_from_agent_gr,
            title='A2A Host Agent',
            description='This assistant can help you with answers on any topic',
        )
    print('Launching Gradio interface...')
    demo.queue().launch(
        theme=gr.themes.Ocean(),
        allowed_paths=["."],
        server_name='127.0.0.1',
        server_port=8083,
    )
    print('Gradio application has been shut down.')


if __name__=="__main__":
    asyncio.run(main())
    #asyncio.run(run())