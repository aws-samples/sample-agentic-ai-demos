import os
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel

EMPLOYEE_INFO_URL = os.environ.get("EMPLOYEE_INFO_URL", "http://localhost:8002/mcp/")
employee_mcp_client = MCPClient(lambda: streamablehttp_client(EMPLOYEE_INFO_URL))

bedrock_model = BedrockModel(
    model_id="amazon.nova-micro-v1:0",
    region_name="us-east-1",
    temperature=0.9,
)

mcp = FastMCP("employee-agent", stateless_http=True, host="0.0.0.0", port=8001)

@mcp.tool()
def inquire(question: str) -> list[str]:
    """answers questions related to our employees"""

    with employee_mcp_client:
        tools = employee_mcp_client.list_tools_sync()
        agent = Agent(model=bedrock_model, tools=tools, system_prompt="you must abbreviate employee first names and list all their skills") #, callback_handler=None)

        return [
            content["text"]
            for content in agent(question).message["content"]
            if "text" in content
        ]

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
