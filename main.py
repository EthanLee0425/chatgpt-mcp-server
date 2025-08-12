#!/usr/bin/env python3
"""
官方 FastMCP 範例測試版本
模擬 Vector Store 行為以測試 ChatGPT 連接
"""

import logging
import os
from typing import Dict, List, Any

from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 模擬文件數據（替代 Vector Store）
MOCK_DOCUMENTS = [
    {
        "file_id": "file-1",
        "filename": "User Manual.pdf",
        "content": "This is a comprehensive user manual for the application. It covers installation, configuration, and basic usage. The manual includes step-by-step instructions for new users and troubleshooting guides for common issues."
    },
    {
        "file_id": "file-2", 
        "filename": "API Documentation.pdf",
        "content": "Complete API documentation including endpoints, authentication, rate limits, and example requests. This document explains how to integrate with our REST API and includes code samples in multiple programming languages."
    },
    {
        "file_id": "file-3",
        "filename": "Security Guidelines.pdf", 
        "content": "Security best practices and guidelines for application deployment. Topics include authentication, authorization, data encryption, secure communication protocols, and compliance requirements."
    },
    {
        "file_id": "file-4",
        "filename": "Troubleshooting Guide.pdf",
        "content": "Common problems and solutions for application issues. Includes performance optimization tips, debugging techniques, error code explanations, and contact information for technical support."
    }
]

server_instructions = """
This MCP server provides search and document retrieval capabilities
for chat and deep research connectors. Use the search tool to find relevant documents
based on keywords, then use the fetch tool to retrieve complete
document content with citations.
"""

def create_server():
    """Create and configure the MCP server with search and fetch tools."""

    # Initialize the FastMCP server (官方範例的完全相同初始化)
    mcp = FastMCP(name="Official Sample Test Server",
                  instructions=server_instructions)

    @mcp.tool()
    async def search(query: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for documents using mock data (模擬 Vector Store 搜尋)

        This tool searches through mock documents to find semantically relevant matches.
        Returns a list of search results with basic information. Use the fetch tool to get
        complete document content.

        Args:
            query: Search query string. Natural language queries work best for semantic search.

        Returns:
            Dictionary with 'results' key containing list of matching documents.
            Each result includes id, title, text snippet, and optional URL.
        """
        if not query or not query.strip():
            return {"results": []}

        logger.info(f"Searching mock documents for query: '{query}'")
        
        # 模擬 Vector Store 搜尋邏輯
        query_lower = query.lower()
        results = []

        for doc in MOCK_DOCUMENTS:
            # 簡單的關鍵字匹配（模擬語意搜尋）
            if (query_lower in doc["content"].lower() or 
                query_lower in doc["filename"].lower()):
                
                # 創建文本片段（與官方範例格式完全相同）
                text_snippet = doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"]
                
                result = {
                    "id": doc["file_id"],
                    "title": doc["filename"],
                    "text": text_snippet,
                    "url": f"https://platform.openai.com/storage/files/{doc['file_id']}"
                }
                
                results.append(result)

        logger.info(f"Mock search returned {len(results)} results")
        return {"results": results}

    @mcp.tool()
    async def fetch(id: str) -> Dict[str, Any]:
        """
        Retrieve complete document content by ID (模擬 Vector Store 檔案檢索)

        This tool fetches the full document content from mock data. Use this after finding
        relevant documents with the search tool to get complete information for analysis and proper citation.

        Args:
            id: File ID from mock documents (file-xxx) or document ID

        Returns:
            Complete document with id, title, full text content, optional URL, and metadata

        Raises:
            ValueError: If the specified ID is not found
        """
        if not id:
            raise ValueError("Document ID is required")

        logger.info(f"Fetching content from mock data for file ID: {id}")

        # 在模擬文件中尋找
        doc = None
        for mock_doc in MOCK_DOCUMENTS:
            if mock_doc["file_id"] == id:
                doc = mock_doc
                break

        if not doc:
            raise ValueError(f"Document not found with ID: {id}")

        # 與官方範例完全相同的回應格式
        result = {
            "id": id,
            "title": doc["filename"],
            "text": doc["content"],
            "url": f"https://platform.openai.com/storage/files/{id}",
            "metadata": {
                "document_type": "mock_document",
                "source": "test_data",
                "language": "en"
            }
        }

        logger.info(f"Fetched mock document: {id}")
        return result

    return mcp

def main():
    """Main function to start the MCP server."""
    
    logger.info("Using mock documents (no API key required)")

    # Create the MCP server (與官方範例完全相同)
    server = create_server()

    # Railway deployment configuration
    port = int(os.environ.get("PORT", 8000))
    
    # Configure and start the server (與官方範例完全相同)
    logger.info(f"Starting Official Sample Test MCP Server on 0.0.0.0:{port}")
    logger.info("Server will be accessible via SSE transport")
    logger.info("Ready for ChatGPT integration!")

    try:
        # Use FastMCP's built-in run method with SSE transport (官方範例完全相同)
        server.run(transport="sse", host="0.0.0.0", port=port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == "__main__":
    main()