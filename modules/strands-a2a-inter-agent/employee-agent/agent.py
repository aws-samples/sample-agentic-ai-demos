import os

from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient
from strands.multiagent.a2a import A2AServer
from urllib.parse import urlparse


EMPLOYEE_INFO_URL = os.environ.get("EMPLOYEE_INFO_URL", "http://localhost:8002/mcp/")
EMPLOYEE_AGENT_URL = os.environ.get("EMPLOYEE_AGENT_URL", "http://localhost:8001/")

employee_mcp_client = MCPClient(lambda: streamablehttp_client(EMPLOYEE_INFO_URL))

bedrock_model = BedrockModel(
    model_id="amazon.nova-pro-v1:0",
    region_name="us-east-1",
)

with employee_mcp_client:
    tools = employee_mcp_client.list_tools_sync()

    employee_agent = Agent(
        model=bedrock_model,
        name="Employee Agent",
        description="Answers questions about employees",
        tools=tools,
        system_prompt="when listing employees, abbreviate employee first names and list all their skills"
    )

    a2a_server = A2AServer(agent=employee_agent, host=urlparse(EMPLOYEE_AGENT_URL).hostname, port=urlparse(EMPLOYEE_AGENT_URL).port)

    if __name__ == "__main__":
        a2a_server.serve(host="0.0.0.0", port=8001)
