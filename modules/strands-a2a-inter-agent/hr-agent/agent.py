import os
from uuid import uuid4

import httpx
import uvicorn
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest, Message, Role, Part, TextPart,
)
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

EMPLOYEE_AGENT_URL = os.environ.get("EMPLOYEE_AGENT_URL", "http://localhost:8001/")

app = FastAPI(title="HR Agent API")

class QuestionRequest(BaseModel):
    question: str

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/inquire")
async def ask_agent(request: QuestionRequest):
        async def generate():
            async with httpx.AsyncClient(timeout=60.0) as httpx_client:
                resolver = A2ACardResolver(httpx_client=httpx_client, base_url=EMPLOYEE_AGENT_URL)

                agent_card = await resolver.get_agent_card()

                message = MessageSendParams(
                    message=Message(
                        role=Role.user,
                        parts=[Part(TextPart(text=request.question))],
                        messageId=uuid4().hex,
                        taskId=uuid4().hex,
                    )
                )

                client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

                streaming_request = SendStreamingMessageRequest(id=str(uuid4()), params=message)

                stream_response = client.send_message_streaming(streaming_request)

                async for chunk in stream_response:
                    data = chunk.model_dump(mode='json', exclude_none=True)
                    result = data.get('result', {})
                    artifact = result.get('artifact', {})
                    parts = artifact.get('parts', [])

                    for part in parts:
                        if 'text' in part:
                            yield part['text']

        return StreamingResponse(
            generate(),
            media_type="text/plain"
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
