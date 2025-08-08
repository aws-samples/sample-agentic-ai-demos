import os
import random
import string

import boto3
import json

region = os.environ.get("AWS_REGION", "us-east-1")

agent_arn = os.environ.get("AGENT_ARN")

agent_core_client = boto3.client('bedrock-agentcore', region_name=region)
payload = json.dumps({"question": "list employees that have skills related to AI"})

session_id = "".join(random.choices(string.digits + string.ascii_lowercase, k=33))

response = agent_core_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=session_id,
    payload=payload,
    qualifier="DEFAULT"
)

response_body = response['response'].read()
response_data = json.loads(response_body)
print(response_data)
