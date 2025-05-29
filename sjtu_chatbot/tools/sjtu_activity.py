from ..mcp_server.server import register_tool, SJTUContext
from .account_info import get_account_info
import requests
from typing import List, Dict, Any, Optional
from urllib import parse
import base64

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

def getJaccountOIDCToken(sess: requests.Session) -> str:
    req1 = sess.get('https://jaccount.sjtu.edu.cn/oauth2/authorize', params={
                            'client_id': "NMCTdJI6Tluw2SSTe6tW",
                            'redirect_uri': 'https://activity.sjtu.edu.cn/auth',
                            'response_type': 'code',
                            'scope': 'profile',
                        }, headers=HEADERS)
    code = parse.parse_qs(parse.urlparse(req1.url).query)['code'][0]
    req2 = sess.get('https://activity.sjtu.edu.cn/api/v1/login/token', params={'code':code}, headers=HEADERS)
    token = req2.json()['data']
    return token

def getActivityTypes(token: str)->Optional[Dict[str, Any]]:
    return requests.get(
        url='https://activity.sjtu.edu.cn/api/v1/system/activity_type',
        params={'isAll': 'true'}, 
        headers={'Authorization': 'Bearer ' + token},
    ).json()["data"]
    
def getHotActivities(token: str, type_id: int = 1)->Optional[Dict[str, Any]]:
    return requests.get(
        url='https://activity.sjtu.edu.cn/api/v1/hot/list', 
        params={
            'activity_type_id': type_id,
            'fill': '1',
        }, 
        headers={'Authorization': 'Bearer ' + token}, 
    ).json()["data"]
    
def getAllActivities(token: str, 
                     type_id: int = 1, page: int = 1, page_size: int = 9)->Optional[Dict[str, Any]]:
    resp = requests.get(
        url='https://activity.sjtu.edu.cn/api/v1/activity/list/home', 
        params={
            'page': page, ## 可翻页
            'per_page': page_size, 
            'activity_type_id': type_id,
            'time_sort': 'desc',
            'can_apply': 'false'
        }, 
        headers={'Authorization': 'Bearer ' + token}, 
    )
    return sorted(resp.json()["data"], key=lambda x: x['activity_time'][0], reverse=True)

def getSingleActivity(token: str, id: int):
    resp = requests.get(
        url=f'https://activity.sjtu.edu.cn/api/v1/activity/{id}', 
        headers={'Authorization': 'Bearer ' + token}, 
    )
    return resp.json()["data"]

def getProfile(token: str):
    resp = requests.get(
        url=f'https://activity.sjtu.edu.cn/api/v1/profile', 
        headers={'Authorization': 'Bearer ' + token}, 
    )
    return resp.json()["data"]

def doSignUp(token, form_submit):
    resp = requests.post(
        url=f'https://activity.sjtu.edu.cn/api/v1/signUp',
        json=form_submit,
        headers={'Authorization': 'Bearer ' + token}, 
    )
    resp.raise_for_status()
    return resp.json()

def actIdToUrlParam(activityId:int) -> str:
    idStr = str(activityId)
    idStr = idStr + ' ' * ((3 - len(idStr)%3) % 3)
    return base64.b64encode(idStr.encode('utf-8')).decode('utf-8')

def getSignUpMethodDesc(method: int):
    match (method):
        case 1:
            return "线上报名（审核录取）"
        case 2:
            return "线下报名"
        case 3:
            return "线上报名（先到先得）"
        case 4:
            return "无需报名"
        case 5:
            return "线上报名（随机录取）"
        case 6:
            return "跳转其他报名"
        case _:
            raise Exception("no this method")

def get_activity_info_nl(activity: dict[str, Any]):
    res = \
    f"- [{activity['name']}]({'https://activity.sjtu.edu.cn/activity/detail/' + actIdToUrlParam(activity['id'])})" + "\n" + \
    f"  ![]({'https://activity.sjtu.edu.cn' + activity['img']})" + "\n" + \
    f"  id:{activity['id']}" + "\n" + \
    f"  主办方：{activity['sponsor']}" + "\n" + \
    (f"  报名人数：{activity['signed_up_num']} / {activity['person_num']}\n" if activity['person_num'] else "") + \
    f"  报名方式：{getSignUpMethodDesc(activity['method'])}" + "\n" + \
    (f"  报名时间：{activity['registration_time'][0]} ~ {activity['registration_time'][1]}\n" if activity['registration_time'][0] else "") + \
    f"  活动地点：{activity['address']}" + "\n" + \
    f"  活动时间：{activity['activity_time'][0]} ~ {activity['activity_time'][1]}"
    return res

