package javamcpbedrockagent;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.transport.HttpClientSseClientTransport;
import io.modelcontextprotocol.spec.McpSchema;
import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.core.document.Document;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient;
import software.amazon.awssdk.services.bedrockruntime.model.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class Application {

    static Document mcpPropertyToDocument(Object o) {
        var properties = switch (o) {
            case Map<?, ?> map when map.keySet().stream().allMatch(k -> k instanceof String)
                    && map.values().stream().allMatch(v -> v instanceof String) ->
                map.entrySet().stream()
                        .map(e -> Map.entry((String)e.getKey(), Document.fromString((String)e.getValue())))
                        .collect(Collectors.toMap(
                                Map.Entry::getKey,
                                Map.Entry::getValue
                        ));
            default -> new HashMap<String, Document>(); // todo: silent failure
        };

        return Document.fromMap(properties);
    }

    static Document mcpInputSchemaToDocument(McpSchema.JsonSchema jsonSchema) {
        var propertiesMap = new HashMap<String, Document>();

        jsonSchema.properties().forEach((key, value) ->
            propertiesMap.put(key, mcpPropertyToDocument(value))
        );

        var requiredList = jsonSchema.required().stream().map(Document::fromString).toList();

        Map<String, Document> rootMap = new HashMap<>();
        rootMap.put("type", Document.fromString("object"));
        rootMap.put("properties", Document.fromMap(propertiesMap));
        rootMap.put("required", Document.fromList(requiredList));

        return Document.fromMap(rootMap);
    }

    static ToolConfiguration mcpToolsToConverseTools(List<McpSchema.Tool> mcpTools) {
        var tools = mcpTools.stream().map(mcpTool -> {
            var inputSchema = ToolInputSchema.fromJson(mcpInputSchemaToDocument(mcpTool.inputSchema()));

            var toolSpec = ToolSpecification.builder()
                    .name(mcpTool.name())
                    .description(mcpTool.description())
                    .inputSchema(inputSchema)
                    .build();

            return Tool.builder().toolSpec(toolSpec).build();
        }).toList();

        return ToolConfiguration.builder().tools(tools).build();
    }


    public static void main(String[] args) {
//        var query = "how many active connections does the tool server have?"; // no params on tool
//        var query = "how many POST connections have been made to the tool server since it started?"; // pass param to tool
//        var query = "how many connections have been made to the tool server since it started?"; // don't pass an optional param
        var query = "Get employees that have skills related to Java";

        System.out.println(query);

//        var transport = HttpClientSseClientTransport.builder("https://mcp-test.jamesward.com").build();
        var transport = HttpClientSseClientTransport.builder("http://localhost:8082").build();

        try (var mcpClient = McpClient.sync(transport).build()) {
            var mcpServerInfo = mcpClient.initialize();

            var toolConfig = mcpToolsToConverseTools(mcpClient.listTools().tools());

            var system = mcpServerInfo.instructions() != null ? SystemContentBlock.fromText(mcpServerInfo.instructions()) : null;

            var modelId = "amazon.nova-micro-v1:0";

            var messages = new ArrayList<Message>();

            var firstMessage = Message.builder()
                    .content(ContentBlock.fromText(query))
                    .role(ConversationRole.USER)
                    .build();

            messages.add(firstMessage);

            try (var bedrockClient = BedrockRuntimeClient.builder()
                    .credentialsProvider(DefaultCredentialsProvider.create())
                    .region(Region.US_EAST_1)
                    .build()) {

                while (true) {
                    var requestBuilder = ConverseRequest.builder()
                            .modelId(modelId)
                            .messages(messages)
                            .toolConfig(toolConfig);

                    var request = system != null ? requestBuilder.system(system).build() : requestBuilder.build();

                    var response = bedrockClient.converse(request);

                    messages.add(response.output().message());

                    response.output().message().content().forEach(content -> {
                        if (content.text() != null) System.out.println(content.text());
                    });

                    if (response.stopReason() == StopReason.TOOL_USE) {
                        List<ContentBlock> allResultContents = response.output().message().content().stream().flatMap(contentBlock -> {
                            if (contentBlock.toolUse() != null) {
                                var input = contentBlock.toolUse().input().asMap().entrySet().stream()
                                        .map(e -> Map.entry(e.getKey(), e.getValue().unwrap()))
                                        .collect(Collectors.toMap(
                                                Map.Entry::getKey,
                                                Map.Entry::getValue
                                        ));

                                var callToolRequest = new McpSchema.CallToolRequest(
                                        contentBlock.toolUse().name(),
                                        input
                                );

                                var callToolResult = mcpClient.callTool(callToolRequest);
                                // todo: isError

                                var resultContents = callToolResult.content().stream().map(content ->
                                        switch (content) {
                                            case McpSchema.TextContent textContent -> ToolResultContentBlock.builder()
                                                    .text(textContent.text())
                                                    .build();
                                            default -> ToolResultContentBlock.builder().build();
                                        }
                                ).toList();

                                var toolResultBlock = ToolResultBlock.builder()
                                        .toolUseId(contentBlock.toolUse().toolUseId())
                                        .content(resultContents)
                                        .build();

                                return Stream.of(ContentBlock.fromToolResult(toolResultBlock));
                            }
                            else {
                                return Stream.of();
                            }
                        }).toList();

                        var resultMessage = Message.builder()
                                .role(ConversationRole.USER)
                                .content(allResultContents)
                                .build();

                        messages.add(resultMessage);
                    }
                    else if (response.stopReason() == StopReason.END_TURN) {
                        break;
                    }
                }
            }
        }
    }
}
