from dataclasses import dataclass
from typing import Any, List, Optional, Dict
from .base.data_utils import from_str, from_none, from_bool, from_dict, from_int, from_list, from_union, to_class
from ..mcp_server.server import register_tool, SJTUContext
import logging

logger = logging.getLogger(__name__)

@dataclass
class Birthday:
    birth_day: str
    birth_month: str
    birth_year: str

    @staticmethod
    def from_dict(obj: Any) -> 'Birthday':
        assert isinstance(obj, dict)
        birth_day = from_str(obj.get("birthDay"))
        birth_month = from_str(obj.get("birthMonth"))
        birth_year = from_str(obj.get("birthYear"))
        return Birthday(birth_day, birth_month, birth_year)

    def to_dict(self) -> dict:
        result: dict = {}
        result["birthDay"] = from_str(self.birth_day)
        result["birthMonth"] = from_str(self.birth_month)
        result["birthYear"] = from_str(self.birth_year)
        return result


@dataclass
class Major:
    id: str
    name: str

    @staticmethod
    def from_dict(obj: Any) -> 'Major':
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        name = from_str(obj.get("name"))
        return Major(id, name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["name"] = from_str(self.name)
        return result


@dataclass
class OrganizeInfo:
    id: str
    name: str

    @staticmethod
    def from_dict(obj: Any) -> 'OrganizeInfo':
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        name = from_str(obj.get("name"))
        return OrganizeInfo(id, name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["name"] = from_str(self.name)
        return result


@dataclass
class IdentityType:
    id: str
    name: str

    @staticmethod
    def from_dict(obj: Any) -> 'IdentityType':
        assert isinstance(obj, dict)
        id = from_str(obj.get("id"))
        name = from_str(obj.get("name"))
        return IdentityType(id, name)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["name"] = from_str(self.name)
        return result


@dataclass
class Identity:
    kind: str
    is_default: bool
    code: Optional[str]
    user_type: str
    user_type_name: str
    organize: Optional[OrganizeInfo]
    top_organize: Optional[OrganizeInfo]
    mgt_organize: Optional[OrganizeInfo]
    top_mgt_organize: Optional[OrganizeInfo]
    status: str
    expire_date: str
    create_date: int
    update_date: int
    class_no: Optional[str]
    gjm: Optional[str]
    default_optional: bool
    major: Optional[Major]
    admission_date: Optional[str]
    train_level: Optional[str]
    graduate_date: Optional[str]
    top_organizes: Optional[List[OrganizeInfo]]
    photo_url: Optional[str]
    identity_type: Optional[IdentityType]

    @staticmethod
    def from_dict(obj: Any) -> 'Identity':
        assert isinstance(obj, dict)
        
        kind = from_str(obj.get("kind"))
        is_default = from_bool(obj.get("isDefault"))
        code = from_union([from_str, from_none], obj.get("code"))
        user_type = from_str(obj.get("userType"))
        user_type_name = from_str(obj.get("userTypeName"))
        
        # 处理组织信息
        organize = from_union([OrganizeInfo.from_dict, from_none], obj.get("organize"))
        top_organize = from_union([OrganizeInfo.from_dict, from_none], obj.get("topOrganize"))
        mgt_organize = from_union([OrganizeInfo.from_dict, from_none], obj.get("mgtOrganize"))
        top_mgt_organize = from_union([OrganizeInfo.from_dict, from_none], obj.get("topMgtOrganize"))
        
        status = from_str(obj.get("status"))
        expire_date = from_str(obj.get("expireDate"))
        create_date = from_int(obj.get("createDate"))
        update_date = from_int(obj.get("updateDate"))
        
        class_no = from_union([from_str, from_none], obj.get("classNo"))
        gjm = from_union([from_str, from_none], obj.get("gjm"))
        default_optional = from_bool(obj.get("defaultOptional"))
        
        # 处理专业信息
        major = from_union([Major.from_dict, from_none], obj.get("major"))
        
        admission_date = from_union([from_str, from_none], obj.get("admissionDate"))
        train_level = from_union([from_str, from_none], obj.get("trainLevel"))
        graduate_date = from_union([from_str, from_none], obj.get("graduateDate"))
        
        # 处理顶级组织列表
        top_organizes = None
        if obj.get("topOrganizes"):
            top_organizes = from_list(OrganizeInfo.from_dict, obj.get("topOrganizes"))
        
        photo_url = from_union([from_str, from_none], obj.get("photoUrl"))
        
        # 处理身份类型
        identity_type = from_union([IdentityType.from_dict, from_none], obj.get("type"))
        
        return Identity(
            kind, is_default, code, user_type, user_type_name,
            organize, top_organize, mgt_organize, top_mgt_organize,
            status, expire_date, create_date, update_date,
            class_no, gjm, default_optional, major,
            admission_date, train_level, graduate_date,
            top_organizes, photo_url, identity_type
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["kind"] = from_str(self.kind)
        result["isDefault"] = from_bool(self.is_default)
        result["code"] = from_union([from_str, from_none], self.code)
        result["userType"] = from_str(self.user_type)
        result["userTypeName"] = from_str(self.user_type_name)
        result["organize"] = from_union([lambda x: to_class(OrganizeInfo, x), from_none], self.organize)
        result["topOrganize"] = from_union([lambda x: to_class(OrganizeInfo, x), from_none], self.top_organize)
        result["mgtOrganize"] = from_union([lambda x: to_class(OrganizeInfo, x), from_none], self.mgt_organize)
        result["topMgtOrganize"] = from_union([lambda x: to_class(OrganizeInfo, x), from_none], self.top_mgt_organize)
        result["status"] = from_str(self.status)
        result["expireDate"] = from_str(self.expire_date)
        result["createDate"] = from_int(self.create_date)
        result["updateDate"] = from_int(self.update_date)
        result["classNo"] = from_union([from_str, from_none], self.class_no)
        result["gjm"] = from_union([from_str, from_none], self.gjm)
        result["defaultOptional"] = from_bool(self.default_optional)
        result["major"] = from_union([lambda x: to_class(Major, x), from_none], self.major)
        result["admissionDate"] = from_union([from_str, from_none], self.admission_date)
        result["trainLevel"] = from_union([from_str, from_none], self.train_level)
        result["graduateDate"] = from_union([from_str, from_none], self.graduate_date)
        result["topOrganizes"] = from_union([lambda x: from_list(lambda y: to_class(OrganizeInfo, y), x), from_none], self.top_organizes)
        result["photoUrl"] = from_union([from_str, from_none], self.photo_url)
        result["type"] = from_union([lambda x: to_class(IdentityType, x), from_none], self.identity_type)
        return result


@dataclass
class AccountInfo:
    id: str
    account: str
    name: str
    kind: str
    code: str
    user_type: str
    organize: OrganizeInfo
    top_organize: OrganizeInfo
    class_no: Optional[str]
    avatars: Dict[str, Any]
    birthday: Optional[Birthday]
    gender: str
    email: str
    time_zone: int
    mobile: str
    identities: List[Identity]
    card_no: Optional[str]
    card_type: Optional[str]
    union_id: Optional[str]
    account_expire_date: Optional[str]

    @staticmethod
    def from_dict(obj: Any) -> 'AccountInfo':
        assert isinstance(obj, dict)
        
        id = from_str(obj.get("id"))
        account = from_str(obj.get("account"))
        name = from_str(obj.get("name"))
        kind = from_str(obj.get("kind"))
        code = from_str(obj.get("code"))
        user_type = from_str(obj.get("userType"))
        
        # 处理组织信息
        organize = OrganizeInfo.from_dict(obj.get("organize"))
        top_organize = OrganizeInfo.from_dict(obj.get("topOrganize"))
        
        class_no = from_union([from_str, from_none], obj.get("classNo"))
        avatars = from_dict(lambda x: x, obj.get("avatars", {}))
        
        # 处理生日信息
        birthday = from_union([Birthday.from_dict, from_none], obj.get("birthday"))
        
        gender = from_str(obj.get("gender"))
        email = from_str(obj.get("email"))
        time_zone = from_int(obj.get("timeZone"))
        mobile = from_str(obj.get("mobile"))
        
        # 处理身份列表
        identities = from_list(Identity.from_dict, obj.get("identities"))
        
        card_no = from_union([from_str, from_none], obj.get("cardNo"))
        card_type = from_union([from_str, from_none], obj.get("cardType"))
        union_id = from_union([from_str, from_none], obj.get("unionId"))
        account_expire_date = from_union([from_str, from_none], obj.get("accountExpireDate"))
        
        return AccountInfo(
            id, account, name, kind, code, user_type,
            organize, top_organize, class_no, avatars,
            birthday, gender, email, time_zone, mobile,
            identities, card_no, card_type, union_id, account_expire_date
        )

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = from_str(self.id)
        result["account"] = from_str(self.account)
        result["name"] = from_str(self.name)
        result["kind"] = from_str(self.kind)
        result["code"] = from_str(self.code)
        result["userType"] = from_str(self.user_type)
        result["organize"] = to_class(OrganizeInfo, self.organize)
        result["topOrganize"] = to_class(OrganizeInfo, self.top_organize)
        result["classNo"] = from_union([from_str, from_none], self.class_no)
        result["avatars"] = from_dict(lambda x: x, self.avatars)
        result["birthday"] = from_union([lambda x: to_class(Birthday, x), from_none], self.birthday)
        result["gender"] = from_str(self.gender)
        result["email"] = from_str(self.email)
        result["timeZone"] = from_int(self.time_zone)
        result["mobile"] = from_str(self.mobile)
        result["identities"] = from_list(lambda x: to_class(Identity, x), self.identities)
        result["cardNo"] = from_union([from_str, from_none], self.card_no)
        result["cardType"] = from_union([from_str, from_none], self.card_type)
        result["unionId"] = from_union([from_str, from_none], self.union_id)
        result["accountExpireDate"] = from_union([from_str, from_none], self.account_expire_date)
        return result


@dataclass
class ApiResponse:
    errno: int
    error: str
    total: int
    entities: List[AccountInfo]

    @staticmethod
    def from_dict(obj: Any) -> 'ApiResponse':
        assert isinstance(obj, dict)
        errno = from_int(obj.get("errno"))
        error = from_str(obj.get("error"))
        total = from_int(obj.get("total"))
        entities = from_list(AccountInfo.from_dict, obj.get("entities"))
        return ApiResponse(errno, error, total, entities)

    def to_dict(self) -> dict:
        result: dict = {}
        result["errno"] = from_int(self.errno)
        result["error"] = from_str(self.error)
        result["total"] = from_int(self.total)
        result["entities"] = from_list(lambda x: to_class(AccountInfo, x), self.entities)
        return result


def account_info_from_dict(s: Any) -> ApiResponse:
    return ApiResponse.from_dict(s)


def account_info_to_dict(x: ApiResponse) -> Any:
    return to_class(ApiResponse, x)


@register_tool(
    name="account_info",
    description="获取当前用户的个人信息，包括基本信息、身份信息、专业信息等",
    require_login=True
)
def get_account_info(context: SJTUContext) -> Dict[str, Any]:
    """
    获取当前用户的个人信息
    
    Args:
        context: SJTU上下文，包含已认证的会话
        
    Returns:
        用户个人信息字典，包含以下字段：
        - success: 是否成功
        - data: 用户信息数据（成功时）
        - error: 错误信息（失败时）
    """
    try:
        # 检查登录状态
        if not context.is_logged_in():
            logger.warning("用户未登录，无法获取个人信息")
            return {
                "success": False,
                "error": "用户未登录，请先登录 jAccount"
            }
        
        # 使用已认证的session发起请求
        session = context.session
        
        # 设置请求头
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://my.sjtu.edu.cn/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        logger.info("正在获取用户个人信息...")
        
        # 发起请求
        resp = session.get(
            "https://my.sjtu.edu.cn/api/account",
            headers=headers,
            timeout=30,
            allow_redirects=True
        )
        
        # 检查是否被重定向到登录页面
        if not resp.url.startswith("https://my.sjtu.edu.cn/"):
            logger.error(f"请求被重定向到: {resp.url}")
            return {
                "success": False,
                "error": "认证失败，请重新登录"
            }
        
        # 检查响应状态
        resp.raise_for_status()
        
        # 解析JSON响应
        try:
            data = resp.json()
        except ValueError as e:
            logger.error(f"响应不是有效的JSON格式: {e}")
            return {
                "success": False,
                "error": "服务器返回的数据格式错误"
            }
        
        # 使用新的数据类解析响应
        try:
            api_response = account_info_from_dict(data)
            
            # 检查API响应状态
            if api_response.errno != 0:
                logger.error(f"API返回错误: {api_response.error}")
                return {
                    "success": False,
                    "error": f"API错误: {api_response.error}"
                }
            
            # 检查是否有用户数据
            if not api_response.entities:
                logger.error("API返回的用户数据为空")
                return {
                    "success": False,
                    "error": "未找到用户信息"
                }
            
            # 获取第一个用户信息（通常只有一个）
            account_info = api_response.entities[0]
            result_data = account_info.to_dict()
            
            logger.info(f"成功获取用户 {account_info.account} ({account_info.name}) 的个人信息")
            return {
                "success": True,
                "data": result_data,
                "summary": {
                    "account": account_info.account,
                    "name": account_info.name,
                    "user_type": account_info.user_type,
                    "organize": account_info.organize.name,
                    "class_no": account_info.class_no,
                    "identities_count": len(account_info.identities)
                }
            }
            
        except Exception as e:
            logger.error(f"解析用户信息数据失败: {e}")
            # 如果解析失败，返回原始数据
            return {
                "success": True,
                "data": data,
                "warning": "数据解析失败，返回原始数据"
            }
        
    except Exception as e:
        error_msg = f"获取用户信息失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg
        }


# 工具元数据（用于MCP服务器自动发现）
TOOL_METADATA = {
    "name": "account_info",
    "version": "1.0.0",
    "author": "Teruteru",
    "description": "获取当前用户的个人信息",
    "category": "basic",
    "require_auth": True,
    "function": get_account_info
}
