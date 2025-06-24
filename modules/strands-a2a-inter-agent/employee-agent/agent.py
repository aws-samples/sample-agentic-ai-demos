import os

import httpx
import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import (AgentCapabilities, AgentCard, AgentSkill, TaskArtifactUpdateEvent, TaskStatusUpdateEvent,
                       TaskStatus, TaskState)
from a2a.utils import new_text_artifact
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp.mcp_client import MCPClient

EMPLOYEE_INFO_URL = os.environ.get("EMPLOYEE_INFO_URL", "http://localhost:8002/mcp/")
employee_mcp_client = MCPClient(lambda: streamablehttp_client(EMPLOYEE_INFO_URL))

bedrock_model = BedrockModel(
    model_id="amazon.nova-micro-v1:0",
    region_name="us-east-1",
    temperature=0.5,
)

skill = AgentSkill(
    id="employee-agent",
    name="Employee Agent",
    description="Answers questions about employees",
    tags=["employees"],
)

agent_card = AgentCard(
    name="Employee Agent",
    description="Answers questions about employees",
    url=f"http://localhost:8001/",
    version="0.0.1",
    defaultInputModes=["text", "text/plain"],
    defaultOutputModes=["text", "text/plain"],
    capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
    skills=[skill],
)

class EmployeeAgentExecutor(AgentExecutor):
    def __init__(self):
        with employee_mcp_client:
            tools = employee_mcp_client.list_tools_sync()
            self.agent = Agent(model=bedrock_model, tools=tools, system_prompt="you must abbreviate employee first names and list all their skills") #, callback_handler=None)

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        with employee_mcp_client:
            query = context.get_user_input()
            agent_stream = self.agent.stream_async(query)

            async for event in agent_stream:
                if "data" in event:
                    message = TaskArtifactUpdateEvent(
                        contextId=context.context_id,
                        taskId=context.task_id,
                        artifact=new_text_artifact(
                            name='current_result',
                            text=event["data"],
                        ),
                    )
                    await event_queue.enqueue_event(message)

                if "contentBlockStop" in event:
                    message = TaskStatusUpdateEvent(
                        status=TaskStatus(state=TaskState.completed),
                        final=True,
                        contextId=context.context_id,
                        taskId=context.task_id,
                    )
                    await event_queue.enqueue_event(message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")

timeout = httpx.Timeout(60.0, read=60.0, write=60.0, connect=10.0)

httpx_client = httpx.AsyncClient(timeout=timeout)

request_handler = DefaultRequestHandler(
    agent_executor=EmployeeAgentExecutor(),
    task_store=InMemoryTaskStore(),
    push_notifier=InMemoryPushNotifier(httpx_client),
)

server = A2AStarletteApplication(
    agent_card=agent_card, http_handler=request_handler
)

if __name__ == "__main__":
    uvicorn.run(server.build(), port=8001)
