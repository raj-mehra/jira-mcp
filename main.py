import anyio
import click
import httpx
import mcp.types as types
from mcp.server.lowlevel import Server
import os
from dotenv import load_dotenv
from jira import JIRA
import json
import sys

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

def get_jira_client() -> JIRA:
    """Create and return a JIRA client instance."""
    return JIRA(
        server=JIRA_URL,
        basic_auth=(JIRA_USERNAME, JIRA_API_TOKEN)
    )

async def fetch_ticket_details(
    ticket_key: str,
    include_comments: bool = False,
    include_attachments: bool = False,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Fetch data from Jira ticket."""
    try:
        jira_client = get_jira_client()
        issue = jira_client.issue(ticket_key)
        
        # Basic ticket information
        ticket_data = {
            "key": issue.key,
            "summary": issue.fields.summary,
            "description": issue.fields.description,
            "status": issue.fields.status.name,
            "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
            "reporter": issue.fields.reporter.displayName if issue.fields.reporter else None,
            "created": issue.fields.created,
            "updated": issue.fields.updated,
            "priority": issue.fields.priority.name if issue.fields.priority else None,
            "labels": issue.fields.labels,
            "components": [comp.name for comp in issue.fields.components],
            "custom_fields": {}
        }
        
        # Add custom fields
        for field_name, field_value in issue.raw['fields'].items():
            if field_name.startswith('customfield_'):
                ticket_data['custom_fields'][field_name] = field_value
        
        # Include comments if requested
        if include_comments:
            comments = []
            for comment in issue.fields.comment.comments:
                comments.append({
                    "author": comment.author.displayName,
                    "body": comment.body,
                    "created": comment.created
                })
            ticket_data["comments"] = comments
        
        # Include attachments if requested
        if include_attachments:
            attachments = []
            for attachment in issue.fields.attachment:
                attachments.append({
                    "filename": attachment.filename,
                    "size": attachment.size,
                    "mimeType": attachment.mimeType,
                    "content": attachment.content
                })
            ticket_data["attachments"] = attachments
        
        return [types.TextContent(type="text", text=json.dumps(ticket_data, indent=2))]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error: Failed to fetch Jira ticket data: {str(e)}"
        )]

async def search_tickets(
    jql: str,
    max_results: int = 50
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Search for Jira tickets using JQL."""
    try:
        jira_client = get_jira_client()
        issues = jira_client.search_issues(jql, maxResults=max_results)
        
        results = []
        for issue in issues:
            results.append({
                "key": issue.key,
                "summary": issue.fields.summary,
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else None,
                "priority": issue.fields.priority.name if issue.fields.priority else None
            })
        
        return [types.TextContent(type="text", text=json.dumps(results, indent=2))]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error: Failed to search Jira tickets: {str(e)}"
        )]

@click.command()
@click.option("--port", default=8000, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(port: int, transport: str) -> int:
    app = Server("jira-mcp-server")

    @app.call_tool()
    async def fetch_tool( # type: ignore[unused-function]
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if name == "fetch_ticket":
            if "ticketKey" not in arguments:
                return [types.TextContent(
                    type="text",
                    text="Error: Missing required argument 'ticketKey'"
                )]
            return await fetch_ticket_details(
                arguments["ticketKey"],
                True,
                True
            )
        elif name == "search_tickets":
            if "jql" not in arguments:
                return [types.TextContent(
                    type="text",
                    text="Error: Missing required argument 'jql'"
                )]
            return await search_tickets(
                arguments["jql"],
                arguments.get("maxResults", 50)
            )
        else:
            return [types.TextContent(
                type="text",
                text=f"Error: Unknown tool: {name}"
            )]

    @app.list_tools()
    async def list_tools() -> list[types.Tool]: # type: ignore[unused-function]
        return [
            types.Tool(
                name="fetch_ticket",
                description="Fetches detailed information about a Jira ticket, including basic fields, custom fields, and optionally comments and attachments.",
                inputSchema={
                    "type": "object",
                    "required": ["ticketKey"],
                    "properties": {
                        "ticketKey": {
                            "type": "string",
                            "description": "Jira ticket key (e.g., PROJ-123)",
                        }
                    },
                },
            ),
            types.Tool(
                name="search_tickets",
                description="Search for Jira tickets using JQL (Jira Query Language)",
                inputSchema={
                    "type": "object",
                    "required": ["jql"],
                    "properties": {
                        "jql": {
                            "type": "string",
                            "description": "JQL query string",
                        },
                        "maxResults": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 50
                        }
                    },
                },
            )
        ]

    if transport == "sse":
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route

        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
        )

        import uvicorn

        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            async with stdio_server() as streams:
                await app.run(
                    streams[0], streams[1], app.create_initialization_options()
                )

        anyio.run(arun)

    return 0

if __name__ == "__main__":
    main() 