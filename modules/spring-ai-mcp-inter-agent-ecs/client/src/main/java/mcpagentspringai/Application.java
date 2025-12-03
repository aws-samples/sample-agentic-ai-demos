package mcpagentspringai;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

@Configuration
class ConversationalConfiguration {
    @Bean
    ChatClient chatClient(ToolCallbackProvider toolCallbackProvider, ChatClient.Builder builder) {
        return builder
                .defaultToolCallbacks(toolCallbackProvider)
                .build();
    }
}

record Prompt(String question) { }

@RestController
class ConversationalController {

    private final ChatClient chatClient;

    ConversationalController(ChatClient chatClient) {
        this.chatClient = chatClient;
    }

    @PostMapping("/inquire")
    String inquire(@RequestBody Prompt prompt) {
        return chatClient
                .prompt()
                .user(prompt.question())
                .call()
                .content();
    }
}
