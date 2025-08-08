#!/usr/bin/env python3
"""
OpenAI-Compliant MCP Server
Based on official OpenAI MCP documentation requirements
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, AsyncGenerator, Optional
import uvicorn
import json
import asyncio
import sqlite3
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database model
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

# Simple database class
class SimpleDatabase:
    def __init__(self, db_path: str = "openai_mcp.db"):
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

    def create_user(self, user: User) -> User:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (user.name, user.email)
            )
            user.id = cursor.lastrowid
            conn.commit()
            return user

    def get_users(self) -> List[User]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM users")
            rows = cursor.fetchall()
            return [User(id=row[0], name=row[1], email=row[2]) for row in rows]

    def get_user(self, user_id: int) -> Optional[User]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return User(id=row[0], name=row[1], email=row[2]) if row else None

app = FastAPI(
    title="OpenAI-Compliant MCP Server",
    description="MCP Server following OpenAI documentation requirements for ChatGPT Deep Research",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = SimpleDatabase("openai_mcp.db")

# MCP Protocol Models
class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPResponse(BaseModel):
    result: Any = None
    error: str = None

# SSE Response formatting for OpenAI compatibility
async def create_sse_response(data: Dict[str, Any]) -> AsyncGenerator[str, None]:
    """Create Server-Sent Events response as required by OpenAI"""
    yield f"data: {json.dumps(data)}\n\n"

@app.get("/")
async def root():
    return {
        "name": "OpenAI-Compliant MCP Server",
        "version": "1.0.0", 
        "status": "ready",
        "protocol": "MCP over SSE",
        "compliance": "OpenAI ChatGPT Deep Research",
        "endpoints": {
            "sse": "/sse/",
            "tools": "/tools",
            "health": "/health"
        },
        "required_tools": ["search", "fetch"],
        "description": "User management MCP server optimized for ChatGPT Deep Research integration"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        users = db.get_users()
        return {
            "status": "healthy",
            "database": "connected",
            "users_count": len(users),
            "compliance": "OpenAI MCP specification",
            "required_tools": ["search", "fetch"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/sse/")
async def sse_endpoint():
    """
    SSE (Server-Sent Events) endpoint as required by OpenAI
    This is the main entry point for ChatGPT Deep Research
    """
    logger.info("SSE endpoint accessed")
    
    async def event_stream():
        # Initial connection message
        welcome_data = {
            "type": "connection",
            "message": "OpenAI MCP Server connected",
            "capabilities": {
                "tools": ["search", "fetch"],
                "protocol": "MCP over SSE",
                "version": "1.0.0"
            }
        }
        
        yield f"data: {json.dumps(welcome_data)}\n\n"
        
        # Keep connection alive
        while True:
            await asyncio.sleep(30)  # Heartbeat every 30 seconds
            heartbeat = {
                "type": "heartbeat",
                "timestamp": asyncio.get_event_loop().time(),
                "status": "alive"
            }
            yield f"data: {json.dumps(heartbeat)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.get("/tools")
async def list_tools():
    """List available tools - focusing on required search and fetch"""
    tools = [
        {
            "name": "search",
            "description": "Search users in the database by name or email (REQUIRED for ChatGPT Deep Research)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "Search query for user name or email"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch", 
            "description": "Fetch detailed user information by ID or email (REQUIRED for ChatGPT Deep Research)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "User ID or email address"
                    },
                    "type": {
                        "type": "string",
                        "enum": ["id", "email"],
                        "description": "Type of identifier"
                    }
                },
                "required": ["identifier", "type"]
            }
        }
    ]
    
    return {
        "tools": tools,
        "server_info": {
            "name": "openai-compliant-mcp-server",
            "version": "1.0.0",
            "compliance": "OpenAI MCP specification"
        }
    }

@app.post("/call")
async def call_tool(request: MCPToolCall) -> MCPResponse:
    """Execute tool calls with OpenAI-compliant responses"""
    try:
        name = request.name
        arguments = request.arguments
        
        logger.info(f"Tool call: {name} with args: {arguments}")
        
        if name == "search":
            query = arguments.get("query", "").lower()
            limit = arguments.get("limit", 10)
            
            # Perform search
            users = db.get_users()
            results = []
            
            for user in users:
                if query in user.name.lower() or query in user.email.lower():
                    results.append({
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "type": "user_record",
                        "relevance": "high" if query in user.name.lower() else "medium"
                    })
                if len(results) >= limit:
                    break
            
            if not results:
                response_text = f"No users found matching query: '{query}'"
            else:
                response_text = f"Found {len(results)} users matching '{query}':\n\n"
                for result in results:
                    response_text += f"[ID] User ID: {result['id']}\n"
                    response_text += f"[NAME] Name: {result['name']}\n"
                    response_text += f"[EMAIL] Email: {result['email']}\n"
                    response_text += f"[RELEVANCE] Relevance: {result['relevance']}\n\n"
            
            return MCPResponse(result=response_text)

        elif name == "fetch":
            identifier = arguments["identifier"]
            id_type = arguments["type"]
            
            logger.info(f"Fetching user: {identifier} (type: {id_type})")
            
            user = None
            if id_type == "id":
                try:
                    user_id = int(identifier)
                    user = db.get_user(user_id)
                except ValueError:
                    return MCPResponse(error=f"Invalid user ID format: {identifier}")
            elif id_type == "email":
                users = db.get_users()
                for u in users:
                    if u.email.lower() == identifier.lower():
                        user = u
                        break
            
            if user:
                detailed_info = f"""
