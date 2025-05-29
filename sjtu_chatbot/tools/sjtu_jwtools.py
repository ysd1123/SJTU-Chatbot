from ..mcp_server.server import register_tool, SJTUContext
import logging
import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://jw.sjtu.edu.cn"  # placeholder base url

@register_tool(
    name="sjtu_jw_request",
    description="与教务系统交互的通用请求接口（移植自 SjtuJwTool.cs）",
    require_login=True,
)
def sjtu_jw_request(context: SJTUContext, path: str) -> dict:
    """访问教务系统的指定接口并返回 JSON 数据

    Args:
        context: MCP 上下文，提供已认证的 jAccount 会话
        path: 教务系统相对路径，如 '/api/student/lesson'

    Returns:
        成功时返回 ``{"success": True, "data": ...}``，失败时返回 ``{"success": False, "error": ...}``
    """
    if not context.is_logged_in():
        return {"success": False, "error": "用户未登录，请先登录 jAccount"}

    url = BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    session = context.session

    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        try:
            data = resp.json()
        except ValueError:
            data = resp.text
        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"访问教务系统失败: {e}")
        return {"success": False, "error": str(e)}
