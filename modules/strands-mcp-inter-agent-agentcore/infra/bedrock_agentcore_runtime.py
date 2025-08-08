import aws_cdk

from aws_cdk import (
    aws_iam,
    aws_lambda,
    aws_ecr,
)

from constructs import Construct

import cdk_ecr_deployment


class BedrockAgentCoreRuntime(Construct):
    def __init__(self, scope: Construct, construct_id: str, *,
                 repository: str,
                 protocol: str,
                 discovery_url: str = None,
                 client_id: str = None,
                 env: dict = None,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        agentcore_custom_resource_repo = aws_ecr.Repository(
            self,
            "AgentCoreCustomResourceRepo",
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            empty_on_delete=True,
            lifecycle_rules=[
                aws_ecr.LifecycleRule(
                    max_image_count=5,
                    description="Only keep 5 images"
                )
            ]
        )

        cfn_customresource_agentcore_image_tag="e55e62a"

        ecr_deployment = cdk_ecr_deployment.ECRDeployment(self, "AgentCoreCustomResourceImage",
                                                          src=cdk_ecr_deployment.DockerImageName(f"ghcr.io/jamesward/cfn-customresource-agentcore:{cfn_customresource_agentcore_image_tag}"),
                                                          dest=cdk_ecr_deployment.DockerImageName(
                                                              agentcore_custom_resource_repo.repository_uri_for_tag(cfn_customresource_agentcore_image_tag)
                                                          )
                                                          )

        custom_resource_lambda = aws_lambda.DockerImageFunction(
            self,
            "AgentCoreCustomResourceLambda",
            code=aws_lambda.DockerImageCode.from_ecr(
                agentcore_custom_resource_repo,
                tag_or_digest=cfn_customresource_agentcore_image_tag
            ),
            memory_size=256,
        )

        custom_resource_lambda.node.add_dependency(ecr_deployment)

        # todo: tighten
        custom_resource_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "bedrock-agentcore:*",
                    "iam:PassRole"
                ],
                resources=["*"]
            )
        )

        account_id = aws_cdk.Stack.of(self).account
        region = aws_cdk.Stack.of(self).region

        permissions_policy = aws_iam.PolicyDocument(
            statements=[
                aws_iam.PolicyStatement(
                    sid="ECRImageAccess",
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer"
                    ],
                    resources=[
                        f"arn:aws:ecr:{region}:{account_id}:repository/*"
                    ]
                ),

                aws_iam.PolicyStatement(
                    sid="ECRTokenAccess",
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "ecr:GetAuthorizationToken"
                    ],
                    resources=["*"]
                ),

                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "logs:DescribeLogStreams",
                        "logs:CreateLogGroup"
                    ],
                    resources=[
                        f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
                    ]
                ),

                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "logs:DescribeLogGroups"
                    ],
                    resources=[
                        f"arn:aws:logs:{region}:{account_id}:log-group:*"
                    ]
                ),

                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
                    ]
                ),

                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                        "xray:GetSamplingRules",
                        "xray:GetSamplingTargets"
                    ],
                    resources=["*"]
                ),

                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=["cloudwatch:PutMetricData"],
                    resources=["*"],
                    conditions={
                        "StringEquals": {
                            "cloudwatch:namespace": "bedrock-agentcore"
                        }
                    }
                ),

                aws_iam.PolicyStatement(
                    sid="GetAgentAccessToken",
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "bedrock-agentcore:GetWorkloadAccessToken",
                        "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                        "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
                    ],
                    resources=[
                        f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                        f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/*" # todo: add agent_name
                    ]
                ),

                aws_iam.PolicyStatement(
                    sid="BedrockModelInvocation",
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    resources=[
                        "arn:aws:bedrock:*::foundation-model/*",
                        f"arn:aws:bedrock:{region}:{account_id}:*"
                    ]
                )
            ]
        )

        agentcore_runtime_role = aws_iam.Role(
            self,
            "BedrockAgentCoreRuntimeRole",
            assumed_by=aws_iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "permissions": permissions_policy
            },
            description="Execution role for Amazon Bedrock AgentCore Runtime"
        )

        self.resource = aws_cdk.CustomResource(
            self,
            "AgentCoreRuntime",
            service_token=custom_resource_lambda.function_arn,
            properties={
                "ContainerUri": repository,
                "RoleArn": agentcore_runtime_role.role_arn,
                "ServerProtocol": protocol,
                "ImageTag": cfn_customresource_agentcore_image_tag, # to trigger update if the lambda changes
                **({} if env is None else {"Env": env}),
                **({} if discovery_url is None else {
                    "AuthorizerConfiguration": {
                        "customJWTAuthorizer": {
                            "discoveryUrl": discovery_url,
                            **({"allowedClients": [client_id]} if client_id is not None else {})
                        }
                    }
                })
            },
        )

        self.resource.node.add_dependency(custom_resource_lambda)