def render_undetermined_form(form: dict[str, any]):
    if (form['tag'] == 'ElInput'):
        return f"- {form['label']}（类型：短文本）"
    elif (form['tag'] == 'textarea'):
        return f"- {form['label']}（类型：长文本）"
    elif (form['tag'] == 'Selector'):
        options = ','.join([("\"" + item['name'] + "\"") for item in form['dict']])
        return f"- {form['label']}（类型：单选；可选项：{options}）"
    elif (form['tag'] == 'RadioGroup'):
        options = ','.join([("\"" + item['name'] + "\"") for item in form['dict']])
        return f"- {form['label']}（类型：单选；可选项：{options}）"
    elif (form['tag'] == 'CheckboxGroup'):
        options = ','.join([("\"" + item['name'] + "\"") for item in form['dict']])
        return f"- {form['label']}（类型：多选；可选项：{options}）"
    elif (form['tag'] == 'file'):
        return f"- {form['label']}（类型：附件；助手无法处理，请用户手动报名）"
    elif (form['tag'] == 'img'):
        return f"- {form['label']}（类型：图片；助手无法处理，请用户手动报名）"

@register_tool(
    name="sjtu_activity",
    description="获取交大'第二课堂'的最新活动列表，参数 page 为页码，默认为 1。其中会返回一个包含一个 Markdown 格式的活动列表的 json，但可能会有格式错误。其中 id 为活动 id，可通过 sjtu_activity_signup 报名。",
    require_login=True
)
def sjtu_activity(context: SJTUContext, page: int = 1) -> dict:
    if not context.is_logged_in():
        return {"success": False, "error": "用户未登录，请先登录 jAccount"}
    sess = context.session
    try:
        token = getJaccountOIDCToken(sess)
        result = getAllActivities(token, 2, page, 10)
        return {"success": True, "data": [get_activity_info_nl(item) for item in result]}
    except Exception as e:
        return {"success": False, "error": str(e)}

@register_tool(
    name="sjtu_activity_signup",
    description="报名交大'第二课堂'活动，参数 id 为活动 id，additional_info 为补充信息（JSON 字符串）。一般不需要填写补充信息，而参数 id 可通过 sjtu_activity 获取。",
    require_login=True
)
def sjtu_activity_signup(context: SJTUContext, id: int, additional_info: str = "{}") -> dict:
    if not context.is_logged_in():
        return {"success": False, "error": "用户未登录，请先登录 jAccount"}
    sess = context.session
    try:
        token = getJaccountOIDCToken(sess)
        profile = getProfile(token)
        if (not profile):
            return {"success": False, "error": "授权失败"}
        activity = getSingleActivity(token, id)
        if (not activity):
            return {"success": False, "error": "找不到活动"}
        if (activity['in_signed_up'] == True):
            return {"success": True, "message": "已经报名，无需重复报名"}
        form_infos = activity['sign_up_info']['form_design']
        form_submit = {"id":id,"college":profile['topOrganizeId'],"form_value":{}}
        if (form_infos):
            import json
            account_info_result = get_account_info(context)
            if not account_info_result["success"]:
                return {"success": False, "error": "无法获取用户信息"}
            account_info = account_info_result["data"]
            identity = None
            for ident in account_info["identities"]:
                if ident.get("isDefault"):
                    identity = ident
                    break
            additional_forminfos = json.loads(additional_info)
            undetermined_forms = []
            for form_info in form_infos:
                if ("手机" in str(form_info['label'])):
                    form_submit['form_value'][form_info['id']] = account_info['mobile']
                elif ("邮箱" in str(form_info['label'])):
                    form_submit['form_value'][form_info['id']] = account_info['email']
                elif ("身份证" in str(form_info['label'])):
                    form_submit['form_value'][form_info['id']] = account_info['cardNo']
                elif ("学院" in str(form_info['label'])):
                    form_submit['form_value'][form_info['id']] = identity['organize']['name'] if identity and identity.get('organize') else None
                elif ("专业" in str(form_info['label'])):
                    form_submit['form_value'][form_info['id']] = identity['major']['name'] if identity and identity.get('major') else None
                elif (str(form_info['label']) in additional_forminfos):
                    form_submit['form_value'][form_info['id']] = additional_forminfos[str(form_info['label'])]
                else:
                    undetermined_forms.append(form_info)
            if (len(undetermined_forms) > 0):
                forms_rendered = '\n'.join(
                    [render_undetermined_form(form) for form in undetermined_forms]
                )
                return {"success": False, "error": "报名需要补充以下信息：\n" + forms_rendered}
        resp = doSignUp(token, form_submit)
        if resp.get("errno", 0) == 0:
            return {"success": True, "message": "报名成功"}
        else:
            return {"success": False, "error": resp.get("errmsg", "报名失败")}
    except Exception as e:
        return {"success": False, "error": str(e)} 

