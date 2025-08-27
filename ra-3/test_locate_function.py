#!/usr/bin/env python3

import sys
import os
sys.path.append('server')

# Import the main module to test the function
from main import initialize_chromadb, locate_relevant_resources, args

def test_locate_function():
    """Test the locate_relevant_resources function."""
    
    # Set the chroma_db_path
    args.chroma_db_path = "/Users/hanisaf/Projects/mcp_demo/pdfs_db"
    
    # Initialize ChromaDB
    initialize_chromadb()
    
    # Test queries
    test_queries = [
        "research community innovation",
        "online communities",
        "knowledge contribution",
        "governance"
    ]
    
    for query in test_queries:
        print(f"\n=== Query: '{query}' ===")
        result = locate_relevant_resources(query)
        print(result)

if __name__ == "__main__":
    test_locate_function()
