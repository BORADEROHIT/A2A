# Necessary Imports ------------------------------------------
from mcp.server.fastmcp import FastMCP
from typing import Annotated
import pandas as pd
import numpy as np
from rich import print as cprint
# For Recent releases of MCP Python SDK use:
# from mcp.server.mcpserver import MCPServer
# Create an MCP server
## - Use 'MCPServer(...)' instead of FastMCP(...) for recent MCP-Python-SDK versions
 
mcp = FastMCP("mcp_tool_server",  
              port=8111, 
              stateless_http=False, 
              streamable_http_path="/mcptoolserver", 
              host="127.0.0.1", 
              warn_on_duplicate_tools=True)
 
# Adding tools
@mcp.tool("search_movie")
def search_movie(genre: Annotated[str, "genre of the movie"] | None = None,
                        year: Annotated[int, "year of release of the movie"] | None = None,
                        rating: Annotated[float, "minimum rating of the movie"] | None = None ) -> list[dict]:
    """Search movies by genre, year and rating.
    Arguments:
        genre (str, optional): The genre of the movie to filter by. Defaults to None.
        year (integer, optional): The year of release of the movie to filter by. Defaults to None.
        rating (float, optional): The minimum rating of the movie to filter by. Defaults to None. Any number between 0.0 to 10.0, e.g., 4.5, 7.5, 8.6 etc. 
    """

 

    dataframe = pd.read_csv("mcp_server/csvs/movies.csv")
    query_conditions = pd.Series([True] * len(dataframe)) # Start with all True
    if genre:
        query_conditions = query_conditions & (dataframe['Genre'].str.lower().str.contains(genre.lower(),case=False))
    if year:
        query_conditions = query_conditions & (dataframe['Year'] == int(year))
    if rating:
        query_conditions = query_conditions & (dataframe['Rating'] >= float(rating))    
    result = dataframe[query_conditions].to_dict(orient='records')
    cprint("[cyan1]MCP Tool: search_movie called with:[/cyan1]", f"[green_yellow]Genre: {genre}, Year: {year}, Rating: {rating}[/green_yellow]")
    cprint("[cyan1]Rows returned:[/cyan1]", f"[green_yellow]{len(result)}[/green_yellow]")
    return result

 

@mcp.tool(name="search_stock")
def search_stock(product_type: Annotated[str, "type of the product"] | None = None,
                      brand_name: Annotated[str, "brand name of the product"] | None = None,
                        min_quantity: Annotated[str | int, "minimum quantity of the product in stock"] | None = None) -> list[dict]:
    """Search Products in Stock based on Product Type, Brand, and/or minimum quantity in stock of the product.
    Arguments:
        product_type (str, optional): Type of the product, domain or product class.
        brand_name (str, optional): Brand name or Manufacturer of the product.
        min_quantity (float, optional): Minimum quantity of the product in stock. 
    """
    dataframe = pd.read_csv("mcp_server/csvs/productdb.csv")
    query_conditions = pd.Series([True] * len(dataframe)) # Start with all True

 

    if product_type:
        query_conditions = query_conditions & (dataframe['Product_Type'].str.lower().str.contains(product_type.lower()))
    if brand_name:
        query_conditions = query_conditions & (dataframe['Brand'].str.lower().str.contains(brand_name.lower()))
    if min_quantity:
        try:
            query_conditions = query_conditions & (dataframe['Quantity_in_Stock']>= int(min_quantity))
        except Exception:
            pass
            
    result = dataframe[query_conditions].to_dict(orient='records')
    cprint("[cyan1]MCP Tool 'search_stock' called with:[/cyan1]", f"[green_yellow]Product Type: {product_type}, Brand Name: {brand_name}, Minimum Quantity: {min_quantity}[/green_yellow]")
    cprint("[cyan1]Rows returned:[/cyan1]", f"[green_yellow]{len(result)}[/green_yellow]")
    return result
 
# Run the MCP Server:
def main():
    """Entry point for the direct execution server."""
    mcp.run(transport="streamable-http")
 
if __name__ == "__main__":
    main()