[DETAILS] **User Details**
==================
[ID] **ID**: {user.id}
[NAME] **Name**: {user.name}  
[EMAIL] **Email**: {user.email}
[TYPE] **Record Type**: User Profile
[STATUS] **Status**: Active

**Available Actions**:
- Update user information
- Contact user
- View user history

**Data Source**: Internal User Database
**Last Accessed**: Just now
"""
                return MCPResponse(result=detailed_info)
            else:
                return MCPResponse(error=f"User not found: {identifier}")

        else:
            return MCPResponse(error=f"Unknown tool: {name}. Only 'search' and 'fetch' tools are supported for ChatGPT Deep Research.")

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return MCPResponse(error=f"Execution error: {str(e)}")

# Initialize sample data
@app.on_event("startup")
async def startup_event():
    """Initialize with sample data for testing"""
    try:
        users = db.get_users()
        if len(users) == 0:
            sample_users = [
                User(name="Alice Johnson", email="alice@example.com"),
                User(name="Bob Smith", email="bob@example.com"), 
                User(name="Carol Brown", email="carol@test.com"),
                User(name="David Wilson", email="david@demo.com"),
                User(name="Eva Garcia", email="eva@sample.com"),
                User(name="Frank Miller", email="frank@research.com"),
                User(name="Grace Lee", email="grace@academic.edu"),
                User(name="Henry Zhang", email="henry@company.org")
            ]
            
            for user in sample_users:
                try:
                    db.create_user(user)
                except:
                    pass  # Skip if user already exists
                    
            logger.info(f"Initialized with {len(sample_users)} sample users")
        else:
            logger.info(f"Database has {len(users)} existing users")
            
        logger.info("OpenAI-Compliant MCP Server started successfully")
        logger.info("Required tools available: search, fetch")
        logger.info("SSE endpoint available at: /sse/")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

if __name__ == "__main__":
    print("[START] Starting OpenAI-Compliant MCP Server...")
    print("[TOOLS] Required tools: search, fetch")  
    print("[SSE] SSE endpoint: http://localhost:8001/sse/")
    print("[DOCS] API docs: http://localhost:8001/docs")
    print("[SUCCESS] ChatGPT Deep Research compatible")
    print("-" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
        reload=True
    )