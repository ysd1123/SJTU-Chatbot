from ..mcp_server.server import register_tool, SJTUContext
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Tuple
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@register_tool(
    name="jwc_news",
    description="获取教务处面向学生的通知公告。",
    require_login=False
)
def jwc_news(context: SJTUContext) -> dict:
    pageUrl = 'https://jwc.sjtu.edu.cn/xwtg/tztg.htm'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        req = requests.get(pageUrl, headers=headers)
        if req.status_code != requests.codes.ok:
            return {"success": False, "error": "获取信息失败，请检查网络连接"}
        req.encoding = 'utf-8'
        html = req.text
        soup = BeautifulSoup(html, 'lxml')
        news_list = soup.find_all('li', class_='clearfix')
        result = []
        for news in news_list:
            try:
                date_div = news.find('div', class_='sj')
                day = date_div.find('h2').text.strip()
                month_year = date_div.find('p').text.strip()
                year, month = month_year.split('.')
                date = f"{year}年{int(month)}月{int(day)}日"
                title = news.find('div', class_='wz').find('h2').text.strip()
                link = news.find('div', class_='wz').find('a').get('href')
                if link.startswith('..'):
                    link = 'https://jwc.sjtu.edu.cn' + link[2:]
                summary = news.find('div', class_='wz').find('p').text.strip()
                result.append({
                    'date': date,
                    'title': title,
                    'link': link,
                    'summary': summary
                })
            except Exception:
                continue
        output = '\n\n'.join(
            [f"- [{item['title']}]({item['link']})\n{item['summary']}\n{item['date']}" for item in result]
        )
        return {"success": True, "data": output}
    except Exception as e:
        return {"success": False, "error": str(e)} 