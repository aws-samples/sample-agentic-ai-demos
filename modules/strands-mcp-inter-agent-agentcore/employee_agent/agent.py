import os
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.fastmcp import FastMCP
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel
import httpx

PORT = int(os.environ.get('PORT', 8001))

REGION=os.environ.get("AWS_REGION", "us-east-1")

EMPLOYEE_INFO_ARN=os.environ.get("EMPLOYEE_INFO_ARN", None)
COGNITO_CLIENT_ID=os.environ.get("COGNITO_CLIENT_ID", None)
COGNITO_CLIENT_SECRET=os.environ.get("COGNITO_CLIENT_SECRET", None)
OAUTH_ENDPOINT=os.environ.get("OAUTH_ENDPOINT", None)

def employee_mcp_client_factory():
    if EMPLOYEE_INFO_ARN is None or COGNITO_CLIENT_ID is None or COGNITO_CLIENT_SECRET is None or OAUTH_ENDPOINT is None:
        return MCPClient(lambda: streamablehttp_client("http://localhost:8002/mcp/"))
    else:
        data = {
            "grant_type": "client_credentials"
        }
        resp = httpx.post(
            OAUTH_ENDPOINT,
            auth=httpx.BasicAuth(COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET),
            data=data,
        )
        resp.raise_for_status()
        payload = resp.json()
        access_token = payload["access_token"]
        headers = {"authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        employee_info_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{EMPLOYEE_INFO_ARN.replace(':', '%3A').replace('/', '%2F')}/invocations?qualifier=DEFAULT"
        return MCPClient(lambda: streamablehttp_client(employee_info_url, headers))

bedrock_model = BedrockModel(
    model_id="amazon.nova-micro-v1:0",
    region_name=REGION,
)

mcp = FastMCP("employee-agent", stateless_http=True, host="0.0.0.0", port=PORT)

@mcp.tool()
def inquire(question: str) -> list[str]:
    """answers questions related to our employees"""

    with employee_mcp_client_factory() as employee_mcp_client:
        tools = employee_mcp_client.list_tools_sync()
        agent = Agent(model=bedrock_model, tools=tools, system_prompt="you must abbreviate employee first names and list all their skills") #, callback_handler=None)

        return [
            content["text"]
            for content in agent(question).message["content"]
            if "text" in content
        ]

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
