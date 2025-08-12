#!/usr/bin/env python3
"""
FastMCP 相容版本的 MCP 伺服器
基於官方範例改寫，使用自定義資料庫而非 Vector Store
"""

import logging
import os
import asyncio
import json
from typing import Dict, List, Any
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database model
class User(BaseModel):
    id: int = None
    name: str
    email: str

# Database class
class UserDatabase:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL
                )
            """)
            conn.commit()

    def get_users(self) -> List[User]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM users")
            rows = cursor.fetchall()
            return [User(id=row[0], name=row[1], email=row[2]) for row in rows]

    def get_user(self, user_id: int) -> User:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return User(id=row[0], name=row[1], email=row[2]) if row else None

    def create_user(self, user: User) -> User:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (user.name, user.email))
            user.id = cursor.lastrowid
            conn.commit()
            return user

# Global database
db = UserDatabase()

# Initialize with sample data
try:
    users = db.get_users()
    if len(users) == 0:
        sample_users = [
            User(name="Alice Johnson", email="alice@example.com"),
            User(name="Bob Smith", email="bob@example.com"),
            User(name="Carol Brown", email="carol@test.com"),
            User(name="David Wilson", email="david@demo.com"),
            User(name="Eva Garcia", email="eva@sample.com")
        ]
        for user in sample_users:
            try:
                db.create_user(user)
            except:
                pass
        logger.info(f"Initialized with {len(sample_users)} sample users")
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")

# MCP Tools Implementation (模擬 FastMCP 的 @mcp.tool() 裝飾器行為)
async def search(query: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search for users in the database.
    
    Args:
        query: Search query string for user names or email addresses
        
    Returns:
        Dictionary with 'results' key containing list of matching users.
        Each result includes id, title, text snippet, and optional URL.
    """
    if not query or not query.strip():
        return {"results": []}
    
    query = query.lower()
    users = db.get_users()
    results = []
    
    for user in users:
        if query in user.name.lower() or query in user.email.lower():
            result = {
                "id": str(user.id),
                "title": f"User: {user.name}",
                "text": f"User {user.name} with email {user.email}. Contact information and profile details available.",
                "url": f"https://chatgpt-mcp-server-production-d35b.up.railway.app/users/{user.id}"
            }
            results.append(result)
            
        if len(results) >= 10:  # Limit results
            break
    
    logger.info(f"Search for '{query}' returned {len(results)} results")
    return {"results": results}

async def fetch(id: str) -> Dict[str, Any]:
    """
    Retrieve complete user details by unique identifier.
    
    Args:
        id: Unique identifier for the user (user ID or email address)
        
    Returns:
        Complete user profile with id, title, full text content, optional URL, and metadata
    """
    if not id:
        raise ValueError("User ID is required")
    
    user = None
    
    # Try to get by ID first
    if id.isdigit():
        try:
            user_id = int(id)
            user = db.get_user(user_id)
        except ValueError:
            pass
    
    # If not found, try by email
    if not user and "@" in id:
        users = db.get_users()
        for u in users:
            if u.email.lower() == id.lower():
                user = u
                break
    
    if user:
        result = {
            "id": str(user.id),
            "title": f"User Profile: {user.name}",
            "text": f"Complete user profile for {user.name}\n\nContact Information:\n- Email: {user.email}\n- User ID: {user.id}\n\nProfile Status: Active\nAccount Type: Standard User\n\nThis user record contains basic contact and identification information.",
            "url": f"https://chatgpt-mcp-server-production-d35b.up.railway.app/users/{user.id}",
            "metadata": {
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "account_type": "standard",
                "status": "active"
            }
        }
        logger.info(f"Fetched user profile: {id}")
        return result
    else:
        raise ValueError(f"User not found with identifier: {id}")

# FastAPI app setup
app = FastAPI(
    title="FastMCP Compatible Server",
    description="MCP Server compatible with ChatGPT Deep Research",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# MCP SSE Transport (模擬 FastMCP 的 transport="sse" 行為)
@app.get("/sse/")
async def mcp_sse_transport():
    """
    MCP SSE Transport - 模擬 FastMCP 的內建 SSE transport
    這個端點實作了與 ChatGPT 相容的 MCP over SSE 協議
    """
    
    async def mcp_stream():
        # 1. 發送初始化訊息 (類似 FastMCP 的初始化)
        init_response = {
            "jsonrpc": "2.0",
            "id": None,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": "FastMCP Compatible Server",
                    "version": "1.0.0"
                },
                "instructions": "This MCP server provides user management capabilities for ChatGPT integration. Use the search tool to find relevant users based on keywords, then use the fetch tool to retrieve complete user profile information with citations."
            }
        }
        
        yield f"data: {json.dumps(init_response)}\n\n"
        
        # 2. 主要的 message loop (模擬 FastMCP 的 message handling)
        while True:
            await asyncio.sleep(30)
            # 發送 heartbeat
            heartbeat = {
                "jsonrpc": "2.0",
                "method": "notifications/message",
                "params": {"level": "info", "message": "Server heartbeat"}
            }
            yield f"data: {json.dumps(heartbeat)}\n\n"
    
    return StreamingResponse(
        mcp_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

# MCP JSON-RPC endpoints (模擬 FastMCP 的 RPC 處理)
@app.post("/")
async def mcp_jsonrpc(request: Request):
    """
    主要的 MCP JSON-RPC 端點
    模擬 FastMCP 處理 tools/list 和 tools/call 的方式
    """
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        rpc_id = body.get("id")
        
        if method == "tools/list":
            # 返回工具列表 (模擬 FastMCP 自動生成的工具定義)
            tools = [
                {
                    "name": "search",
                    "description": "Search for users in the database. Returns a list of potentially relevant users based on the search query (REQUIRED for ChatGPT Deep Research)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query string for user names or email addresses"
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "fetch",
                    "description": "Retrieve complete user details by unique identifier. Returns full user profile information (REQUIRED for ChatGPT Deep Research)",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Unique identifier for the user (user ID or email address)"
                            }
                        },
                        "required": ["id"]
                    }
                }
            ]
            
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {"tools": tools}
            }
        
        elif method == "tools/call":
            # 執行工具調用 (模擬 FastMCP 的工具執行)
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "search":
                result = await search(**arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": result
                }
            
            elif tool_name == "fetch":
                try:
                    result = await fetch(**arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "result": result
                    }
                except ValueError as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {
                            "code": -1,
                            "message": str(e)
                        }
                    }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }
    
    except Exception as e:
        logger.error(f"JSON-RPC error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {
                "code": -32603,
                "message": "Internal error"
            }
        }

# Health check
@app.get("/")
async def root():
    return {
        "name": "FastMCP Compatible Server",
        "version": "1.0.0", 
        "status": "running",
        "description": "MCP Server compatible with ChatGPT Deep Research (FastMCP style)",
        "sse_endpoint": "/sse/",
        "users_count": len(db.get_users())
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    
    logger.info("Starting FastMCP Compatible MCP Server...")
    logger.info(f"SSE endpoint: http://0.0.0.0:{port}/sse/")
    logger.info("Server ready for ChatGPT integration!")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")