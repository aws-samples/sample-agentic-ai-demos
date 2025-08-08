from typing import Optional

import aws_cdk
from aws_cdk import (
    aws_iam,
    aws_lambda,
    aws_ecr,
    aws_s3_assets,
    aws_codebuild,
)
from constructs import Construct
import cdk_ecr_deployment


# todo: rebuild on source changes
class BuildpackImageAsset(Construct):
    def __init__(self, scope: Construct, construct_id: str, *,
                 source_path: str,
                 builder: str,
                 run_image: str,
                 platform: str,
                 default_process: Optional[str] = None,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        repo = aws_ecr.Repository(self, "Repo",
                                       removal_policy=aws_cdk.RemovalPolicy.DESTROY,
                                       empty_on_delete=True,
                                       lifecycle_rules=[
                                           aws_ecr.LifecycleRule(
                                               max_image_count=5,
                                               description="Only keep 5 images"
                                           )
                                       ]
                                       )

        source_asset = aws_s3_assets.Asset(self, "BuildSource",
                                           path=source_path,
                                           exclude=[".git", "cdk.out", ".venv", ".idea", "infra"]  # todo: yuck
                                           )

        self.ecr_repo=repo.repository_uri_for_tag(source_asset.s3_object_key.split("/")[-1].removesuffix(".zip"))

        build_project = aws_codebuild.Project(self, "Project",
                                              environment=aws_codebuild.BuildEnvironment(
                                                  privileged=True,  # for docker-in-docker support
                                                  build_image=aws_codebuild.LinuxBuildImage.AMAZON_LINUX_2_ARM_3
                                                  # todo: non-arm also
                                              ),
                                              source=aws_codebuild.Source.s3(
                                                  bucket=source_asset.bucket,
                                                  path=source_asset.s3_object_key
                                              ),
                                              environment_variables={
                                                  "AWS_ACCOUNT_ID": aws_codebuild.BuildEnvironmentVariable(
                                                      value=aws_cdk.Stack.of(self).account
                                                  ),
                                                  "AWS_DEFAULT_REGION": aws_codebuild.BuildEnvironmentVariable(
                                                      value=aws_cdk.Stack.of(self).region
                                                  ),
                                                  "ECR_REPO": aws_codebuild.BuildEnvironmentVariable(
                                                      value=self.ecr_repo
                                                  ),
                                                  "BUILDER": aws_codebuild.BuildEnvironmentVariable(
                                                      value=builder
                                                  ),
                                                  "RUN_IMAGE": aws_codebuild.BuildEnvironmentVariable(
                                                      value=run_image
                                                  ),
                                                  # todo: only if not there
                                                  "DEFAULT_PROCESS": aws_codebuild.BuildEnvironmentVariable(
                                                      value=default_process
                                                  )
                                              },
                                              build_spec=aws_codebuild.BuildSpec.from_object({
                                                  "version": 0.2,
                                                  "phases": {
                                                      "pre_build": {
                                                          "commands": [
                                                              "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
                                                          ]
                                                      },
                                                      "install": {
                                                          "commands": [
                                                              "curl -sSL https://github.com/buildpacks/pack/releases/download/v0.38.2/pack-v0.38.2-linux-arm64.tgz | tar -C /usr/local/bin/ -xzv"
                                                              # todo: non-arm also
                                                          ]
                                                      },
                                                      "build": {
                                                          "commands": [
                                                              # todo: non-arm also
                                                              "pack build --platform linux/arm64 --default-process $DEFAULT_PROCESS --builder $BUILDER --run-image $RUN_IMAGE --publish $ECR_REPO"
                                                          ]
                                                      }
                                                  }
                                              }),
                                              )

        source_asset.grant_read(build_project.role)

        repo.grant_pull_push(build_project.role)

        custom_resource_codebuild_startandwait_repo = aws_ecr.Repository(
            self,
            "CustomResourceCodeBuildStartAndWaitRepo",
            removal_policy=aws_cdk.RemovalPolicy.DESTROY,
            empty_on_delete=True,
            lifecycle_rules=[
                aws_ecr.LifecycleRule(
                    max_image_count=5,
                    description="Only keep 5 images"
                )
            ]
        )

        custom_resource_codebuild_startandwait_image = cdk_ecr_deployment.ECRDeployment(self,
                                                                                        "CustomResourceCodeBuildStartAndWaitImage",
                                                                                        src=cdk_ecr_deployment.DockerImageName(
                                                                                            "ghcr.io/jamesward/cfn-customresource-codebuild-startandwait"),
                                                                                        dest=cdk_ecr_deployment.DockerImageName(
                                                                                            custom_resource_codebuild_startandwait_repo.repository_uri)
                                                                                        )

        custom_resource_lambda = aws_lambda.DockerImageFunction(
            self,
            "CustomResourceCodeBuildStartAndWaitLambda",
            code=aws_lambda.DockerImageCode.from_ecr(
                custom_resource_codebuild_startandwait_repo
            ),
            timeout=aws_cdk.Duration.minutes(5),
            memory_size=256,
        )

        custom_resource_lambda.node.add_dependency(custom_resource_codebuild_startandwait_image)

        # # todo: tighten
        custom_resource_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                effect=aws_iam.Effect.ALLOW,
                actions=[
                    "codebuild:*",
                    "iam:PassRole"
                ],
                resources=["*"]
            )
        )

        aws_cdk.CustomResource(
            self,
            "Build",
            service_token=custom_resource_lambda.function_arn,
            properties={
                "ProjectName": build_project.project_name,
                "ECR_REPO": self.ecr_repo, # rebuild when repo changes
            },
        )
