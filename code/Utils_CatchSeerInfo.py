import random

import requests
from urllib.parse import quote
from bs4 import BeautifulSoup
import json
import time


def get_race_values(spirit_name):
    """获取指定精灵的种族值数据"""
    url = f"https://wiki.biligame.com/seer/{quote(spirit_name)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://wiki.biligame.com/"
    }

    try:
        # 发起请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 初始化结果字典
        result = {
            "名称": spirit_name,
            "体力": 0,
            "攻击": 0,
            "特攻": 0,
            "防御": 0,
            "特防": 0,
            "速度": 0,
            "总和": 0
        }

        # 解析种族值表格
        table = soup.find("table", class_="qnzl_character_talent_table")
        if table:
            rows = table.find_all("tr")

            # 确保表格结构正确
            if len(rows) >= 4:
                headers = [th.text.strip() for th in rows[2].find_all("th")]  # 第三行是表头
                values = [td.text.strip().replace("&nbsp;", "") for td in rows[3].find_all("td")]

                # 映射字段到结果字典
                field_mapping = {
                    "攻击": "攻击",
                    "防御": "防御",
                    "特攻": "特攻",
                    "特防": "特防",
                    "速度": "速度",
                    "体力": "体力",
                    "总能力值": "总和"
                }

                # 动态匹配字段
                for header, value in zip(headers, values):
                    if header in field_mapping:
                        key = field_mapping[header]
                        try:
                            result[key] = int(value)
                        except ValueError:
                            pass

        return result

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {str(e)}")
        return None
    except Exception as e:
        print(f"解析失败: {str(e)}")
        return None


def main():
    spirits = [
        "波古",
        "浮空苗",
        "卡克拉",
        "卡门兔",
        "艾丝柏",
    ]

    results = []
    for spirit in spirits:
        print(f"正在抓取 {spirit}...")
        data = get_race_values(spirit)
        if data:
            results.append(data)
        randomT = random.randint(1, 3)
        print(f"{spirit} 抓取完成，等待 {randomT} 秒...")
        time.sleep(randomT)  # 添加请求间隔

    # 输出结果
    print("\n抓取结果：")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
