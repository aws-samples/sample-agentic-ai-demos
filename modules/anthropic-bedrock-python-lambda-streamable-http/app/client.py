from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage, JSONRPCRequest
import asyncio
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import json
import httpx
from anthropic import AnthropicBedrock
from dotenv import load_dotenv
import os

load_dotenv()

FUNCTION_URL = os.getenv('FUNCTION_URL')

class LambdaMCPClient:
    def __init__(self, func_url: str):
        self.func_url = func_url
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.region = 'us-east-1'
        self.anthropic = AnthropicBedrock()
        self.headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        }
        

    async def send_to_lambda(self, message: JSONRPCMessage):
        request = AWSRequest(
            method='POST',
            url=self.func_url,
            data=message.model_dump_json(),
            headers=self.headers
        )
        SigV4Auth(self.credentials, "lambda", self.region).add_auth(request)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                request.url,
                content=request.data,
                headers=dict(request.headers)
            )
            lambda_response = response.json()
            if 'body' in lambda_response:
                return json.loads(lambda_response['body'])
            else:
                raise ValueError(f"Unexpected response format: {lambda_response}")

    async def list_tools(self):
        """Get available tools from the MCP server"""
        list_tools_msg = JSONRPCMessage(
            JSONRPCRequest(
                jsonrpc="2.0",
                method="tools/list",
                id=1
            )
        )
        response = await self.send_to_lambda(list_tools_msg)
        return response['result']['tools']

    async def call_tool(self, name: str, arguments: dict):
        """Call a specific tool with arguments"""
        call_tool_msg = JSONRPCMessage(
            JSONRPCRequest(
                jsonrpc="2.0",
                method="tools/call",
                params={
                    "name": name,
                    "arguments": arguments
                },
                id=2
            )
        )
        response = await self.send_to_lambda(call_tool_msg)
        return response['result']

    async def process_query(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [{"role": "user", "content": query}]
        final_text = []
        tools = await self.list_tools()

        available_tools = [
            {
                "name": tool['name'],
                "description": tool['description'],
                "input_schema": tool['inputSchema']
            }
            for tool in tools
        ]

        while True:
            # Get response from Claude
            response = self.anthropic.messages.create(
                model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                max_tokens=1000,
                messages=messages,
                tools=available_tools,
            )
            
            for content in response.content:
                if content.type == "text":
                    final_text.append(content.text)
                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input

                    # Call the tool
                    result = await self.call_tool(tool_name, tool_args)
                    final_text.append(f"[Tool Result: {result}]")
                    
                    # Add the tool result to the conversation
                    messages.append({
                        "role": "assistant",
                        "content": response.content[0].text
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Tool result: {result}"
                    })
                    
                    # Continue the conversation
                    continue
            break

        return "\n".join(final_text)


async def main():
    func_url = FUNCTION_URL
    client = LambdaMCPClient(func_url)
    
    # List available tools
    tools = await client.list_tools()
    print("Available tools:", tools)
    
    # Test the model with a query
    query = "Please greet someone named Bob using the greeting tool"
    result = await client.process_query(query)
    print("\nQuery result:", result)

if __name__ == "__main__":
    asyncio.run(main())
