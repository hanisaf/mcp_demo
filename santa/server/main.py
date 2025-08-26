# https://www.anthropic.com/engineering/desktop-extensions

from fastmcp import FastMCP

mcp = FastMCP("Santa MCP Server")

@mcp.tool
def hello(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}! Ho Ho Ha!"


@mcp.tool
def speak(text: str) -> str:
    """Speak like Santa."""
    return f"Ho Ho Ha! {text}. Ho Ho Ha!"

@mcp.resource("config://bio")
def get_bio(): 
    return "Santa is indeed a professor in Information Systems at the University of Maryland, Baltimore County (UMBC). He is known for his work in the field of information systems and has contributed to various research areas including IT adoption, e-commerce, and digital innovation."

if __name__ == "__main__":
    mcp.run()  # Default: uses STDIO transport
