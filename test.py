#!/usr/bin/env python3
"""
SJTU-Chatbot Demo 测试脚本

该脚本用于测试 SJTU-Chatbot 的基本功能，包括 MCP 服务器启动、工具加载和 jAccount 登录。
"""

import os
import sys
import time
import logging
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.absolute()))

# 导入 MCP 服务器模块
from sjtu_chatbot.mcp_server import create_mcp_server, JAccountLoginManager


def main():
    """主函数"""
    # 配置命令行参数
    parser = argparse.ArgumentParser(description="SJTU-Chatbot Demo 测试脚本")
    parser.add_argument("--port", type=int, default=1896, help="MCP 服务器端口，默认为 1896")
    parser.add_argument("--debug", action="store_true", help="启用调试日志")
    parser.add_argument("--no-login", action="store_true", help="跳过 jAccount 登录检查（仅在已有有效会话时可用）")
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 检查端口是否被占用
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('0.0.0.0', args.port))
        s.close()
    except socket.error as e:
        print(f"错误: 端口 {args.port} 已被占用，请关闭占用该端口的程序或使用其他端口。")
        print(f"您可以使用 --port 参数指定其他端口，例如: python test.py --port 1897")
        print(f"技术细节: {e}")
        sys.exit(1)
    
    # 创建 MCP 服务器
    mcp_server = create_mcp_server()
    
    # [TEST.PY 特有] 在启动服务器前确保 jAccount 已登录
    print("\n[jAccount 登录检查] 检查登录状态...")
    jaccount_login = JAccountLoginManager.get_instance()
    
    if args.no_login:
        print("[jAccount 登录] 已跳过登录检查（--no-login 模式）")
        if not jaccount_login.is_logged_in():
            print("[jAccount 警告] 当前会话无效，工具可能无法访问受限资源")
    else:
        if not jaccount_login.ensure_logged_in():
            print("[jAccount 登录] 登录失败或取消，程序退出")
            sys.exit(1)
        
        print("[jAccount 登录] 登录成功，启动会话监控...")
        
        # 启动会话监控，确保在服务器运行期间保持登录状态
        def login_callback():
            print("[jAccount 会话] 会话已失效，尝试重新登录")
            if not jaccount_login.ensure_logged_in():
                print("[jAccount 会话] 重新登录失败")
        
        jaccount_login.start_session_monitor(login_callback)
    
    # 显示已注册的工具
    tools = mcp_server.tools
    print("已注册的工具:")
    for tool_name, tool_func in tools.items():
        if hasattr(tool_func, '_tool_info'):
            info = tool_func._tool_info
            print(f"  - {info['name']}: {info['description']}")
    
    # 启动 MCP 服务器（在主线程中）
    try:
        print(f"\n[MCP 服务器] 正在启动，端点: http://0.0.0.0:{args.port}/mcp")
        print(f"[MCP 服务器] 浏览器测试: http://localhost:{args.port}/mcp")
        print(f"[MCP 服务器] Docker配置: http://host.docker.internal:{args.port}/mcp")
        
        # 启动服务器
        mcp_server.run(host="0.0.0.0", port=args.port)
    except KeyboardInterrupt:
        print("\n[MCP 服务器] 已被用户中断")
    except Exception as e:
        print(f"\n[MCP 服务器] 启动失败: {e}")
    finally:
        # 停止会话监控（如果启动了）
        if not args.no_login:
            jaccount_login.stop_session_monitor()
        print("[MCP 服务器] 已关闭")


if __name__ == "__main__":
    main()
