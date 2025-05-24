"""
MCP 服务器模块
该模块负责提供 MCP (Model Context Protocol) 服务器功能，
包括工具注册、jAccount 登录集成和 MCP 协议实现。
完全符合 MCP Streamable HTTP 规范实现。
"""
from .jaccount_login import JAccountLogin, JAccountLoginManager
from .server import MCPStreamableHTTPServer, SJTUContext, register_tool, create_mcp_server, get_context

__all__ = [
    "JAccountLogin", 
    "JAccountLoginManager", 
    "MCPStreamableHTTPServer", 
    "SJTUContext", 
    "register_tool", 
    "create_mcp_server", 
    "get_context"
]
