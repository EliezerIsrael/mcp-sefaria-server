from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import asyncio
import os
import logging
import sys
import json
from .sefaria_handler import * 

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('sefaria_jewish_library.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('sefaria_jewish_library')

SEFARIA_API_URL = "https://sefaria.org"


server = Server("sefaria_jewish_library")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    logger.debug("Handling list_tools request")
    return [
        types.Tool(
            name="get_text",
            description="get a jewish text from the jewish library",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "The reference of the jewish text, e.g. 'שולחן ערוך אורח חיים סימן א' or 'Genesis 1:1'.  Complex references can be debugged using the get_name endpoint.",
                    },
                    "version_language": {
                        "type": "string",
                        "description": "Language version to retrieve. Options: 'source' (original language), 'english', 'both' (both source and English), or leave empty for all available versions",
                        "enum": ["source", "english", "both"]
                    },
                },
                "required": ["reference"],
            },
        ),
        types.Tool(
            name="get_situational_info",
            description="get current Jewish calendar information, including Hebrew date, Parshat Hashavua, Daf Yomi, and other learning schedules",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        types.Tool(
            name="get_links",
            description="get a list of links (connections) for a jewish text reference, including commentaries, earlier sources, parallels, and reference material",
            inputSchema={
                "type": "object",
                "properties": {
                    "reference": {
                        "type": "string",
                        "description": "The reference of the jewish text, e.g. 'שולחן ערוך אורח חיים סימן א' or 'Genesis 1:1'.  Complex references can be debugged using the get_name endpoint.",
                    },
                    "with_text": {
                        "type": "string",
                        "description": "Include the text content of linked resources. Default is '0' (exclude text). Individual texts can be loaded using the texts endpoint.",
                        "enum": ["0", "1"],
                        "default": "0"
                    },
                },
                "required": ["reference"],
            },
        ),
        types.Tool(
            name="search_texts",
            description="search for jewish texts in the Sefaria library",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "filters": {
                        "type": ["string", "array"],
                        "description": "Filters can be a string of one filter, or an array of many strings. They must be complete paths to Sefaria categories or texts. For any search result, this is the concatenation of the categories of the text, joined with \"/\" (e.g. \"Tanakh\", \"Mishnah\", \"Talmud\", \"Midrash\", \"Halakhah\", \"Kabbalah\", \"Liturgy\", \"Jewish Thought\", \"Tosefta\", \"Chasidut\", \"Musar\", \"Responsa\", \"Reference\", \"Second Temple\", \"Talmud Commentary\", \"Tanakh Commentary\", \"Mishnah Commentary\", \"Tanakh/Torah\", \"Talmud/Yerushalmi\", \"Talmud/Bavli\", \"Reference/Dictionary/BDB\", \"Talmud Commentary/Rishonim on Talmud/Rashi\")",
                        "items": {
                            "type": "string"
                        }
                    },
                    "size": {
                        "type": "integer",
                        "description": "Number of results to return.",
                        "default": 10
                    }
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="search_dictionaries",
            description="search Sefaria dictionaries for terms and definitions",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for dictionary entries",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_name",
            description="get name validation and autocomplete information for a text name, reference, topic, or other Sefaria object",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The text string to match against Sefaria's data collections",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (0 indicates no limit)",
                    },
                    "type_filter": {
                        "type": "string",
                        "description": "Filter results to a specific type (ref, Collection, Topic, TocCategory, Term, User)",
                        "enum": ["ref", "Collection", "Topic", "TocCategory", "Term", "User"],
                    },
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="get_shape",
            description="get the structure (shape) of a text or list texts in a category/corpus",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Either a text name (e.g., 'Genesis') or a category/corpus name (e.g., 'Tanakh', 'Mishnah', 'Talmud', 'Midrash', 'Halakhah', 'Kabbalah', 'Liturgy', 'Jewish Thought', 'Tosefta', 'Chasidut', 'Musar', 'Responsa', 'Reference', 'Second Temple', 'Yerushalmi', 'Midrash Rabbah', 'Bavli').  Text names can be debugged with the get_name endpoint, or listed within their respective categories",
                    },
                },
                "required": ["name"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can search the Jewish library and return formatted results.
    """
    logger.debug(f"Handling call_tool request for {name} with arguments {arguments}")
    
    try:
        if name == "get_text":
            try:
                reference = arguments.get("reference")
                if not reference:
                    raise ValueError("Missing reference parameter")  
                
                version_language = arguments.get("version_language")
                
                logger.debug(f"handle_get_text: {reference}, version_language: {version_language}")
                text = await get_text(reference, version_language)
                
                return [types.TextContent(
                    type="text",
                    text=text
                )]
            except Exception as err:
                logger.error(f"retrieve text error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
                
              
        
        elif name == "get_links":
            try:
                reference = arguments.get("reference")
                if not reference:
                    raise ValueError("Missing reference parameter")
                
                with_text = arguments.get("with_text", "0")
                
                logger.debug(f"handle_get_links: {reference}, with_text: {with_text}")
                links = await get_links(reference, with_text)
                
                return [types.TextContent(
                    type="text",
                    text=links
                )]
            except Exception as err:
                logger.error(f"retrieve links error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
        
        elif name == "search_texts":
            try:
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")
                    
                filters = arguments.get("filters")
                if not filters:
                    filters = None
                size = arguments.get("size")
                if not size:
                    size = 10
                
                logger.debug(f"handle_search_texts: {query}, filters: {filters}, size: {size}")
                results = await search_texts(query, filters, size)
                
                # Convert results to JSON string if it's a list of dictionaries
                if isinstance(results, list):
                    formatted_results = json.dumps(results, indent=2)
                else:
                    formatted_results = results
                
                return [types.TextContent(
                    type="text",
                    text=formatted_results
                )]
            except Exception as err:
                logger.error(f"search texts error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
                
        elif name == "get_name":
            try:
                name_param = arguments.get("name")
                if not name_param:
                    raise ValueError("Missing name parameter")
                    
                limit = arguments.get("limit")
                type_filter = arguments.get("type_filter")
                
                logger.debug(f"handle_get_name: {name_param}, limit: {limit}, type: {type_filter}")
                results = await get_name(name_param, limit, type_filter)
                
                return [types.TextContent(
                    type="text",
                    text=results
                )]
            except Exception as err:
                logger.error(f"name info error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
                
        elif name == "get_shape":
            try:
                name_param = arguments.get("name")
                if not name_param:
                    raise ValueError("Missing name parameter")
                
                logger.debug(f"handle_get_shape: {name_param}")
                results = await get_shape(name_param)
                
                return [types.TextContent(
                    type="text",
                    text=results
                )]
            except Exception as err:
                logger.error(f"shape info error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
                
        elif name == "get_situational_info":
            try:
                logger.debug("handle_get_situational_info")
                results = await get_situational_info()
                
                return [types.TextContent(
                    type="text",
                    text=results
                )]
            except Exception as err:
                logger.error(f"situational info error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
                
        elif name == "search_dictionaries":
            try:
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")
                
                logger.debug(f"handle_search_dictionaries: {query}")
                results = await search_dictionaries(query)
                
                # Convert results to JSON string
                formatted_results = json.dumps(results, indent=2)
                
                return [types.TextContent(
                    type="text",
                    text=formatted_results
                )]
            except Exception as err:
                logger.error(f"dictionary search error: {err}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(err)}"
                )]
           
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]
    
async def main():
    try:
        logger.info("Starting Jewish Library MCP server...")
            
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="sefaria_jewish_library",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
