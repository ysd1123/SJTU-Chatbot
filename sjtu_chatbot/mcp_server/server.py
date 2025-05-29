"""
MCP 服务器模块
该模块提供 MCP (Model Context Protocol) 服务器功能，
完全符合 MCP Streamable HTTP 规范实现。
"""
import os
import logging
import importlib
import pkgutil
import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import functools
import inspect

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .jaccount_login import JAccountLoginManager

# 配置日志
logger = logging.getLogger(__name__)

class SJTUContext:
    """SJTU 上下文类，提供 jAccount 登录状态和会话访问"""
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id
        self._jaccount = JAccountLoginManager.get_instance()
    
    def is_logged_in(self) -> bool:
        """检查用户是否已登录 jAccount"""
        return self._jaccount.is_logged_in()
    
    def get_username(self) -> Optional[str]:
        """获取当前登录的 jAccount 用户名"""
        if self.is_logged_in():
            # TODO: 实现用户名获取功能
            return None
        return None
    
    @property
    def session(self):
        """获取 jAccount 会话"""
        return self._jaccount.session

def register_tool(name: str = None, description: str = None, require_login: bool = True):
    """
    工具注册装饰器
    
    参数:
        name: 工具名称
        description: 工具描述
        require_login: 是否需要登录
    """
    def decorator(func):
        # 获取函数名和文档
        func_name = name or func.__name__
        func_doc = description or func.__doc__ or ""
        
        # 创建包装函数，处理登录检查
        @functools.wraps(func)
        def wrapper(context: SJTUContext = None, *args, **kwargs):
            if context is None:
                context = SJTUContext()
            if require_login and not context.is_logged_in():
                raise ValueError(f"工具 {func_name} 需要 jAccount 登录才能使用")
            return func(context, *args, **kwargs)
        '''
        def wrapper(context: SJTUContext = None):
            # 创建上下文（如果没有提供）
            if context is None:
                context = SJTUContext()
                
            # 检查登录状态
            if require_login and not context.is_logged_in():
                raise ValueError(f"工具 {func_name} 需要 jAccount 登录才能使用")
            
            # 执行原始函数
            return func(context)
        '''
        
        # 将工具信息存储在函数上
        wrapper._tool_info = {
            'name': func_name,
            'description': func_doc,
            'require_login': require_login,
            'original_func': func
        }
        
        return wrapper
    return decorator

