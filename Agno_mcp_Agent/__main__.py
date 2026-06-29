# Necessary Imports ------------------------------------------
import sys, httpx, click, logging, uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
import uuid
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from agent_executor import MCPAgentExecutor
from mcp_agent import McpAgent
from dotenv import load_dotenv
load_dotenv()

 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

 

# A2A Server Implementation ==================================================================
@click.command()
@click.option('--host', 'host', default='127.0.0.1')
@click.option('--port', 'port', default=8048)
def main(host, port):
    try:
        # Defining Agent Skills, capabilities and Agent Card ------------------------------
        
        ## Defining the Agent Capabilitties
        capabilities = AgentCapabilities(streaming=False, push_notifications=False)
        ## Defining the Agent Skills
        movie_search_skill = AgentSkill(
            id='movie_search',
            name='Movie Search',
            description="""Perform search on Movie database to retrieve related information.
Search movies by genre, year and rating. 
All search criterion or filters are optional.""",
            tags=['Movie Information', 'Search by Genre', 'Search by Year of Release', 'Search by Rating'],
            examples=['Suggest some good comedy movies released in 2016?',
                    'which are the action movies rated above 7?'],
        )
        product_search_skill = AgentSkill(
            id='product_search',
            name='Stock Product Search',
            description="""Perform search Stock Product databases to retrieve related information
Search Products in Stock based on Product Type, Brand, and/or minimum quantity in stock of the product.
All search criterion or filters are optional.""",
            tags=['Product Information', 'Search by Brand Name', 'Search by Product Type', 'Search by Minimum Quantity in Stock'],
            examples=['Suggest some Home Goods products?',
                    'Which Electronics products have stock greater than 100?'],
        )
        ## Defining the Agent Card with Skills and Capabilitties---------------------------
        agent_card = AgentCard(
            name='Movie and Stock Product Information Agent',
            description='Helps with searching and retrieving information from internal movie and stock database to answer user queries on movies and products in stock',
            url=f'http://{host}:{port}/',
            version='1.0.0',
            default_input_modes=McpAgent.SUPPORTED_CONTENT_TYPES,
            default_output_modes=McpAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[movie_search_skill, product_search_skill],
        )
        ##----------------------------------------------------------------------------------
        
        ## Creating Push Notification Capability--------------------------------------------
        httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        push_config_store = InMemoryPushNotificationConfigStore()
        push_sender = BasePushNotificationSender(httpx_client=httpx_client,
                        config_store=push_config_store)
            
        # Creating the A2A Request Handler-------------------------------------------------
        request_handler = DefaultRequestHandler(
        agent_executor=MCPAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_config_store=push_config_store,
        push_sender= push_sender
        )
            
        # Creating the A2A Starlette Application with the Agent Card and Request Handler---
        server = A2AStarletteApplication(
            agent_card=agent_card,
            http_handler=request_handler
        )
        # Running the Uvicorn Server ------------------------------------------------------
        uvicorn.run(server.build(), host=host, port=port)
       
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)
 
if __name__ == '__main__':
    main()