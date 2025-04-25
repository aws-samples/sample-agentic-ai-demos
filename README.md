## Model Context Protocol samples

Collection of examples of how to use Model Context Protocol with AWS.

List of modules:

| Module                                                                                                        | Lang               | Description                                                                                                                                                                    |
|---------------------------------------------------------------------------------------------------------------|--------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [Server Client MCP/SSE Demo](./modules/converse-client-server-sse-demo-docker/)                               | TypeScript         | This full demo creates an Amazon Bedrock MCP client using the converse API and MCP server. The sample is deployed in containers that connect over MCP/SSE.                     |
| [Server Client MCP/stdio Demo](./modules/converse-client-server-stdio-demo-local/)                            | Python             | This is a demo Amazon Bedrock MCP client using the converse API and a simple MCP stdio server. The sample runs locally connected with Amazon Bedrock.                          |
| [Server Client MCP/SSE on ECS](./modules/spring-ai-agent-ecs/)                                                | Spring AI & Kotlin | Provides a sample Spring AI MCP Server that runs on ECS; which is used by a Spring AI Agent using Bedrock; which also runs on ECS and is exposed publicly via a Load Balancer. |
| [Server Client MCP/SSE in Bedrock Converse Client w/ pgVector RAG](./modules/spring-ai-java-bedrock-mcp-rag/) | Spring AI & Java   | A Spring AI dog adoption agent built on Bedrock using PostgreSQL with pgvector for RAG, and an MCP Server for managing adoption appointments.                                  |
| [Server MCP/SSE on ECS](./modules/spring-ai-mcp-server-ecs/)                                                  | Spring AI & Kotlin | Very basic Spring AI MCP Server over SSE running on ECS.                                                                                                                       |
| [MCP/SSE Server - FastAPI Client with Anthropic Bedrock](./modules/anthropic-bedrock-python-ecs-mcp/)         | Python             | An MCP SSE server with a FastAPI client that leverages Anthropic Bedrock. The sample runs on ECS Fargate with public access through an Application Load Balancer. |

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
