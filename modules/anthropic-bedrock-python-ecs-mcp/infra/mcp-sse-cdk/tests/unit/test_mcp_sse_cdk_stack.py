import aws_cdk as core
import aws_cdk.assertions as assertions

from mcp_sse_cdk.mcp_sse_cdk_stack import McpSseCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in mcp_sse_cdk/mcp_sse_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = McpSseCdkStack(app, "mcp-sse-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
