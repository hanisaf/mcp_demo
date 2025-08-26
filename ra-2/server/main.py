#!/usr/bin/env python3
# structure from https://github.com/anthropics/dxt/blob/main/examples/file-manager-python/server/main.py

import re
import mimetypes
import os
import argparse
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from urllib.parse import quote
from datetime import datetime
from pypdf import PdfReader 


# Parse command line arguments
parser = argparse.ArgumentParser(description="Research Assistant MCP Server")
parser.add_argument(
    "--workspace_directory", default=os.path.expanduser("~/Downloads/pdfs"))
parser.add_argument("--limit_text", default=-1)

args = parser.parse_args()

# Initialize server
mcp = FastMCP("ra-2")

# In-memory index of registered resources for quick lookup/search
# Key: URI, Value: dict(name, path, size, mtime, pages)
RESOURCE_INDEX: dict[str, dict] = {}


@mcp.tool()
def obtain_resource_content(path: str) -> str:
    """Obtain the text content of a file resource by its path."""
    file = Path(path)
    root = Path(args.workspace_directory).expanduser().resolve()
    # resolve path within root
    if not file.is_absolute():
        path_obj = root.joinpath(file).resolve()
    if not path_obj.exists():
        return f"File not found: {path}"
    if not path_obj.is_file():
        return f"Path is not a file: {path}"

    try:
        if path.strip().lower().endswith('.pdf'):
            with path_obj.open("rb") as f:
                reader = PdfReader(f)
                content = []
                for page in reader.pages:
                    try:
                        text = page.extract_text()
                        if text:
                            limit = int(args.limit_text)
                            content.append(text[:limit] if limit > 0 else text)
                    except Exception:
                        continue
            return f"Contents of {path}:\n" + "\n".join(content)
        else:
            # assume text file for other extensions
            with path_obj.open("r", encoding="utf-8") as f:
                content = f.read()

            return f"Contents of {path}:\n{content}"

    except UnicodeDecodeError:
        return f"File is not text or uses unsupported encoding: {path}"
    except PermissionError:
        return f"Permission denied reading: {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def locate_relevant_resouces(query: str) -> str:
    """
    Select the single most relevant resource by counting token overlap
    between the query and the FILE NAME (basename). Returns the selected
    resource first, followed by a short ranked list for transparency.
    """

    def tokenize(text: str):
        return set(re.findall(r"[a-z0-9]+", (text or "").lower()))

    q_tokens = tokenize(query.lower())
    if not q_tokens:
        return "Query is empty."

    candidates = []

    if RESOURCE_INDEX:
        for uri, meta in RESOURCE_INDEX.items():
            name = meta.get("name") or uri
            filename = Path(name).name
            overlap = len(q_tokens & tokenize(filename.lower()))
            candidates.append({
                "score": overlap,
                "uri": uri,
                "meta": meta,
                "filename": filename,
            })
    else:
        return f"No resources available to search."


    # Rank: higher overlap -> newer mtime (if available) -> shorter filename -> lex uri
    def sort_key(item):
        meta = item.get("meta", {})
        try:
            mtime = float(meta.get("mtime", 0))
        except Exception:
            mtime = 0.0
        return (-item["score"], -mtime, len(item["filename"]), item["uri"])

    candidates.sort(key=sort_key)

    lines = [
        "Top candidates:",
    ]
    for i, it in enumerate(candidates[:10], start=0):
        meta = it.get("meta", {})
        size = meta.get("size")
        pages = meta.get("pages")
        lines.append(f"{i}- filename: `{it['filename']}` --- (overlap {it['score']})")

    return "\n".join(lines)
    
def register_file_resources(
    workspace: str,
    include_globs: tuple[str, ...] = ("**/*.pdf",),
    ignore_dirs: tuple[str, ...] = (".git", ".svn", "__pycache__"),
    follow_symlinks: bool = False,
    max_bytes: int | None = None,
) -> None:
    """
    Walk `workspace` and register concrete MCP resources for matching files as
    `workspace://<percent-encoded-relative-path>`.
    """
    root = Path(workspace).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Workspace does not exist or is not a directory: {workspace}")

    # Clear and rebuild the index each time
    RESOURCE_INDEX.clear()

    def make_resource(uri: str, target: Path, display_name: str, description: str, mime: str):
        # Define a unique resource function bound to this file & URI
        @mcp.resource(
            uri,
            name=display_name,                    # resource name shown to clients
            description=description,
            mime_type=mime,
        )
        def _file_resource() -> bytes:
            # Return raw bytes so binary files work too
            return target.read_bytes()
        return _file_resource

    # Build a list of candidate paths honoring ignore rules
    candidates: list[Path] = []
    for pattern in include_globs:
        try:
            for p in root.glob(pattern):
                # Enforce directory ignore rules
                parts = set(p.parts)
                if any(ig in parts for ig in ignore_dirs):
                    continue
                if not follow_symlinks and p.is_symlink():
                    continue
                if not p.exists() or not p.is_file():
                    continue
                if max_bytes is not None:
                    try:
                        if p.stat().st_size > max_bytes:
                            continue
                    except Exception:
                        # If we cannot stat, skip conservatively
                        continue
                candidates.append(p)
        except Exception:
            # Ignore malformed patterns or traversal errors
            continue

    # Deterministic ordering
    candidates.sort(key=lambda x: x.as_posix())

    for p in candidates:
        try:
            rel = p.relative_to(root).as_posix()        # posix-style path
            uri = f"workspace://{quote(rel, safe='/')}" # keep slashes, encode spaces, etc.

            size = p.stat().st_size
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            mime, _ = mimetypes.guess_type(p.name)
            mime = mime or "application/pdf"  # default to PDF since we target PDFs by default

            desc_bits = [p.name]
            description = " | ".join(desc_bits)

            # Use relative path as the display name to disambiguate duplicates
            display_name = rel

            make_resource(uri, p, display_name, description, mime)

            # Populate index for later search
            RESOURCE_INDEX[uri] = {
                "name": display_name,
                "path": str(p),
                "size": size,
                "mtime": mtime.timestamp(),
                "mime": mime,
            }
        except PermissionError:
            # Skip unreadable files, keep going
            continue
        except Exception:
            # Never let a single bad file break registration
            continue

if __name__ == "__main__":
    print("Starting Research Assistant MCP Server...")
    print(args)
    
    # Register workspace files as MCP resources
    register_file_resources(args.workspace_directory)

    # Run the server
    mcp.run()
