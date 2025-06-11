import os
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from strands.models import BedrockModel
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

EMPLOYEE_AGENT_URL = os.environ.get("EMPLOYEE_AGENT_URL", "http://localhost:8001/mcp/")
hr_mcp_client = MCPClient(lambda: streamablehttp_client(EMPLOYEE_AGENT_URL))

bedrock_model = BedrockModel(
    model_id="amazon.nova-micro-v1:0",
    region_name="us-east-1",
    temperature=0.9,
)

app = FastAPI(title="HR Agent API")

class QuestionRequest(BaseModel):
    question: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/inquire")
async def ask_agent(request: QuestionRequest):
    # with hr_mcp_client:
    #     tools = hr_mcp_client.list_tools_sync()
    #
    #     agent = Agent(model=bedrock_model, tools=tools, callback_handler=None)
    #
    #     return [
    #         content["text"]
    #         for content in agent(request.question).message["content"]
    #         if "text" in content
    #     ]

    async def generate():
        with hr_mcp_client:
            tools = hr_mcp_client.list_tools_sync()
            agent = Agent(model=bedrock_model, tools=tools) #, callback_handler=None)
            async for event in agent.stream_async(request.question):
                if "data" in event:
                    yield event["data"]

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
