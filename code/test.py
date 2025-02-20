import ctypes
import os

import win32com
from comtypes.client import CreateObject
from win32com.client import Dispatch






# 初始化大漠插件
dm = win32com.client.DispatchEx("dm.dmsoft")
print(f"已加载大漠插件，版本: {dm.Ver()}")



# 查找图片
image_path = "img/勇者之塔1.bmp"

# 调用 FindPic 进行图像识别
# position = dm.FindPic(0, 0, 4000, 4000, image_path, "000000", 0.8, 0)
# position = DisplayBase.find_image(display, image_path, similarity=0.9, match_mode=0)
# 获取窗口句柄
hwnd = dm.FindWindow("", "茶杯登录器")
# 绑定窗口
bind_window = dm.BindWindow(hwnd, "normal", "normal", "normal", 0)
# 如果绑定成功，则进行识图
if bind_window:
    print("已绑定窗口，开始识图")
    # 注意这里的识图需要在画面内可见，被识别的区域不能被其它窗口覆盖
    position = dm.FindPic(0, 0, 4000, 4000, image_path, "000000", 0.8, 0)
    print("识图坐标", position)
    if position[1] != -1 and position[2] != -1:
        print("识图成功")
        # 获取识别到的图片坐标
        x, y = position[0], position[1]
        # 移动鼠标到识别到的图片坐标
        dm.MoveTo(445, 95)
        # 执行主点击操作
        dm.LeftClick()
    else:
        print("没有找到图片")
