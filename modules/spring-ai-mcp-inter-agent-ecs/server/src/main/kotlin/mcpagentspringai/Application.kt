package mcpagentspringai

import org.springaicommunity.mcp.annotation.McpTool
import org.springframework.ai.tool.annotation.ToolParam
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication
import org.springframework.stereotype.Service

@SpringBootApplication
class Application

data class Employee(val name: String, val skills: List<String>)

@Service
class MyTools {

    @McpTool(description = "the list of all possible employee skills")
    fun getSkills(): Set<String> = run {
        println("getSkills")
        SampleData.employees.flatMap { it.skills }.toSet()
    }

    @McpTool(description = "the employees that have a specific skill")
    fun getEmployeesWithSkill(@ToolParam(description = "skill") skill: String): List<Employee> = run {
        println("getEmployeesWithSkill $skill")
        SampleData.employees.filter { employee ->
            employee.skills.any { it.equals(skill, ignoreCase = true) }
        }
    }

}

fun main(args: Array<String>) {
    SampleData.employees.forEach { println(it) }
    runApplication<Application>(*args)
}
