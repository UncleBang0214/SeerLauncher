import json
from collections import defaultdict


def merge_learning_data(race_file, learn_file, output_file):
    """
    合并种族值数据和学习力数据

    参数：
    race_file: 种族值数据文件路径
    learn_file: 学习力数据文件路径
    output_file: 输出文件路径
    """
    # 加载种族值数据
    with open(race_file, 'r', encoding='utf-8') as f:
        race_data = json.load(f)

    # 构建名称索引字典（处理名称可能重复的情况）
    name_mapping = defaultdict(list)
    for idx, item in enumerate(race_data):
        name_mapping[item["名称"]].append(idx)

    # 解析学习力数据
    learn_data = {}
    with open(learn_file, 'r', encoding='utf-8') as f:
        # 跳过表头
        next(f)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                serial = parts[0].strip()
                name = parts[1].strip()
                learn = parts[2].strip()
                learn_data[name] = {
                    "序号": int(serial),
                    "学习力掉落": learn
                }

    merged = []
    for name, indexes in name_mapping.items():
        if name in learn_data:
            learn_info = learn_data[name]
            for idx in indexes:
                original_item = race_data[idx]
                # 重新组织字段顺序
                merged_item = {
                    "序号": learn_info["序号"],  # 先放序号
                    "名称": original_item["名称"],  # 接着是名称
                    # 保持其他属性原有顺序
                    "体力": original_item["体力"],
                    "攻击": original_item["攻击"],
                    "特攻": original_item["特攻"],
                    "防御": original_item["防御"],
                    "特防": original_item["特防"],
                    "速度": original_item["速度"],
                    "总和": original_item["总和"],
                    "学习力掉落": learn_info["学习力掉落"]  # 最后放学习力
                }
                merged.append(merged_item)

    # 按序号排序
    merged.sort(key=lambda x: x["序号"])

    # 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"成功合并 {len(merged)} 条数据，已保存至 {output_file}")


# 使用示例
if __name__ == "__main__":
    merge_learning_data(
        race_file="C:/Users/Yun/Desktop/种族值.txt",
        learn_file="C:/Users/Yun/Desktop/学习力.txt",
        output_file="C:/Users/Yun/Desktop/合并结果.json"
    )