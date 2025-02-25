import requests
from bs4 import BeautifulSoup


def crawl_seer_wiki(pet_name):
    url = f"https://wiki.biligame.com/seer/{pet_name}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 检查HTTP状态码
        soup = BeautifulSoup(response.text, 'html.parser')

        # 示例：提取页面标题
        title = soup.find("h1", {"id": "firstHeading"}).text
        print(f"页面标题: {title}")

        # 更多数据提取逻辑（需自行分析页面结构）
        # 例如属性表格、技能表等

    except Exception as e:
        print(f"爬取失败: {str(e)}")


# 使用示例
crawl_seer_wiki("圣灵谱尼")