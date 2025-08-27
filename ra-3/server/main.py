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
import chromadb
from chromadb.config import Settings 


# Parse command line arguments
parser = argparse.ArgumentParser(description="Research Assistant MCP Server")
parser.add_argument(
    "--workspace_directory", default=os.path.expanduser("~/Downloads/pdfs"))
parser.add_argument("--limit_text", default=-1)
parser.add_argument(
    "--chroma_db_path", default=os.path.expanduser("~/Projects/mcp_demo/pdfs_db"))

args = parser.parse_args()

# Initialize server
mcp = FastMCP("ra-3")

# Initialize ChromaDB client
chroma_client = None
chroma_collection = None

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
def locate_relevant_resources(query: str) -> str:
    """
    Select the most relevant resources using vector similarity search
    against the ChromaDB collection. Returns ranked results based on
    semantic similarity to the query.
    """
    global chroma_client, chroma_collection
    
    if not query.strip():
        return "Query is empty."
    
    if chroma_collection is None:
        return "ChromaDB collection not available. Please check the database path."
    
    try:
        # Query the ChromaDB collection
        results = chroma_collection.query(
            query_texts=[query],
            n_results=10  # Get top 10 results
        )
        
        if not results['documents'] or not results['documents'][0]:
            return "No relevant documents found in the database."
        
        # Extract results and format them
        documents = results['documents'][0]
        distances = results['distances'][0] if results['distances'] else []
        metadatas = results['metadatas'][0] if results['metadatas'] else []
        ids = results['ids'][0] if results['ids'] else []
        
        lines = ["Top candidates:"]
        
        for i, (doc_id, distance, metadata) in enumerate(zip(ids, distances, metadatas)):
            # Extract filename from metadata or document ID
            filename = metadata.get('filename', doc_id) if metadata else doc_id
            
            # Convert distance to similarity score (lower distance = higher similarity)
            similarity_score = 1.0 - distance if distance is not None else 0.0
            
            lines.append(f"{i}- filename: `{filename}` --- (similarity {similarity_score:.3f})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"
    
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

def initialize_chromadb():
    """Initialize ChromaDB client and collection."""
    global chroma_client, chroma_collection
    
    try:
        # Initialize ChromaDB client with the specified path
        chroma_client = chromadb.PersistentClient(
            path=args.chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get the first available collection (assuming there's one)
        collections = chroma_client.list_collections()
        if collections:
            chroma_collection = collections[0]
            print(f"Connected to ChromaDB collection: {chroma_collection.name}")
        else:
            print("Warning: No collections found in ChromaDB")
            
    except Exception as e:
        print(f"Error initializing ChromaDB: {e}")
        chroma_client = None
        chroma_collection = None

if __name__ == "__main__":
    print("Starting Research Assistant MCP Server...")
    print(args)
    
    # Initialize ChromaDB
    initialize_chromadb()
    
    # Register workspace files as MCP resources
    register_file_resources(args.workspace_directory)

    # Run the server
    mcp.run()
