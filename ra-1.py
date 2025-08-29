
#!/usr/bin/env python3
# modified from https://github.com/anthropics/dxt/blob/main/examples/file-manager-python/server/main.py

import os
import sys
import argparse
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from urllib.parse import quote

# Parse command line arguments
parser = argparse.ArgumentParser(description="File Manager MCP Server")
parser.add_argument(
    "--workspace", default=os.path.expanduser("~/Documents"), help="Workspace directory"
)
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
args = parser.parse_args()

# Initialize server
mcp = FastMCP("ra-1")

def register_file_resources(workspace: str) -> None:
    """
    For each file under `workspace`, register a concrete resource at:
      workspace://<percent-encoded-relative-path>

    Example:
      /Users/hani/docs/report 1.pdf -> workspace://docs/report%201.pdf
    """
    root = Path(workspace).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Workspace does not exist or is not a directory: {workspace}")

    def make_resource(uri: str, target: Path, display_name: str):
        # Define a unique resource function bound to this file & URI
        @mcp.resource(
            uri,
            name=display_name,                    # resource name shown to clients
            description=f"{display_name}",
            mime_type="application/pdf",          # ensures clients treat it as a PDF
        )
        def _file_resource() -> bytes:
            # Return raw bytes so binary files work too
            return target.read_bytes()
        return _file_resource

    for p in root.rglob("*.pdf"):
        if p.is_file():
            rel = p.relative_to(root).as_posix()        # posix-style path
            uri = f"workspace://{quote(rel, safe='/')}" # keep slashes, encode spaces, etc.
            make_resource(uri, p, p.name)

if __name__ == "__main__":
    # Debug output if enabled
    if args.debug:
        print("Starting Research Assistant MCP Server...", file=sys.stderr)
        print(f"Workspace: {args.workspace}", file=sys.stderr)
    
    # Register workspace files as MCP resources
    register_file_resources(args.workspace)

    # Run the server
    mcp.run()
