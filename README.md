# MCP Demo - Research Assistant

A demonstration of creating Model Context Protocol (MCP) servers using Python for Claude Desktop integration. This project showcases multiple iterations of a research assistant MCP server that provides access to PDF documents through semantic search and content extraction.

## Overview

This repository contains several MCP server implementations (ra-1, ra-2, ra-3, santa) that demonstrate different approaches to building research assistant tools. The main functionality includes:

- **PDF Resource Management**: Access and read PDF documents from a workspace directory
- **Semantic Search**: Use ChromaDB for vector similarity search to find relevant documents
- **Content Extraction**: Extract text content from PDF files with configurable limits
- **MCP Integration**: Full integration with Claude Desktop through the Model Context Protocol

## Features

### Core Tools
- `obtain_resource_content(path)`: Extract text content from PDF and text files
- `locate_relevant_resources(query)`: Find the most relevant documents using vector similarity search

### Key Capabilities
- Configurable workspace directory for PDF storage
- ChromaDB integration for semantic document search
- Text extraction limit controls for API usage optimization
- Cross-platform compatibility (Windows, macOS, Linux)

## Project Structure

```
mcp_demo/
├── README.md
├── pdfs/                    # Sample PDF documents
├── pdfs_db/                 # ChromaDB vector database
├── ra-1/                    # First iteration of research assistant
├── ra-2/                    # Second iteration
├── ra-3/                    # Latest iteration with ChromaDB integration
│   ├── manifest.json        # MCP server configuration
│   ├── pyproject.toml       # Python project configuration
│   ├── requirements.txt     # Python dependencies
│   └── server/
│       └── main.py         # Main MCP server implementation
└── santa/                   # Additional MCP server example
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd mcp_demo
   ```

2. **Install dependencies** (for ra-3):
   ```bash
   cd ra-3
   pip install -r requirements.txt
   ```

3. **Set up ChromaDB** (optional, for semantic search):
   - The server will automatically connect to existing ChromaDB collections in the specified path
   - Ensure your vector database is populated with document embeddings

## Configuration

The MCP server accepts several configuration parameters:

- `workspace_directory`: Directory containing PDF files (default: `~/Downloads/pdfs`)
- `limit_text`: Character limit per file (-1 for no limit, useful for API rate limits)
- `chroma_db_path`: Path to ChromaDB database directory (default: `~/Downloads/pdfs_db`)

## Usage with Claude Desktop

1. **Configure Claude Desktop** with the MCP server by adding the server configuration to your Claude Desktop settings

2. **Use the tools** in your Claude conversations:
   - Ask Claude to search for relevant documents on a topic
   - Request content from specific PDF files
   - Perform semantic searches across your document collection

## Development Iterations

### ra-1
Basic file access and content extraction functionality.

### ra-2
Enhanced error handling and improved file processing.

### ra-3
Current version featuring:
- ChromaDB integration for semantic search
- Improved resource registration
- Better error handling and logging
- Configurable text limits
- Cross-platform file path handling

## Dependencies

- **mcp**: Model Context Protocol library
- **pypdf**: PDF text extraction
- **chromadb**: Vector database for semantic search
- **trio**: Async I/O framework

## References

- [Anthropic Desktop Extensions](https://www.anthropic.com/engineering/desktop-extensions)
- [Model Context Protocol Quickstart](https://modelcontextprotocol.io/quickstart/server)
- [Claude Desktop Integration](https://docs.anthropic.com/en/docs/build-with-claude/computer-use)

## License

MIT License - See individual project files for specific licensing information.
