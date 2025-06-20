# Serverless MCP with AWS Lambda

This project demonstrates how to deploy a Model Context Protocol (MCP) server as a serverless function using AWS Lambda with Function URLs. It uses the new Streamable HTTP protocol and AWS IAM authentication for security.

## Architecture
- Lambda Function with AWS Lambda Web Adapter
- AWS IAM Authentication

## Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.11+
- boto3
- An existing Lambda layer containing MCP and its dependencies
- Lambda Web Adapter layer ARN

## Step 1: Prepare Lambda Layer

Ensure you have created a Lambda layer containing MCP and its dependencies. You should have the ARN of this layer ready for the deployment script.

## Step 2: Deploy Lambda Function

1. Update `deployment.py` with your MCP layer ARN and the correct Lambda Web Adapter layer ARN for your region.
```python
# Update this lines with your layer ARNs
lambda_web_adapter_layer = "arn:aws:lambda:us-east-1:XXXXXXXX:layer"
```

2. Deploy the function:
```bash
python deployment.py
```

3. Save the Function URL from the output.

## Step 3: Test with MCP Client

Within `client.py`:
```python
# Replace with your Lambda Function URL
FUNCTION_URL = os.getenv('FUNCTION_URL')
```

Update `FUNCTION_URL` within your Lambda Function URL and run:
```bash
python client.py
```

## Security
- Function URL uses AWS IAM authentication
- All requests must be signed with SigV4
- Lambda execution role has minimal required permissions

## Key Features
- Serverless MCP implementation
- Streamable HTTP protocol support
- AWS IAM authentication
- Stateless operation

## Troubleshooting
- Check Lambda CloudWatch logs for execution issues
- Verify IAM permissions for both function and client
- Ensure AWS credentials are properly configured
- Check Layer ARNs are correct in deployment script

This setup provides a secure, scalable, and cost-effective way to deploy MCP servers using AWS Lambda.