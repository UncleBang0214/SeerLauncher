from PIL import Image

def turn_to_24bit_bmp(input_path, output_path):
    """
    将图片转换为 24 位色 BMP 格式。

    参数:
    - input_path: 输入图片路径
    - output_path: 输出 BMP 图片路径
    """
    try:
        # 打开图片
        img = Image.open(input_path)

        # 确保图片为 RGB 模式（24 位色）
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 保存为 BMP 格式
        img.save(output_path, "BMP")
        print(f"图片已成功转换为 24 位色 BMP 格式，保存路径: {output_path}")
    except Exception as e:
        print(f"图片转换失败: {e}")


input_image = "C:/Users/Yun/Desktop/Test/SeerLauncher/code/img/误触赛尔个人信息.png"
output_image = "C:/Users/Yun/Desktop/Test/SeerLauncher/code/img/误触赛尔个人信息.bmp"
turn_to_24bit_bmp(input_image, output_image)