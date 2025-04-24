from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Documentation")


@mcp.tool()
def greeting(name: str) -> str:
    """
    Return a specialized, friendly greeting to the user,

    Args:
        name: The name of the person we are greeting

    Returns:
        Text greeting with the user's name.
    """
    return f"Hello {name}!"


if __name__ == "__main__":
    mcp.run(transport="sse")
