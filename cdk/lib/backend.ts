import { Construct } from "constructs"
import { DockerImageAsset, Platform } from "aws-cdk-lib/aws-ecr-assets"
import { CfnOutput, Stack, StackProps } from "aws-cdk-lib"
import { CfnRuntime } from "aws-cdk-lib/aws-bedrockagentcore"
import { Effect, PolicyStatement, Role, ServicePrincipal } from "aws-cdk-lib/aws-iam"
import path from "node:path"

export class VoiceAgentBackendStack extends Stack {
    // Optionally set up the environment
    // 1. make sure the sample rates set here matches the ones set on the CLI
    // 2. To set the region, use stack env instead, ie: VoiceAgentBackendStack(app, "...", env=cdk.Environment(region="us-east-1"))

    MODEL_ID = "amazon.nova-2-sonic-v1:0"
    INPUT_SAMPLE_RATE = "16000"
    OUTPUT_SAMPLE_RATE = "16000"
    CHANNELS = "1"

    constructor(scope: Construct, id: string, props: StackProps) {
        super(scope, id, props)

        // agentcore runtime
        const dockerImageAsset = new DockerImageAsset(this, "BackendAppAsset", {
            // The directory where the Dockerfile is stored
            directory: path.join(__dirname, "..", "..", "backend"),
            platform: Platform.LINUX_ARM64,
            file: "Dockerfile",
        })

        const agentCoreRole = new Role(this, "AgentCoreRole", {
            assumedBy: new ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description: "IAM role for Bedrock AgentCore Runtime",
        })

        const region = this.region
        const accountId = this.account

        // ECR
        agentCoreRole.addToPolicy(new PolicyStatement({
            sid: "ECRTokenAccess",
            effect: Effect.ALLOW,
            actions: [
                "ecr:GetAuthorizationToken"
            ],
            resources: ["*"]
        }))


        agentCoreRole.addToPolicy(new PolicyStatement({
            sid: "ECRImageAccess",
            effect: Effect.ALLOW,
            actions: [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            resources: [
                `arn:aws:ecr:${region}:${accountId}:repository/*`
            ]
        }))


        // Logging
        agentCoreRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                "logs:DescribeLogGroups"
            ],
            resources: [
                `arn:aws:logs:${region}:${accountId}:log-group:*`
            ]
        }))

        agentCoreRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                "logs:DescribeLogStreams",
                "logs:CreateLogGroup"
            ],
            resources: [
                `arn:aws:logs:${region}:${accountId}:log-group:/aws/bedrock-agentcore/runtimes/*`
            ]
        }))

        agentCoreRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            resources: [
                `arn:aws:logs:${region}:${accountId}:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*`
            ]
        }))


        agentCoreRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ["cloudwatch:PutMetricData"],
            resources: ["*"],
            conditions: {
                StringEquals: {
                    "cloudwatch:namespace": "bedrock-agentcore"
                }
            }
        }))


        agentCoreRole.addToPolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets"
            ],
            resources: ["*"]
        }))


        // Bedrock
        agentCoreRole.addToPolicy(new PolicyStatement({
            sid: "BedrockModelInvocation",
            effect: Effect.ALLOW,
            actions: [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            resources: [
                "arn:aws:bedrock:*::foundation-model/*",
                `arn:aws:bedrock:${region}:${accountId}:*`
            ]
        }))

        const runtime = new CfnRuntime(this, "AgentCoreRuntime", {
            agentRuntimeName: "Itsuki_AgentCoreRuntime",
            agentRuntimeArtifact: {
                containerConfiguration: {
                    containerUri: dockerImageAsset.imageUri,
                }
            },
            networkConfiguration: {
                networkMode: "PUBLIC",
            },
            roleArn: agentCoreRole.roleArn,
            protocolConfiguration: "HTTP",
            environmentVariables: {
                "MODEL_ID": this.MODEL_ID,
                "REGION_NAME": this.region,
                "INPUT_SAMPLE_RATE": this.INPUT_SAMPLE_RATE,
                "OUTPUT_SAMPLE_RATE": this.OUTPUT_SAMPLE_RATE,
                "CHANNELS": this.CHANNELS,
            },
            // for oauth
            // authorizerConfiguration: {
            //     customJwtAuthorizer: {
            //         // client Id: user pool client id
            //         allowedClients: [props.cognitoClientId],
            //         discoveryUrl: `https://cognito-idp.${region}.amazonaws.com/${props.cognitoPool.userPoolId}/.well-known/openid-configuration`
            //     }
            // }
        })

        runtime.node.addDependency(agentCoreRole)

        const _ = new CfnOutput(this, "AgentCoreRuntimeArn", {
            value: runtime.attrAgentRuntimeArn
        })
    }
}
