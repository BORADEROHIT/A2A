# Required Imports
import logging
from typing import Any
from uuid import uuid4
import uuid
from rich.pretty import pprint
from rich import print as cprint
import httpx
from a2a.client import (
        A2ACardResolver, 
        A2AClient, 
        A2ACardResolver
    )
from a2a.utils.message import get_message_text
from a2a.types import TransportProtocol
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
)
import warnings
warnings.filterwarnings("ignore")
 
def get_user_query() -> str:
    return input('\n> ')
 
def print_initwelcome_message() -> None:
    print("\n\n")
    cprint('[bright_yellow]==================================Welcome to the A2A client!=================[/bright_yellow]')
    cprint("[bright_yellow]Simple Client Example: Understanding A2A Server Operations[/bright_yellow]")
    cprint("[bright_yellow]=============================================================================[/bright_yellow]")
 
def print_input_message() -> None:
    print("\n\n")
    cprint("[green_yellow]Please enter your query (type 'exit' to quit):[/green_yellow]")
 
async def close(self):
    """Close the HTTP client."""
    if self.httpx_client:
        await self.httpx.client.aclose()
        
async def main() -> None:
    # Configure logging to show INFO level messages
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # Get a logger instance
    # URL of the Remote Agent hosted via A2A Protocol Server 
    base_url = 'http://127.0.0.1:8024'
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0)) as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url,
        )
        
        # Fetch Public Agent Card and Initialize Client
        agent_card: AgentCard | None = None
        logger.info(
            f'Attempting to fetch public agent card from: {base_url}{AGENT_CARD_WELL_KNOWN_PATH}'
        )
        try:
            agent_card = (
                await resolver.get_agent_card()
            )  # Fetches from default public path
            logger.info('Successfully fetched public agent card')
            cprint(f"[cyan1]Agent Card:----------------------------------------------------------[/cyan1]")
            pprint(agent_card)
            cprint(f"[cyan1]---------------------------------------------------------------------[/cyan1]")
            
            
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )
        except Exception as e:
            logger.error(f'Critical error fetching public agent card: {e}', exc_info=True)
            raise RuntimeError('Failed to fetch the public agent card. Cannot continue.') from e
        client = A2AClient(httpx_client=httpx_client, 
                           agent_card=agent_card
                        )
        logger.info('A2AClient initialized.')
        print_initwelcome_message()
        context_id=uuid4().hex
        #Prepare the message request
        while True:
            print_input_message()
            user_input = get_user_query()
            if user_input.lower() == 'exit':
                cprint('[green_yellow]bye!~[/green_yellow]')
                break
            try:
                # Create the message object
                send_message_payload: dict[str, Any] = {
                    'message': {
                        'role': 'user',
                        'parts': [
                            {'kind': 'text', 'text': user_input}
                        ],
                        'messageId': uuid4().hex,
                        'context_id':context_id
                    },
                }
            
                # Send the message to the A2A server
                request = SendMessageRequest(
                    id=str(uuid4()), params=MessageSendParams(**send_message_payload)
                )
                response = await client.send_message(request)
                # Check if response has root
                if not hasattr(response, 'root') or not response.root:
                    print("Response missing 'root' attribute")
                    continue
                # Check if root is an error response
                if hasattr(response.root, "error") and response.root.error:
                    print("A2A server error:", response.root.error)
                    continue
                # Check if root has result (success response)
                if not hasattr(response.root, 'result') or not response.root.result:
                    print("Response missing 'result' attribute")
                    continue
                # Extract response data
                result = response.root.result
                cprint("[bright_green]Remote Server Response:[/bright_green]=====================")
                pprint(result)
                cprint("[bright_green]==========================================================[/bright_green]")
                
                # Get the response content from artifacts
                # Check if Result has Artifact(s)
                # When Result has multiple Artifacts
                if hasattr(result, 'artifacts') and result.artifacts:
                    # Extract content from the first artifact
                    artifact = result.artifacts[0]
                # When Result has a Single Artifact
                elif hasattr(result, 'artifact') and result.artifact:
                    # Extract content from the only artifact
                    artifact = result.artifact
                # Fallback: check for content in other locations
                elif hasattr(result, 'content') and result.content:
                    logger.info(f"Successfully retrieved response from A2A server")
                    content = result.content
                    cprint(f"Ans:[cyan1] {content}[/cyan1]\n")
                else:
                    logger.warning("No content found in A2A server response")
                    print("No response content received from A2A server")
                # When Artifact Exists then Retrieve the Text Content from the Root object of its Part
                if artifact:
                    # Checks if Artifact has Part object
                    if hasattr(artifact, 'parts') and artifact.parts:
                        part = artifact.parts[0]
                        # Checks if Part has Root object and Root has text
                        if hasattr(part, 'root') and hasattr(part.root, 'text'):
                            content = part.root.text
                            logger.info(f"Successfully retrieved response from A2A server")
                            cprint(f"Ans:[cyan1] {content}[/cyan1]\n")
            except Exception as e:
                logger.error(f"Error communicating with A2A server: {e}")
                logger.error(f"Error type: {type(e).__name__}")
                cprint(f"[bright_red]Error communicating with A2A server: {str(e)}[/bright_red]")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
 