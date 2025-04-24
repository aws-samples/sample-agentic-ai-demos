#!/usr/bin/env python3
from mcp_sse_cdk.mcp_sse_cdk_stack import McpSseCdkStack
from aws_cdk import App


app = App()
McpSseCdkStack(app, "McpSseCdkStack")
app.synth()

