# Serverless MCP with AWS Lambda

This project demonstrates how to deploy a Model Context Protocol (MCP) server as a serverless function using AWS Lambda with Function URLs. It uses the new Streamable HTTP protocol and AWS IAM authentication for security.

## Architecture
- Lambda Function with AWS Lambda Web Adapter
- Streamable HTTP Protocol (stateless mode)
- AWS IAM Authentication
- Python 3.11+ Runtime
- MCP Layer containing all dependencies

## Prerequisites
- AWS CLI configured with appropriate permissions
- Python 3.11+
- boto3
- An existing Lambda layer containing MCP and its dependencies
- Lambda Web Adapter layer ARN (varies by region)

## Step 1: Prepare Lambda Layer

Ensure you have created a Lambda layer containing MCP and its dependencies. You should have the ARN of this layer ready for the deployment script.

## Step 2: Deploy Lambda Function

1. Update `deploy.py`:
```python

# Update this lines with your layer ARNs
lambda_web_adapter_layer = "arn:aws:lambda:us-east-1:XXXXXXXX:layer"
```

2. Update `deploy.py` with your MCP layer ARN and the correct Lambda Web Adapter layer ARN for your region.

3. Deploy the function:
```bash
python deploy.py
```

Save the Function URL from the output.

## Step 3: Test with MCP Client

Within `client.py`:
```python
async def main():
    # Replace with your Lambda Function URL
    func_url = 'YOUR_LAMBDA_FUNCTION_URL'
```

Update the `func_url` with your Lambda Function URL and run:
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
- Easy deployment and updates
- Cost-effective (pay per request)

## Notes
- The Lambda Web Adapter handles the translation between HTTP and Lambda
- Streamable HTTP protocol allows for efficient request/response handling
- AWS IAM authentication ensures secure access
- Layer-based deployment simplifies dependency management
- Function URLs provide direct HTTPS endpoint access

## Troubleshooting
- Check Lambda CloudWatch logs for execution issues
- Verify IAM permissions for both function and client
- Ensure AWS credentials are properly configured
- Check Layer ARNs are correct in deployment script

This setup provides a secure, scalable, and cost-effective way to deploy MCP servers using AWS Lambda.