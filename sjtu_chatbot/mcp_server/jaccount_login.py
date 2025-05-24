"""
jAccount 登录管理模块

该模块负责处理 jAccount 的登录认证、会话管理和 Cookie 持久化，
支持账号密码登录，并提供会话状态检查和 Cookie 管理功能。
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple, Callable
import logging
from PIL import Image
import io
import threading
import urllib.parse
from bs4 import BeautifulSoup
from getpass4 import getpass

# 配置日志
logger = logging.getLogger(__name__)

# 默认的初始访问 URL，用于触发 jAccount 登录流程
DEFAULT_INITIAL_URL = "https://my.sjtu.edu.cn/api/account"

# 登录状态验证 URL，用于检查是否已登录
LOGIN_CHECK_URL = "https://my.sjtu.edu.cn/api/account"

# Cookie 有效期检查间隔（秒）
COOKIE_CHECK_INTERVAL = 300  # 5分钟检查一次


class JAccountLoginManager:
    """
    jAccount 登录管理器单例类

    该类负责全局管理 jAccount 登录状态和会话，确保系统中只有一个登录管理实例。
    """
    _instance = None

    @classmethod
    def get_instance(cls, config_path: Optional[Union[str, Path]] = None):
        """
        获取 JAccountLoginManager 单例实例

        参数:
            config_path: Cookie 配置文件路径，如果为 None 则使用默认路径

        返回:
            JAccountLoginManager 单例实例
        """
        if cls._instance is None:
            cls._instance = JAccountLogin(config_path)
        return cls._instance


class JAccountLogin:
    """
    jAccount 登录管理类

    该类提供了与上海交通大学 jAccount 系统交互的功能，包括登录、登出、会话管理等。
    支持账号密码登录，并能够持久化保存登录会话。
    """

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        初始化 jAccount 登录管理器

        参数:
            config_path: Cookie 配置文件路径，如果为 None 则使用默认路径
        """
        self.session = requests.Session()

        # 设置默认配置路径
        if config_path is None:
            # 使用相对于当前文件的路径
            self.config_path = Path(__file__).parent.parent / "config" / "jaccount_config.json"
        else:
            self.config_path = Path(config_path)

        # 确保配置目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建缓存目录
        self.cache_dir = self.config_path.parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cookies = None
        self._load_cookies()

        # 会话状态监控
        self._session_monitor_thread = None
        self._session_monitor_stop = False
        self._login_callback = None
        self._last_check_time = 0

    def _save_cookies(self) -> None:
        """保存会话 Cookie 到配置文件"""
        if self.cookies:
            try:
                with open(self.config_path, 'w') as f:
                    json.dump(self.cookies, f)
                logger.info(f"Cookie 已保存到 {self.config_path}")
            except Exception as e:
                logger.error(f"保存 Cookie 时出错: {e}")

    def _load_cookies(self) -> None:
        """从配置文件加载会话 Cookie"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    self.cookies = json.load(f)
                    # 直接更新会话的 cookies 字典，而不是使用 update 方法
                    for key, value in self.cookies.items():
                        self.session.cookies.set(key, value)
                    logger.info(f"Cookie 已从 {self.config_path} 加载")
            else:
                logger.info(f"Cookie 文件 {self.config_path} 不存在，创建新会话")
                self.cookies = None
        except json.JSONDecodeError:
            logger.error(f"解析 Cookie 文件 {self.config_path} 时出错，创建新会话")
            self.cookies = None
        except Exception as e:
            logger.error(f"加载 Cookie 时出错: {e}")
            self.cookies = None

    def _parse_params(self, url: str) -> Dict[str, str]:
        """
        解析 URL 中的查询参数

        参数:
            url: 要解析的 URL

        返回:
            包含查询参数的字典
        """
        params = {}
        if '?' in url:
            query_string = url.split('?', 1)[1]
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    params[urllib.parse.unquote(key)] = urllib.parse.unquote(value)
        return params

    def _get_login_params(self, initial_url: str = DEFAULT_INITIAL_URL) -> Tuple[Dict[str, str], str, str]:
        """
        获取 jAccount 登录所需的参数

        参数:
            initial_url: 初始访问的 URL，默认为 my.sjtu.edu.cn/api/account

        返回:
            (登录参数字典, UUID, 登录页面 URL)
        """
        try:
            # 访问初始 URL，触发重定向到 jAccount 登录页面
            response = self.session.get(
                initial_url,
                headers={"accept-language": "zh-CN"},
                allow_redirects=True
            )

            # 解析登录页面 URL 中的参数
            login_url = response.url
            login_params = self._parse_params(login_url)

            # 从页面内容中提取 UUID
            soup = BeautifulSoup(response.content, 'html.parser')

            # 尝试多种方式提取 UUID
            uuid = None

            # 方法1: 通过 firefox_link
            firefox_link = soup.find('a', attrs={'id': 'firefox_link'})
            if firefox_link and 'href' in firefox_link.attrs:
                href = firefox_link['href']
                if '=' in href:
                    uuid = href.split('=')[1]

            # 方法2: 通过 input 字段
            if not uuid:
                uuid_input = soup.find('input', attrs={'name': 'uuid'})
                if uuid_input and 'value' in uuid_input.attrs:
                    uuid = uuid_input['value']

            # 方法3: 通过 URL 参数
            if not uuid and 'uuid' in login_params:
                uuid = login_params['uuid']

            # 方法4: 通过 JavaScript 变量
            if not uuid:
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'var uuid' in script.string:
                        for line in script.string.split('\n'):
                            if 'var uuid' in line and '=' in line:
                                uuid_part = line.split('=')[1].strip()
                                uuid = uuid_part.strip('"').strip("'").strip(';')
                                break

            if not uuid:
                # 尝试直接从页面内容中查找 UUID 格式的字符串
                import re
                uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
                uuid_matches = re.findall(uuid_pattern, response.text)
                if uuid_matches:
                    uuid = uuid_matches[0]

            if not uuid:
                # 如果仍然无法提取 UUID，则尝试使用固定的登录 URL
                logger.warning("无法从页面提取 UUID，尝试使用固定的登录 URL")
                login_url = "https://jaccount.sjtu.edu.cn/jaccount/jalogin"
                login_params = {}
                uuid = ""
            else:
                logger.info(f"已获取登录参数: {login_params}")
                logger.info(f"已获取 UUID: {uuid}")

            return login_params, uuid, login_url

        except Exception as e:
            logger.error(f"获取登录参数时出错: {e}")
            raise

    def is_logged_in(self) -> bool:
        """
        检查当前会话是否已登录

        返回:
            如果已登录则返回 True，否则返回 False
        """
        if not self.cookies:
            return False

        try:
            # 访问登录状态验证 URL
            response = self.session.get(
                LOGIN_CHECK_URL,
                allow_redirects=False,
                timeout=10
            )

            # 如果返回 200 且响应是 JSON 格式，检查是否包含成功标志
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("errno") == 0 and data.get("error") == "success":
                        logger.info("会话已登录")
                        return True
                except ValueError:
                    pass

            # 如果状态码是 302 且重定向到登录页面，则未登录
            if response.status_code == 302 and "jaccount.sjtu.edu.cn/jaccount/jalogin" in response.headers.get("Location", ""):
                logger.info("会话未登录")
                return False

            logger.info("会话未登录或状态不明确")
            return False

        except Exception as e:
            logger.error(f"检查登录状态时出错: {e}")
            return False

    def login_with_password(self, username: str, password: str, initial_url: str = DEFAULT_INITIAL_URL) -> bool:
        """
        使用账号密码登录 jAccount

        参数:
            username: jAccount 用户名
            password: jAccount 密码
            initial_url: 初始访问的 URL，默认为 my.sjtu.edu.cn/api/account

        返回:
            登录成功返回 True，否则返回 False
        """
        logger.info(f"尝试使用密码登录账号: {username}")

        try:
            # 获取登录参数
            login_params, uuid, login_url = self._get_login_params(initial_url)

            # 获取验证码图片
            captcha_url = "https://jaccount.sjtu.edu.cn/jaccount/captcha"
            captcha_params = {
                "uuid": uuid,
                "t": time.time_ns() #int(time.time() * 1000)
            }

            captcha_response = self.session.get(
                captcha_url,
                params=captcha_params,
                headers={"Referer": captcha_url, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"},
                timeout=10
            )

            # 保存验证码图片到临时文件
            try:
                # 先将验证码保存为文件，然后再用 PIL 打开，避免直接从内存打开可能的格式问题
                captcha_temp_path = self.cache_dir / f"captcha_temp_{int(time.time())}.png"
                with open(captcha_temp_path, "wb") as f:
                    f.write(captcha_response.content)

                # 使用 PIL 打开保存的图片文件
                captcha_img = Image.open(captcha_temp_path)
                captcha_path = self.cache_dir / f"captcha_{int(time.time())}.png"
                captcha_img.save(captcha_path)

                # 删除临时文件
                if captcha_temp_path.exists():
                    captcha_temp_path.unlink()

                print(f"验证码图片已保存到: {captcha_path}")
            except Exception as e:
                logger.error(f"处理验证码图片时出错: {e}")
                # 如果 PIL 处理失败，直接保存原始内容
                captcha_path = self.cache_dir / f"captcha_raw_{int(time.time())}.png"
                with open(captcha_path, "wb") as f:
                    f.write(captcha_response.content)
                print(f"验证码图片已保存到: {captcha_path}")

            captcha = input("请输入验证码: ")

            # 提交登录表单
            login_data = {
                "user": username,
                "pass": password,
                "uuid": uuid,
                "captcha": captcha,
                **login_params
            }

            login_response = self.session.post(
                "https://jaccount.sjtu.edu.cn/jaccount/ulogin",
                data=login_data,
                headers={"accept-language": "zh-CN"},
                allow_redirects=True,
                timeout=10
            )

            # 检查登录是否成功
            if "jaccount.sjtu.edu.cn/jaccount/jalogin" in login_response.url:
                logger.error("登录失败，可能是用户名、密码或验证码错误")
                return False

            # 保存 Cookie - 使用字典序列化而不是直接使用 session.cookies
            self.cookies = {}
            for cookie in self.session.cookies:
                self.cookies[cookie.name] = cookie.value

            self._save_cookies()
            logger.info("密码登录成功")
            return True

        except Exception as e:
            logger.error(f"密码登录过程中发生错误: {e}")
            return False

    def logout(self) -> bool:
        """
        登出 jAccount

        返回:
            登出成功返回 True，否则返回 False
        """
        try:
            # 访问登出 URL
            logout_url = "https://jaccount.sjtu.edu.cn/jaccount/logout"
            self.session.get(logout_url, allow_redirects=True, timeout=10)

            # 清除会话和 Cookie
            self.cookies = None
            self.session.cookies.clear()

            # 删除 Cookie 文件
            if self.config_path.exists():
                self.config_path.unlink()
                logger.info(f"已删除 Cookie 文件: {self.config_path}")

            logger.info("已成功登出")
            return True
        except Exception as e:
            logger.error(f"登出过程中发生错误: {e}")
            return False

    def get_session(self) -> requests.Session:
        """
        获取当前会话对象

        返回:
            requests.Session 对象，可用于访问需要 jAccount 认证的资源
        """
        return self.session

    def get_cookies_dict(self) -> Dict:
        """
        获取当前会话的 Cookie 字典

        返回:
            Cookie 字典，如果未登录则返回空字典
        """
        return self.cookies or {}

    def get_auth_cookie(self) -> str:
        """
        获取用于认证的 Cookie 字符串

        返回:
            认证 Cookie 字符串，如果未登录则返回空字符串
        """
        if not self.cookies:
            return ""

        # 提取关键认证 Cookie，例如 JAAuthCookie
        auth_cookies = []
        for key, value in self.cookies.items():
            if key.lower() in ["jaauthcookie", "jsessionid", "castgc"]:
                auth_cookies.append(f"{key}={value}")

        return "; ".join(auth_cookies)

    def start_session_monitor(self, login_callback: Optional[Callable[[], None]] = None) -> None:
        """
        启动会话状态监控线程

        该方法启动一个后台线程，定期检查会话状态，确保登录状态持续有效。
        如果检测到会话失效，将调用登录回调函数。

        参数:
            login_callback: 会话失效时的回调函数，用于触发重新登录
        """
        if self._session_monitor_thread and self._session_monitor_thread.is_alive():
            logger.info("会话监控线程已在运行")
            return

        self._login_callback = login_callback
        self._session_monitor_stop = False
        self._session_monitor_thread = threading.Thread(
            target=self._session_monitor_task,
            daemon=True
        )
        self._session_monitor_thread.start()
        logger.info("已启动会话状态监控")

    def stop_session_monitor(self) -> None:
        """停止会话状态监控线程"""
        if self._session_monitor_thread and self._session_monitor_thread.is_alive():
            self._session_monitor_stop = True
            self._session_monitor_thread.join(timeout=2)
            logger.info("已停止会话状态监控")

    def _session_monitor_task(self) -> None:
        """会话状态监控任务"""
        logger.info("会话监控线程已启动")

        while not self._session_monitor_stop:
            # 检查是否需要验证登录状态
            current_time = time.time()
            if current_time - self._last_check_time >= COOKIE_CHECK_INTERVAL:
                self._last_check_time = current_time

                # 检查登录状态
                if not self.is_logged_in():
                    logger.warning("检测到会话已失效")

                    # 如果设置了回调函数，调用它
                    if self._login_callback:
                        try:
                            self._login_callback()
                        except Exception as e:
                            logger.error(f"执行登录回调函数时出错: {e}")
                else:
                    # 访问一次受保护资源，保持会话活跃
                    try:
                        self.session.get(
                            LOGIN_CHECK_URL,
                            timeout=10
                        )
                        logger.debug("已刷新会话状态")
                    except Exception as e:
                        logger.error(f"刷新会话状态时出错: {e}")

            # 休眠一段时间
            time.sleep(10)  # 每10秒检查一次是否需要验证登录状态

        logger.info("会话监控线程已退出")

    def ensure_logged_in(self, username: str = None, password: str = None) -> bool:
        """
        确保当前会话已登录，如果未登录则尝试登录

        参数:
            username: jAccount 用户名，如果为 None 则在需要时提示输入
            password: jAccount 密码，如果为 None 则在需要时提示输入

        返回:
            如果已登录或登录成功则返回 True，否则返回 False
        """
        # 检查是否已登录
        if self.is_logged_in():
            logger.info("会话已登录，无需重新登录")
            return True

        logger.info("会话未登录，尝试登录")

        # 如果未提供用户名和密码，提示输入
        if username is None:
            time.sleep(1)
            username = input("请输入 jAccount 用户名: ")
        if password is None:
            time.sleep(1)
            # password = input("请输入 jAccount 密码: ")
            print("我们使用了 getpass4 模块来隐藏密码输入，但是它在 PyCharm 终端下不受支持。")
            print("如果你正在使用 PyCharm，请退出程序并使用其他命令行终端执行 Python 文件。")
            password = getpass("请输入 jAccount 密码:") # 让输入不可见，提高隐私保护
            
        # 尝试登录
        return self.login_with_password(username, password)


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 示例用法
    login_manager = JAccountLogin()
    
    # 确保已登录
    if not login_manager.ensure_logged_in():
        print("登录失败或取消")
        exit(1)
        
    print("已成功登录")
    
    # 启动会话监控
    def login_callback():
        print("会话已失效，请重新登录")
        login_manager.ensure_logged_in()
    
    login_manager.start_session_monitor(login_callback)
    
    # 保持程序运行一段时间，以便观察会话监控
    try:
        print("程序将保持运行 60 秒，以便观察会话监控...")
        time.sleep(60)
    except KeyboardInterrupt:
        print("程序已被用户中断")
    finally:
        login_manager.stop_session_monitor()
        print("程序已退出")
