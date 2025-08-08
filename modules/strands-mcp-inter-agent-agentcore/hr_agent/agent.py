import os
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import httpx

REGION=os.environ.get("AWS_REGION", "us-east-1")

EMPLOYEE_AGENT_ARN=os.environ.get("EMPLOYEE_AGENT_ARN", None)
COGNITO_CLIENT_ID=os.environ.get("COGNITO_CLIENT_ID", None)
COGNITO_CLIENT_SECRET=os.environ.get("COGNITO_CLIENT_SECRET", None)
OAUTH_ENDPOINT=os.environ.get("OAUTH_ENDPOINT", None)

def employee_mcp_client_factory():
    if EMPLOYEE_AGENT_ARN is None or COGNITO_CLIENT_ID is None or COGNITO_CLIENT_SECRET is None or OAUTH_ENDPOINT is None:
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
        employee_agent_url = f"https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{EMPLOYEE_AGENT_ARN.replace(':', '%3A').replace('/', '%2F')}/invocations?qualifier=DEFAULT"
        return MCPClient(lambda: streamablehttp_client(employee_agent_url, headers))

bedrock_model = BedrockModel(
    model_id="amazon.nova-micro-v1:0",
    region_name=REGION,
)

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    """HR Agent"""
    with employee_mcp_client_factory() as employee_mcp_client:
        tools = employee_mcp_client.list_tools_sync()
        agent = Agent(model=bedrock_model, tools=tools) #, callback_handler=None)
        user_message = payload.get("question")
        result = agent(user_message)
        return {"result": result.message}

if __name__ == "__main__":
    PORT=int(os.environ.get("PORT", "8000"))
    app.run(port=PORT)
