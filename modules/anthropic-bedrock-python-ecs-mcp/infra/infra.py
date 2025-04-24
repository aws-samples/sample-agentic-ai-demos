from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_servicediscovery as servicediscovery,
    CfnOutput,
    Duration,
)
from constructs import Construct

class MCPAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC
        self.vpc = ec2.Vpc(
            self, "ApplicationVPC",
            max_azs=2,
            cidr="10.0.0.0/16",
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # ECS Cluster
        self.cluster = ecs.Cluster(
            self, "ECSCluster",
            vpc=self.vpc,
            cluster_name=f"{construct_id}-cluster"
        )

        # Log Group
        log_group = logs.LogGroup(
            self, "LogGroup",
            log_group_name=f"/ecs/{construct_id}",
            retention=logs.RetentionDays.ONE_DAY,
        )

        # IAM Roles
        server_execution_role = iam.Role(
            self, "ServerExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ]
        )

        client_execution_role = iam.Role(
            self, "ClientExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ]
        )

        task_role = iam.Role(
            self, "TaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ]
        )

        # Add Bedrock policy to task role
        task_role.add_to_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"]
            )
        )

        # Security Groups
        server_security_group = ec2.SecurityGroup(
            self, "ServerSecurityGroup",
            vpc=self.vpc,
            description="Security group for server container"
        )

        client_security_group = ec2.SecurityGroup(
            self, "ClientSecurityGroup",
            vpc=self.vpc,
            description="Security group for client container"
        )

        alb_security_group = ec2.SecurityGroup(
            self, "LoadBalancerSecurityGroup",
            vpc=self.vpc,
            description="Security group for ALB"
        )

        # Security Group rules
        server_security_group.add_ingress_rule(
            peer=client_security_group,
            connection=ec2.Port.tcp(8000)
        )

        client_security_group.add_ingress_rule(
            peer=alb_security_group,
            connection=ec2.Port.tcp(8080)
        )

        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80)
        )

        # Service Connect Namespace
        namespace = servicediscovery.HttpNamespace(
            self, "ServiceConnectNamespace",
            name=construct_id
        )

        # Task Definitions
        server_task_definition = ecs.FargateTaskDefinition(
            self, "MCPServerTaskDefinition",
            execution_role=server_execution_role,
            task_role=task_role,
            cpu=256,
            memory_limit_mib=512
        )

        client_task_definition = ecs.FargateTaskDefinition(
            self, "MCPClientTaskDefinition",
            execution_role=client_execution_role,
            task_role=task_role,
            cpu=256,
            memory_limit_mib=1024
        )

        # Container Definitions
        server_container = server_task_definition.add_container(
            "mcp-agent-ai-server",
            image=ecs.ContainerImage.from_registry(
                f"{Stack.of(self).account}.dkr.ecr.{Stack.of(self).region}.amazonaws.com/mcp-sse:server-image"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=log_group
            ),
            port_mappings=[ecs.PortMapping(container_port=8000)]
        )

        client_container = client_task_definition.add_container(
            "mcp-agent-ai-client",
            image=ecs.ContainerImage.from_registry(
                f"{Stack.of(self).account}.dkr.ecr.{Stack.of(self).region}.amazonaws.com/mcp-sse:client-image"
            ),
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_group=log_group
            ),
            port_mappings=[ecs.PortMapping(container_port=8080)],
            environment={
                "SERVER_URL": f"http://mcp-server.{construct_id}:8000"
            }
        )

        # Load Balancer
        load_balancer = elbv2.ApplicationLoadBalancer(
            self, "LoadBalancer",
            vpc=self.vpc,
            internet_facing=True,
            security_group=alb_security_group
        )

        # Target Group
        target_group = elbv2.ApplicationTargetGroup(
            self, "TargetGroup",
            vpc=self.vpc,
            port=8080,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                path="/actuator/health",
                timeout=Duration.seconds(120),
                interval=Duration.seconds(240)
            )
        )

        listener = load_balancer.add_listener(
            "Listener",
            port=80,
            default_target_groups=[target_group]
        )

        # ECS Services
        server_service = ecs.FargateService(
            self, "MCPServerECSService",
            cluster=self.cluster,
            task_definition=server_task_definition,
            security_groups=[server_security_group],
            service_connect_configuration=ecs.ServiceConnectConfiguration(
                namespace=namespace,
                services=[ecs.ServiceConnectService(
                    port_mapping_name="http",
                    discovery_name="mcp-server",
                    port=8000
                )]
            )
        )

        client_service = ecs.FargateService(
            self, "MCPClientECSService",
            cluster=self.cluster,
            task_definition=client_task_definition,
            security_groups=[client_security_group],
            service_connect_configuration=ecs.ServiceConnectConfiguration(
                namespace=namespace
            )
        )

        # Output
        CfnOutput(
            self, "LoadBalancerDNS",
            value=load_balancer.load_balancer_dns_name,
            description="DNS name of the load balancer"
        )
