import boto3
import json
import io
import zipfile

def create_lambda_function():
    lambda_client = boto3.client('lambda')
    iam = boto3.client('iam')

    function_name = 'mcp-lambda'
    role_name = 'mcp-lambda-role'
    lambda_handler = 'server.lambda_handler'

    # Create IAM role for Lambda
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy)
        )
    except iam.exceptions.EntityAlreadyExistsException:
        role = iam.get_role(RoleName=role_name)

    # Attach necessary policies
    iam.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    )

    # Create custom policy for Bedrock
    bedrock_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:InvokeModel"
                ],
                "Resource": "*"
            }
        ]
    }

    try:
        policy = iam.create_policy(
            PolicyName='mcp-lambda-bedrock-policy',
            PolicyDocument=json.dumps(bedrock_policy)
        )
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy['Policy']['Arn']
        )
    except iam.exceptions.EntityAlreadyExistsException:
        pass

    # Create deployment package
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.write('server.py')

    # Wait for role to be ready
    import time
    time.sleep(10)

    # Lambda Web Adapter Layer ARN (replace with the correct ARN for your region)
    lambda_web_adapter_layer = "YOUR_LAMBDA_LAYER_HERE"

    try:
        # Create Lambda function
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.12',
            Role=role['Role']['Arn'],
            Handler=lambda_handler,
            Code={'ZipFile': zip_buffer.getvalue()},
            MemorySize=1024,
            Timeout=900,
            Environment={
                'Variables': {
                    'AWS_LWA_INVOKE_MODE': 'RESPONSE_STREAM',
                    'PORT': '8080'
                }
            },
            Layers=[lambda_web_adapter_layer]
        )
    except lambda_client.exceptions.ResourceConflictException:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_buffer.getvalue()
        )
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={
                'Variables': {
                    'AWS_LWA_INVOKE_MODE': 'RESPONSE_STREAM',
                    'PORT': '8080'
                }
            },
            Layers=[lambda_web_adapter_layer]
        )

    # Create or update function URL
    try:
        url_config = lambda_client.create_function_url_config(
            FunctionName=function_name,
            AuthType='AWS_IAM',
            InvokeMode='RESPONSE_STREAM'
        )
    except lambda_client.exceptions.ResourceConflictException:
        url_config = lambda_client.update_function_url_config(
            FunctionName=function_name,
            AuthType='AWS_IAM',
            InvokeMode='RESPONSE_STREAM'
        )

    print(f"Function URL: {url_config['FunctionUrl']}")
    return url_config['FunctionUrl']

if __name__ == "__main__":
    function_url = create_lambda_function()
    print(f"\nDeployment complete. Function URL: {function_url}")
