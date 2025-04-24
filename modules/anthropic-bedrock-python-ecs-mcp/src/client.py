from typing import Optional
from contextlib import AsyncExitStack
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from mcp import ClientSession
from mcp.client.sse import sse_client

from anthropic import AnthropicBedrock
from dotenv import load_dotenv
import os

load_dotenv()
SERVER_URL = os.getenv("SERVER_URL", "http://0.0.0.0:8080")
app = FastAPI()


class Query(BaseModel):
    text: str


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = AnthropicBedrock()

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        self._streams_context = sse_client(url=f"{server_url}/sse")
        streams = await self._streams_context.__aenter__()

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()

        print("Initialized SSE client...")
        print("Listing tools...")
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        response = self.anthropic.messages.create(
            model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        tool_results = []
        final_text = []

        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                result = await self.session.call_tool(tool_name, tool_args)
                tool_results.append({"call": tool_name, "result": result})
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                if hasattr(content, "text") and content.text:
                    messages.append({"role": "assistant", "content": content.text})
                messages.append({"role": "user", "content": result.content})

                response = self.anthropic.messages.create(
                    model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                    max_tokens=1000,
                    messages=messages,
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)


# Create a global MCPClient instance
mcp_client = MCPClient()


@app.on_event("startup")
async def startup_event():
    """Initialize the MCP client when the FastAPI app starts"""
    await mcp_client.connect_to_sse_server(server_url=SERVER_URL)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up the MCP client when the FastAPI app shuts down"""
    await mcp_client.cleanup()


@app.post("/query")
async def process_query(query: Query):
    """Handle POST requests with queries"""
    try:
        response = await mcp_client.process_query(query.text)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