class MCPStreamableHTTPServer:
    """符合 MCP Streamable HTTP 规范的服务器实现"""
    
    def __init__(self, name: str = "SJTU-Chatbot MCP Server"):
        self.name = name
        self.app = FastAPI(title=name)
        self.sessions = {}  # session_id -> session_data
        self.tools = {}     # tool_name -> tool_function
        
        # 初始化 jAccount 登录管理器
        self.jaccount_login = JAccountLoginManager.get_instance()
        
        # 配置CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 注册路由
        self._setup_routes()
        
        # 自动扫描并注册工具
        self._scan_and_register_tools()
        
        logger.info(f"MCP 服务器已初始化，名称: {name}")
    
    def _setup_routes(self):
        """设置路由，完全符合 MCP Streamable HTTP 规范"""
        
        @self.app.post("/mcp")
        @self.app.post("/mcp/") 
        async def handle_post(request: Request):
            return await self._handle_mcp_request(request)
        
        @self.app.get("/mcp")
        @self.app.get("/mcp/")
        async def handle_get(request: Request):
            return await self._handle_mcp_get(request)
    
    async def _handle_mcp_request(self, request: Request):
        """处理 POST 请求 - 符合 MCP 规范"""
        try:
            # 检查 Accept 头
            accept_header = request.headers.get("accept", "")
            if "application/json" not in accept_header and "text/event-stream" not in accept_header:
                return JSONResponse(
                    status_code=406,
                    content={
                        "jsonrpc": "2.0",
                        "id": "server-error",
                        "error": {
                            "code": -32600,
                            "message": "Not Acceptable: Client must accept both application/json and text/event-stream"
                        }
                    },
                    headers={"Content-Type": "application/json"}
                )
            
            # 解析请求体
            try:
                body = await request.body()
                if not body:
                    raise ValueError("Empty request body")
                
                data = json.loads(body.decode('utf-8'))
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={
                        "jsonrpc": "2.0",
                        "id": "server-error", 
                        "error": {
                            "code": -32700,
                            "message": f"Parse error: {str(e)}"
                        }
                    },
                    headers={"Content-Type": "application/json"}
                )
            
            # 处理 JSON-RPC 请求
            response = await self._process_jsonrpc_request(data, request)
            
            # 如果响应为None（通知），返回202 Accepted
            if response is None:
                return JSONResponse(
                    status_code=202,
                    content={},
                    headers={"Content-Type": "application/json"}
                )
            
            # 检查是否需要设置session ID头
            session_id = getattr(request, '_session_id', None)
            extra_headers = {}
            if session_id:
                extra_headers["Mcp-Session-Id"] = session_id
            
            # 根据 Accept 头决定响应格式
            # 优先返回JSON响应以兼容更多客户端（如Dify插件）
            # 只有当客户端明确只接受SSE流时才返回SSE
            if "application/json" in accept_header:
                # 返回 JSON（优先选择）
                return JSONResponse(
                    content=response,
                    headers={
                        "Content-Type": "application/json",
                        **extra_headers
                    }
                )
            elif "text/event-stream" in accept_header:
                # 返回 SSE 流（仅当不支持JSON时）
                return StreamingResponse(
                    self._create_sse_response(response),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        **extra_headers
                    }
                )
            else:
                # 这种情况理论上不会发生，因为我们在上面已经检查过Accept头
                return JSONResponse(
                    content=response,
                    headers={
                        "Content-Type": "application/json",
                        **extra_headers
                    }
                )
                
        except Exception as e:
            logger.error(f"处理MCP请求时出错: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "id": "server-error",
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                },
                headers={"Content-Type": "application/json"}
            )
    
    async def _handle_mcp_get(self, request: Request):
        """处理 GET 请求 - 用于 SSE 流"""
        accept_header = request.headers.get("accept", "")
        
        if "text/event-stream" not in accept_header:
            return JSONResponse(
                status_code=405,
                content={
                    "jsonrpc": "2.0",
                    "id": "server-error",
                    "error": {
                        "code": -32601,
                        "message": "Method Not Allowed: GET requires Accept: text/event-stream"
                    }
                },
                headers={"Content-Type": "application/json"}
            )
        
        # 返回 SSE 流用于服务器推送
        return StreamingResponse(
            self._create_keepalive_sse_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    async def _process_jsonrpc_request(self, data: dict, request: Request) -> Optional[dict]:
        """处理 JSON-RPC 请求和通知"""
        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")
        
        # 检查是否是通知（没有id字段）
        is_notification = request_id is None
        
        try:
            # 处理请求方法
            if method == "initialize":
                if is_notification:
                    logger.warning("initialize 方法不应该作为通知发送")
                    return None
                return await self._handle_initialize(params, request_id, request)
            
            elif method == "tools/list":
                if is_notification:
                    logger.warning("tools/list 方法不应该作为通知发送")
                    return None
                return await self._handle_tools_list(params, request_id, request)
            
            elif method == "tools/call":
                if is_notification:
                    logger.warning("tools/call 方法不应该作为通知发送")
                    return None
                return await self._handle_tools_call(params, request_id, request)
            
            # 处理通知方法
            elif method == "notifications/initialized":
                # 客户端通知服务器初始化已完成
                logger.info("客户端初始化完成通知")
                return None  # 通知不需要响应
            
            elif method.startswith("notifications/"):
                # 其他通知方法
                logger.info(f"收到通知: {method}")
                return None  # 通知不需要响应
            
            else:
                # 未知方法
                if is_notification:
                    # 对于未知的通知，静默忽略（符合JSON-RPC规范）
                    logger.warning(f"未知通知方法: {method}")
                    return None
                else:
                    # 对于未知的请求，返回错误
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    
        except Exception as e:
            logger.error(f"处理方法 {method} 时出错: {e}")
            
            if is_notification:
                # 对于通知的错误，不返回响应
                return None
            else:
                # 对于请求的错误，返回错误响应
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
    
    async def _handle_initialize(self, params: dict, request_id: str, request: Request) -> dict:
        """处理初始化请求"""
        # 创建新会话
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "protocol_version": params.get("protocolVersion", "2024-11-05"),
            "client_info": params.get("clientInfo", {}),
            "capabilities": params.get("capabilities", {}),
            "created_at": asyncio.get_event_loop().time()
        }
        
        # 设置 session ID，用于在响应头中返回
        request._session_id = session_id
        
        # 构造响应
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "experimental": {},
                    "prompts": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": self.name,
                    "version": "1.0.0"
                }
            }
        }
        
        return response
    
    async def _handle_tools_list(self, params: dict, request_id: str, request: Request) -> dict:
        """处理工具列表请求"""
        # 验证 session（可选，但推荐）
        session_id = request.headers.get("mcp-session-id")
        if session_id and session_id not in self.sessions:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32600,
                    "message": "Bad Request: Invalid session ID"
                }
            }
        
        # 构造工具列表
        tools = []
        for tool_name, tool_func in self.tools.items():
            if hasattr(tool_func, '_tool_info'):
                info = tool_func._tool_info
                tools.append({
                    "name": info['name'],
                    "description": info['description'],
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                })
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
    
    async def _handle_tools_call(self, params: dict, request_id: str, request: Request) -> dict:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Tool not found: {tool_name}"
                }
            }
        
        try:
            # 创建上下文
            session_id = request.headers.get("mcp-session-id")
            context = SJTUContext(session_id)
            
            # 调用工具
            # tool_func = self.tools[tool_name]
            # result = tool_func(context)
            tool_func = self.tools[tool_name]
            
            # 确保结果是字符串
            if not isinstance(result, str):
                result = json.dumps(result, ensure_ascii=False, indent=2)
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": result
                        }
                    ]
                }
            }
            
        except Exception as e:
            logger.error(f"工具调用失败 {tool_name}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Tool execution failed: {str(e)}"
                }
            }
    
    async def _create_sse_response(self, response_data: dict):
        """创建 SSE 响应流"""
        # 发送数据
        yield f"event: message\n"
        yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
        
        # 可选：发送完成事件
        yield f"event: done\n"
        yield f"data: {{}}\n\n"
    
    async def _create_keepalive_sse_stream(self):
        """创建保持连接的 SSE 流"""
        try:
            while True:
                yield f"event: ping\n"
                yield f"data: {{}}\n\n"
                await asyncio.sleep(30)  # 每30秒发送ping
        except Exception:
            # 客户端断开连接
            pass
    
    def _scan_and_register_tools(self) -> None:
        """自动扫描并注册工具模块"""
        try:
            # 导入工具包
            import sjtu_chatbot.tools
            
            # 获取工具包路径
            tools_path = os.path.dirname(sjtu_chatbot.tools.__file__)
            
            # 扫描工具包下的所有模块
            for _, module_name, _ in pkgutil.iter_modules([tools_path]):
                try:
                    # 导入模块
                    module = importlib.import_module(f"sjtu_chatbot.tools.{module_name}")
                    logger.info(f"已加载工具模块: sjtu_chatbot.tools.{module_name}")
                    
                    # 扫描模块中的所有函数，查找带有 _tool_info 的函数
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if hasattr(attr, '_tool_info'):
                            tool_info = attr._tool_info
                            tool_name = tool_info['name']
                            
                            # 注册工具
                            self.tools[tool_name] = attr
                            logger.info(f"已注册工具: {tool_name}")
                            
                except Exception as e:
                    logger.error(f"加载工具模块 sjtu_chatbot.tools.{module_name} 时出错: {e}")
        except Exception as e:
            logger.error(f"扫描工具模块时出错: {e}")
    
    def run(self, host: str = "0.0.0.0", port: int = 1896):
        """启动服务器"""
        logger.info(f"启动 MCP Streamable HTTP 服务器: http://{host}:{port}/mcp")
        uvicorn.run(self.app, host=host, port=port, log_level="info")

def create_mcp_server(config_path: Optional[Union[str, Path]] = None) -> MCPStreamableHTTPServer:
    """
    创建 MCP 服务器实例
    
    参数:
        config_path: jAccount 配置文件路径，如果为 None 则使用默认路径
        
    返回:
        MCPStreamableHTTPServer 实例
    """
    # 初始化 jAccount 登录管理器
    JAccountLoginManager.get_instance(config_path)
    
    # 创建服务器实例
    server = MCPStreamableHTTPServer()
    
    return server

def get_context() -> SJTUContext:
    """
    获取当前请求的上下文
    
    返回:
        SJTUContext 实例
    """
    return SJTUContext()

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 创建并启动服务器
    server = create_mcp_server()
    server.run(host="0.0.0.0", port=1896)
