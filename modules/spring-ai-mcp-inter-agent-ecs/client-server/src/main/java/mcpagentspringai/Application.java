package mcpagentspringai;

import io.modelcontextprotocol.client.McpSyncClient;
import org.springaicommunity.mcp.annotation.McpTool;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.mcp.SyncMcpToolCallbackProvider;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.stereotype.Service;

import java.util.List;

@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

@Configuration
class AgentConfiguration {

    // Bedrock Converse chat client with employee database MCP client
    // The manual toolcallback creation (as opposed to automatic ToolCallbackProvider) is used to avoid having this MCP server expose the MCP client's tools as well
    @Bean
    ChatClient chatClient(List<McpSyncClient> mcpSyncClients, ChatClient.Builder builder) {
        return builder
                .defaultToolCallbacks(SyncMcpToolCallbackProvider.builder().mcpClients(mcpSyncClients).build())
                .defaultSystem("abbreviate employee first names with first letter and a period")
                .build();
    }

}

@Service
class EmployeeQueries {
    private final ChatClient chatClient;

    EmployeeQueries(ChatClient chatClient) {
        this.chatClient = chatClient;
    }

    String query(String question) {
        return chatClient
                .prompt()
                .user(question)
                .call()
                .content();
    }

}

@Service
class MyTools {

    private final EmployeeQueries employeeQueries;

    MyTools(EmployeeQueries employeeQueries) {
        this.employeeQueries = employeeQueries;
    }

    @McpTool(description = "answers questions related to our employees")
    String inquire(@ToolParam(description = "the query about the employees", required = true) String question) {
        return employeeQueries.query(question);
    }

}
