import pytesseract
from PIL import Image

# 加载图片
image = Image.open("C:/Users/Yun/Desktop/Cache_-39c41bc39d332ff6.jpg")

# 进行OCR识别
text = pytesseract.image_to_string(image, lang='chi_sim')  # 使用简体中文语言包

# 打印识别结果
print(text)
