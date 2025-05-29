from ..mcp_server.server import register_tool, SJTUContext
import logging
import requests

logger = logging.getLogger(__name__)

MAIL_BASE = "https://mail.sjtu.edu.cn"  # placeholder base url

@register_tool(
    name="sjtu_mail_inbox",
    description="获取交大邮箱首页信息（移植自 SjtuMailTool.cs）",
    require_login=True,
)
def sjtu_mail_inbox(context: SJTUContext) -> dict:
    """从交大邮箱获取邮件列表

    Args:
        context: MCP 上下文

    Returns:
        成功时返回 ``{"success": True, "data": ...}``
    """
    if not context.is_logged_in():
        return {"success": False, "error": "用户未登录，请先登录 jAccount"}

    session = context.session
    try:
        resp = session.get(MAIL_BASE, timeout=30)
        resp.raise_for_status()
        content = resp.text
        return {"success": True, "data": content}
    except Exception as e:
        logger.error(f"访问邮件系统失败: {e}")
        return {"success": False, "error": str(e)}
