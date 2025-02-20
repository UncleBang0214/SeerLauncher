# SeerLauncher

项目基于PYQT5，使用Python3.6.8-32bit

主要实现Seer登录器的登录、变速、内置信息、脚本等功能，该登录器主要面向民间服务器版本Seer


部分注意事项：

1.生成QRC文件
引用时写from img import login_logo_rc
pyrcc5 -o login_logo_rc.py img/login_logo.qrc

2.打包
pyinstaller SeerLauncher.spec




更新日志：

v0.9.0.20250204_Base
实现了加载页面、刷新和绕过登录

v0.9.1.20250205_Alpha
添加独立的登录窗口，实现了变速功能

v0.9.2.20250207_Alpha
基于1920*1080分辨率调整窗口大小，添加窗口logo

v0.9.3.20250210_Alpha
添加静音功能，制作识图点击脚本雏形

v0.9.4.20250214_Alpha
新增加载定义脚本功能，支持自主启停，支持自定义编写json脚本

v0.9.5.20250219_Beta
新增精灵能力值计算器

