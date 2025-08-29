#!/usr/bin/env python3

import chromadb
import os

def test_chromadb_connection():
    """Test ChromaDB connection and query functionality."""
    
    chroma_db_path = "/Users/hanisaf/Projects/mcp_demo/pdfs_db"
    
    try:
        # Initialize ChromaDB client (v1.0.20 API)
        client = chromadb.PersistentClient(path=chroma_db_path)
        
        print(f"Connected to ChromaDB at: {chroma_db_path}")
        
        # List collections
        collections = client.list_collections()
        print(f"Found {len(collections)} collections:")
        
        for collection in collections:
            print(f"  - {collection.name} (count: {collection.count()})")
            
            # Test a sample query
            if collection.count() > 0:
                results = collection.query(
                    query_texts=["research community innovation"],
                    n_results=3
                )
                
                print(f"Sample query results for '{collection.name}':")
                if results['documents'] and results['documents'][0]:
                    for i, (doc_id, distance, metadata) in enumerate(zip(
                        results['ids'][0], 
                        results['distances'][0], 
                        results['metadatas'][0] if results['metadatas'] else []
                    )):
                        filename = metadata.get('filename', doc_id) if metadata else doc_id
                        similarity = 1.0 - distance
                        print(f"    {i+1}. {filename} (similarity: {similarity:.3f})")
        
        # If no collections found, try to get collection by name
        if not collections:
            try:
                collection = client.get_collection("references")
                print(f"Found collection by name: {collection.name} (count: {collection.count()})")
            except Exception as e:
                print(f"Could not get collection 'references': {e}")
                # Try to list all available collections with different method
                try:
                    all_collections = client.list_collections()
                    print(f"All collections: {[c.name for c in all_collections]}")
                except Exception as e2:
                    print(f"Error listing collections: {e2}")
                
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_chromadb_connection()