if __name__ == "__main__":
    import sys
    import json
    from sjtu_chatbot.mcp_server.jaccount_login import JAccountLoginManager
    from sjtu_chatbot.mcp_server.server import SJTUContext

    # 1. 获取登录管理器并确保已登录
    login_manager = JAccountLoginManager.get_instance()
    if not login_manager.ensure_logged_in():
        print("登录失败或取消，程序退出")
        sys.exit(1)
    sess = login_manager.get_session()

    # 2. 获取 OIDC token
    try:
        token = getJaccountOIDCToken(sess)
    except Exception as e:
        print(f"获取 OIDC Token 失败: {e}")
        sys.exit(1)
    
    context = SJTUContext(sess)
    print(sjtu_activity.__wrapped__(context, 1))
    res = sjtu_activity_signup.__wrapped__(context, int(9766), '')
    print(json.dumps(res, ensure_ascii=False, indent=2))
    

    # # 3. 命令行菜单
    # while True:
    #     print("\\n请选择要测试的功能：")
    #     print("1. 获取活动类型")
    #     print("2. 获取热门活动")
    #     print("3. 获取全部活动")
    #     print("4. 获取单个活动详情")
    #     print("5. 报名活动")
    #     print("0. 退出")
    #     choice = input("请输入序号: ").strip()
    #     if choice == '1':
    #         res = getActivityTypes(token)
    #         print(json.dumps(res, ensure_ascii=False, indent=2))
    #     elif choice == '2':
    #         type_id = input("请输入活动类型ID（默认1）: ").strip() or '1'
    #         res = getHotActivities(token, int(type_id))
    #         print(json.dumps(res, ensure_ascii=False, indent=2))
    #     elif choice == '3':
    #         type_id = input("请输入活动类型ID（默认1）: ").strip() or '1'
    #         page = input("请输入页码（默认1）: ").strip() or '1'
    #         page_size = input("每页数量（默认9）: ").strip() or '9'
    #         res = getAllActivities(token, int(type_id), int(page), int(page_size))
    #         print(json.dumps(res, ensure_ascii=False, indent=2))
    #     elif choice == '4':
    #         act_id = input("请输入活动ID: ").strip()
    #         if not act_id.isdigit():
    #             print("活动ID必须为数字！")
    #             continue
    #         res = getSingleActivity(token, int(act_id))
    #         print(json.dumps(res, ensure_ascii=False, indent=2))
    #     elif choice == '5':
    #         act_id = input("请输入要报名的活动ID: ").strip()
    #         additional_info = input("请输入补充信息（JSON字符串，默认{}）: ").strip() or "{}"
    #         # 伪造 context
    #         class DummyContext:
    #             def __init__(self, sess):
    #                 self.session = sess
    #             def is_logged_in(self):
    #                 return True
    #         context = DummyContext(sess)
    #         res = sjtu_activity_signup(context, int(act_id), additional_info)
    #         print(json.dumps(res, ensure_ascii=False, indent=2))
    #     elif choice == '0':
    #         print("再见！")
    #         break
    #     else:
    #         print("无效选项，请重新输入。")