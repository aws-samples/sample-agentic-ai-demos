from mcp.server.fastmcp import FastMCP
import json
import asyncio

app = FastMCP(name="Greeting")

@app.tool()
def greeting(name: str) -> str:
    """
    Return a specialized, friendly greeting to the user.

    Args: 
        name: The name of the person we are greeting

    Returns:
        Text greeting with the user's name.
    """
    return f"Hello {name}!"

# Configure FastMCP for Lambda
app.settings.stateless_http = True
app.settings.json_response = True

async def handle_request(event):
    # Extract the JSON-RPC message from the Lambda Function URL event
    if 'body' in event:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
    else:
        body = event

    # Create a fresh session manager and ASGI app for each request
    asgi_app = app.streamable_http_app()
    session_manager = app._session_manager

    # Prepare the ASGI event
    scope = {
        'type': 'http',
        'http_version': '1.1',
        'method': 'POST',
        'path': '/mcp/',
        'raw_path': b'/mcp/',
        'query_string': b'',
        'headers': [
            [b'content-type', b'application/json'],
            [b'accept', b'application/json, text/event-stream'],
        ],
    }

    response = {}
    
    async def receive():
        return {'type': 'http.request', 'body': json.dumps(body).encode()}

    async def send(message):
        if message['type'] == 'http.response.start':
            response['status_code'] = message['status']
            response['headers'] = {k.decode(): v.decode() for k, v in message.get('headers', [])}
        elif message['type'] == 'http.response.body':
            response['body'] = message.get('body', b'').decode()

    async with session_manager.run():
        await asgi_app(scope, receive, send)

    return response

def lambda_handler(event, context):
    # Reset the session manager for each invocation
    app._session_manager = None
    
    response = asyncio.run(handle_request(event))
    
    return {
        'statusCode': response['status_code'],
        'headers': response['headers'],
        'body': response['body']
    }
