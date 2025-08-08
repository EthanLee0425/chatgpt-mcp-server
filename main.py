#!/usr/bin/env python3
"""
Railway.app Deployment Version
Optimized for cloud deployment with Railway
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
import sqlite3
import os

app = FastAPI(
    title="ChatGPT MCP Server",
    description="User Management MCP Server for ChatGPT integration",
    version="1.0.0"
)

# Enable CORS for ChatGPT integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Database model
class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

# Simple database class for cloud deployment
class CloudDatabase:
    def __init__(self, db_path: str = "cloud_users.db"):
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

    def update_user(self, user_id: int, user: User) -> Optional[User]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (user.name, user.email, user_id)
            )
            if cursor.rowcount > 0:
                conn.commit()
                user.id = user_id
                return user
            return None

    def delete_user(self, user_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            success = cursor.rowcount > 0
            if success:
                conn.commit()
            return success

# Global database instance
db = CloudDatabase()

# Request/Response models
class MCPToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]

class MCPResponse(BaseModel):
    result: Any = None
    error: str = None

# Tool execution functions
async def execute_search(arguments: dict) -> str:
    """Execute search tool"""
    query = arguments.get("query", "").lower()
    limit = arguments.get("limit", 10)
    
    users = db.get_users()
    results = []
    
    for user in users:
        if query in user.name.lower() or query in user.email.lower():
            results.append(user)
        if len(results) >= limit:
            break
    
    if not results:
        return f"No users found for: {query}"
    
    response = f"Found {len(results)} users matching '{query}':\n"
    for user in results:
        response += f"- ID: {user.id}, Name: {user.name}, Email: {user.email}\n"
    
    return response

async def execute_fetch(arguments: dict) -> str:
    """Execute fetch tool"""
    identifier = arguments["identifier"]
    id_type = arguments["type"]
    
    if id_type == "id":
        try:
            user_id = int(identifier)
            user = db.get_user(user_id)
        except ValueError:
            return f"Invalid ID: {identifier}"
    elif id_type == "email":
        users = db.get_users()
        user = None
        for u in users:
            if u.email.lower() == identifier.lower():
                user = u
                break
    
    if user:
        return f"User Details:\nID: {user.id}\nName: {user.name}\nEmail: {user.email}"
    else:
        return f"User not found: {identifier}"

# API endpoints
@app.get("/")
async def root():
    return {
        "name": "ChatGPT MCP Server",
        "version": "1.0.0",
        "status": "running",
        "description": "User Management MCP Server for ChatGPT",
        "endpoints": {
            "tools": "/tools",
            "call": "/call", 
            "health": "/health",
            "docs": "/docs"
        },
        "deployment": "Railway Cloud"
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
            "environment": "production"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e)
        }

@app.get("/capabilities")
async def capabilities():
    """MCP server capabilities endpoint"""
    return {
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False,
            "logging": False
        },
        "serverInfo": {
            "name": "ChatGPT MCP Server",
            "version": "1.0.0",
            "protocolVersion": "2024-11-05"
        },
        "instructions": "This server provides user management tools for ChatGPT integration"
    }

@app.get("/tools")
async def list_tools():
    """List all available MCP tools"""
    tools = [
        {
            "name": "search",
            "description": "Search users by name or email (REQUIRED for ChatGPT)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results", "default": 10}
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch",
            "description": "Fetch user details by ID or email (REQUIRED for ChatGPT)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "User ID or email"},
                    "type": {"type": "string", "enum": ["id", "email"], "description": "Identifier type"}
                },
                "required": ["identifier", "type"]
            }
        },
        {
            "name": "create_user",
            "description": "Create a new user",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "User name"},
                    "email": {"type": "string", "description": "User email"}
                },
                "required": ["name", "email"]
            }
        },
        {
            "name": "list_users",
            "description": "List all users",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max users", "default": 50}
                }
            }
        },
        {
            "name": "get_user",
            "description": "Get user by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"}
                },
                "required": ["user_id"]
            }
        },
        {
            "name": "update_user",
            "description": "Update user information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "name": {"type": "string", "description": "New name"},
                    "email": {"type": "string", "description": "New email"}
                },
                "required": ["user_id", "name", "email"]
            }
        },
        {
            "name": "delete_user",
            "description": "Delete a user",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"}
                },
                "required": ["user_id"]
            }
        }
    ]
    
    return {"tools": tools}

@app.post("/call")
async def call_tool(request: MCPToolCall) -> MCPResponse:
    """Execute MCP tool call"""
    try:
        name = request.name
        arguments = request.arguments
        
        if name == "search":
            result = await execute_search(arguments)
        elif name == "fetch":
            result = await execute_fetch(arguments)
        elif name == "create_user":
            user = User(**arguments)
            created = db.create_user(user)
            result = f"Created user: ID={created.id}, Name={created.name}, Email={created.email}"
        elif name == "list_users":
            limit = arguments.get("limit", 50)
            users = db.get_users()
            if not users:
                result = "No users in database"
            else:
                limited = users[:limit]
                result = f"Users ({len(limited)} of {len(users)}):\n"
                for user in limited:
                    result += f"ID: {user.id}, Name: {user.name}, Email: {user.email}\n"
        elif name == "get_user":
            user_id = arguments["user_id"]
            user = db.get_user(user_id)
            if user:
                result = f"User: ID={user.id}, Name={user.name}, Email={user.email}"
            else:
                result = f"User not found: ID={user_id}"
        elif name == "update_user":
            user_id = arguments["user_id"]
            user_data = User(name=arguments["name"], email=arguments["email"])
            updated = db.update_user(user_id, user_data)
            if updated:
                result = f"Updated: ID={updated.id}, Name={updated.name}, Email={updated.email}"
            else:
                result = f"User not found: ID={user_id}"
        elif name == "delete_user":
            user_id = arguments["user_id"]
            success = db.delete_user(user_id)
            if success:
                result = f"Deleted user: ID={user_id}"
            else:
                result = f"User not found: ID={user_id}"
        else:
            return MCPResponse(error=f"Unknown tool: {name}")
            
        return MCPResponse(result=result)
        
    except Exception as e:
        return MCPResponse(error=str(e))

# Add sample data on startup
@app.on_event("startup")
async def startup_event():
    """Initialize with sample data"""
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
                    
            print(f"[SUCCESS] Initialized with {len(sample_users)} sample users")
        else:
            print(f"[INFO] Database has {len(users)} existing users")
    except Exception as e:
        print(f"[WARNING] Startup warning: {e}")

# Railway deployment configuration
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    print("[START] Starting ChatGPT MCP Server for Railway deployment...")
    print(f"[PORT] Port: {port}")
    print("[SUCCESS] Ready for ChatGPT integration!")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )