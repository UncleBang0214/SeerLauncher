import atexit
import json
import sys
import os
import threading
import time
from ctypes import CDLL, c_float

from pycaw.utils import AudioUtilities
from win32com.client import Dispatch
from PyQt5 import QAxContainer, QtWidgets, QtCore
from PyQt5.QtCore import QRect, pyqtSignal, Qt, QEvent
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog, QMessageBox, QFileDialog
from PyQt5.QtGui import QIcon
from Ui_MainWindow import Ui_MainWindow
from Ui_LoginWindow import Ui_LoginWindow
from Ui_SpeedControlWindow import Ui_SpeedControlWindow
from Ui_CalculatorWindow import Ui_CalculatorWindow
from Ui_LoadScriptDialogWindow import Ui_LoadScriptDialogWindow
from Ui_ConfirmExitDialogWindow import Ui_ConfirmExitDialogWindow

launcher_name = "茶杯登录器"  # 登录器名称
global_is_stay_on_top = False  # 窗口置顶状态标志
dm = None  # 大漠插件对象
global_is_scripts_enabled = False  # 脚本功能是否启用
global_script_path = None  # 当前脚本路径
script_thread = None  # 脚本线程


##################### 获取资源路径 #####################
def resource_path(relative_path):
    # 获取exe文件所在路径
    if getattr(sys, 'frozen', False):  # 判断是否为打包后的exe文件
        base_path = os.path.dirname(sys.executable)  # exe文件所在目录，注意把所有需要加载的图片资源都外放
    else:
        base_path = os.path.abspath(".")  # 开发环境下的项目根目录

    # 构建资源文件的绝对路径
    resource_path = os.path.join(base_path, relative_path)
    # print(f"使用默认资源: {resource_path}")
    return resource_path


##################### 初始化大漠插件并注册为全局变量 #####################
def initialize_dm():
    global dm
    try:
        dll_path = resource_path('dm.dll')
        if not os.path.exists(dll_path):
            print(f"未找到dll: {dll_path}")
            return False

        result = os.system(f"regsvr32 /s {dll_path}")
        if result == 0:
            print(f"{dll_path} 注册成功！")
        else:
            print(f"{dll_path} 注册失败，请检查是否以管理员身份运行！")
            return False

        dm = Dispatch('dm.dmsoft')
        print(f"已加载大漠插件，版本: {dm.Ver()}")
        return True

    except Exception as e:
        print(f"初始化大漠插件失败: {e}")
        return False


##################### 注销大漠插件 #####################
def unregister_dm():
    global dm
    if dm is not None:
        print("正在注销大漠插件")
        try:
            dll_path = resource_path('dm.dll')
            if os.path.exists(dll_path):
                result = os.system(f"regsvr32 /u /s {dll_path}")
                if result == 0:
                    print(f"{dll_path} 注销成功！")
                else:
                    print(f"{dll_path} 注销失败，请检查权限！")
            else:
                print("未找到大漠插件 DLL 文件，无法注销！")
        except Exception as e:
            print(f"注销大漠插件失败: {e}")
    else:
        print("大漠插件未初始化，无需注销！")


##################### 根据账号密码生成oldSession #####################
def string_to_hex(s):
    hex_string = ''.join([format(ord(c), '02x') for c in s])
    while len(hex_string) < 24:
        hex_string = '0' + hex_string
    return hex_string


def generate_old_session(account, password):
    account_bytes = string_to_hex(password)
    num = int(account)
    hex_string = format(num, '08x')
    old_session = hex_string + hex_string + account_bytes
    return old_session


##################### 确认退出对话框定义 #####################
class ConfirmExitDialog(QDialog):
    def __init__(self, parent=None):
        super(ConfirmExitDialog, self).__init__(parent)
        self.ui = Ui_ConfirmExitDialogWindow()
        self.ui.setupUi(self)

        # 连接按钮信号到对话框的 accept 和 reject 方法
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


##################### 登录窗口定义及初始化 #####################
class LoginDialog(QDialog, Ui_LoginWindow):
    def __init__(self, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.setupUi(self)
        self.confirmButton.clicked.connect(self.handle_login)
        self.setWindowIcon(self.windowIcon())

    def handle_login(self):
        account = self.accountEdit.text().strip()
        password = self.passwordEdit.text().strip()
        if not account or not password:
            QMessageBox.warning(self, "警告", "账号或密码不能为空！")
            return
        if not account.isdigit() or len(account) != 9:
            QMessageBox.warning(self, "警告", "账号必须是 9 位数字！")
            return
        if len(password) > 10:
            QMessageBox.warning(self, "警告", "密码长度不能超过 10 位！")
            return
        old_session = generate_old_session(account, password)
        self.main_window = MyMainWindow(old_session)
        self.accept()


##################### 变速窗口定义及初始化 #####################
class SpeedControlDialog(QDialog, Ui_SpeedControlWindow):
    def __init__(self, parent=None):
        super(SpeedControlDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowIcon(self.windowIcon())
        self.lib = CDLL(r"SpeedControl.dll")
        self.horizontalSlider.setMinimum(1)
        self.horizontalSlider.setMaximum(10)
        self.horizontalSlider.setSingleStep(1)
        self.horizontalSlider.valueChanged.connect(self.update_text_edit)
        self.buttonBox.accepted.connect(self.change_speed)
        self.buttonBox.rejected.connect(self.reject)

    def update_text_edit(self):
        value = self.horizontalSlider.value()
        self.textEdit_speed.setText(str(value))

    def change_speed(self):
        try:
            value = float(self.textEdit_speed.text())
            if value < 1:
                value = 1
            self.lib.SetRange(c_float(value))
            print(f"变速为 {value}x.")
            self.accept()
        except Exception as e:
            print(f"变速时发生错误: {e}")


##################### 计算器窗口定义及初始化 #####################
class CalculatorWindow(QtWidgets.QMainWindow, Ui_CalculatorWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)  # 加载 UI 文件

        # 设置输入框内的字体居中
        input_fields = [
            self.LevelEdit,
            self.IndividualEdit,
            self.RaceEdit_1, self.EffortEdit_1, self.CharacterEdit_1,
            self.RaceEdit_2, self.EffortEdit_2, self.CharacterEdit_2,
            self.RaceEdit_3, self.EffortEdit_3, self.CharacterEdit_3,
            self.RaceEdit_4, self.EffortEdit_4, self.CharacterEdit_4,
            self.RaceEdit_5, self.EffortEdit_5, self.CharacterEdit_5,
            self.RaceEdit_6, self.EffortEdit_6, self.HPLabel,
            self.AttackLabel, self.SpAttackLabel, self.DefenseLabel,
            self.SpDefenseLabel, self.SpeedLabel
        ]

        for field in input_fields:
            if field:  # 确保字段存在
                field.setAlignment(QtCore.Qt.AlignCenter)  # 设置文本居中

        # 检查控件是否正确加载
        if not hasattr(self, "CalculateButton"):
            raise AttributeError("UI 文件中缺少 CalculateButton 控件")
        if not hasattr(self, "LevelEdit"):
            raise AttributeError("UI 文件中缺少 LevelEdit 控件")

        # 绑定“开始计算”按钮点击事件
        self.CalculateButton.clicked.connect(self.calculate_stats)
        self.CharacterComboBox.currentTextChanged.connect(self.update_character_modifiers)

    def calculate_stats(self):
        """计算精灵能力值"""
        try:
            # 获取等级和个体值
            level = int(self.LevelEdit.text().strip() or 100)  # 默认等级为 100
            iv_value = int(self.IndividualEdit.text().strip() or 31)  # 默认个体值为 31

            # 定义属性名称、控件及其对应的性格修正框
            stats = {
                "体力": (self.RaceEdit_1, self.EffortEdit_1, None, self.HPLabel),  # 体力无性格修正框
                "攻击": (self.RaceEdit_2, self.EffortEdit_2, self.CharacterEdit_1, self.AttackLabel),
                "特攻": (self.RaceEdit_3, self.EffortEdit_3, self.CharacterEdit_2, self.SpAttackLabel),
                "防御": (self.RaceEdit_4, self.EffortEdit_4, self.CharacterEdit_3, self.DefenseLabel),
                "特防": (self.RaceEdit_5, self.EffortEdit_5, self.CharacterEdit_4, self.SpDefenseLabel),
                "速度": (self.RaceEdit_6, self.EffortEdit_6, self.CharacterEdit_5, self.SpeedLabel),
            }

            # 获取当前选择的性格
            current_nature = self.CharacterComboBox.currentText()  # 假设性格下拉框名为 NatureComboBox

            # 根据性格计算性格修正值
            nature_modifiers = self.get_nature_modifiers(current_nature)

            # 遍历每个属性并计算能力值
            for stat_name, (race_edit, effort_edit, char_edit, result_label) in stats.items():
                race_value = int(race_edit.text().strip() or 0)  # 种族值
                effort_value = int(effort_edit.text().strip() or 0)  # 努力值
                nature_modifier = nature_modifiers.get(stat_name, 1.0)  # 获取该属性的性格修正值

                # 如果有性格修正框且当前属性不是体力，则设置性格修正框的值
                if char_edit and stat_name != "体力":
                    char_edit.setText(f"{nature_modifier:.1f}")

                # 计算基础公式
                base_stat = ((race_value * 2 + iv_value + effort_value // 4) * level) // 100

                if stat_name == "体力":
                    stat_value = base_stat + level + 10  # HP 公式
                else:
                    stat_value = base_stat + 5  # 非 HP 公式

                # 应用性格修正（仅对非 HP 属性生效）
                if stat_name != "体力":
                    stat_value = int(stat_value * nature_modifier)

                # 设置结果显示
                result_label.setText(f"{stat_value}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"计算失败: {e}")
            print(f"Error: {e}")

    def get_nature_modifiers(self, nature):
        """
        根据性格返回各属性的性格修正值。
        """
        # 性格修正规则表
        nature_table = {
            "固执": {"攻击": 1.1, "特攻": 0.9},
            "孤独": {"攻击": 1.1, "防御": 0.9},
            "调皮": {"攻击": 1.1, "特防": 0.9},
            "勇敢": {"攻击": 1.1, "速度": 0.9},
            "保守": {"特攻": 1.1, "攻击": 0.9},
            "稳重": {"特攻": 1.1, "防御": 0.9},
            "马虎": {"特攻": 1.1, "特防": 0.9},
            "冷静": {"特攻": 1.1, "速度": 0.9},
            "胆小": {"速度": 1.1, "攻击": 0.9},
            "开朗": {"速度": 1.1, "特攻": 0.9},
            "急躁": {"速度": 1.1, "防御": 0.9},
            "天真": {"速度": 1.1, "特防": 0.9},
            "大胆": {"防御": 1.1, "攻击": 0.9},
            "顽皮": {"防御": 1.1, "特攻": 0.9},
            "无虑": {"防御": 1.1, "特防": 0.9},
            "悠闲": {"防御": 1.1, "速度": 0.9},
            "沉着": {"特防": 1.1, "攻击": 0.9},
            "慎重": {"特防": 1.1, "特攻": 0.9},
            "温顺": {"特防": 1.1, "防御": 0.9},
            "狂妄": {"特防": 1.1, "速度": 0.9},
        }

        # 默认无补正
        modifiers = {"体力": 1.0, "攻击": 1.0, "特攻": 1.0, "防御": 1.0, "特防": 1.0, "速度": 1.0}

        # 根据性格更新修正值
        if nature in nature_table:
            for stat, modifier in nature_table[nature].items():
                modifiers[stat] = modifier

        return modifiers

    def update_character_modifiers(self):
        """更新性格修正倍率框的值"""
        try:
            # 获取当前选择的性格
            current_nature = self.CharacterComboBox.currentText()

            # 根据性格计算性格修正值
            nature_modifiers = self.get_nature_modifiers(current_nature)

            # 定义属性名称与性格修正框的映射关系
            char_edit_mapping = {
                "攻击": self.CharacterEdit_1,
                "特攻": self.CharacterEdit_2,
                "防御": self.CharacterEdit_3,
                "特防": self.CharacterEdit_4,
                "速度": self.CharacterEdit_5,
            }

            # 更新每个性格修正框的值
            for stat_name, char_edit in char_edit_mapping.items():
                modifier = nature_modifiers.get(stat_name, 1.0)  # 获取该属性的性格修正值
                if char_edit:  # 确保控件存在
                    char_edit.setText(f"{modifier:.1f}")  # 设置倍率框的值

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"更新性格修正失败: {e}")
            print(f"Error: {e}")  # 打印详细错误信息到控制台


##################### 加载自定义脚本窗口定义及初始化 #####################
class LoadScriptDialog(QDialog):
    def __init__(self, parent=None):
        super(LoadScriptDialog, self).__init__(parent)
        self.ui = Ui_LoadScriptDialogWindow()
        self.ui.setupUi(self)
        self.selected_script_path = None
        self.ui.selectFileButton.clicked.connect(self.select_file)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def select_file(self):
        """选择脚本文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择脚本文件",
            "",
            "INI Files (*.json);;All Files (*)",
            options=options
        )
        if file_path:
            self.selected_script_path = file_path
            self.ui.filePathLabel.setText(file_path)

    def get_selected_script_path(self):
        return self.selected_script_path


##################### 主窗口定义及初始化 #####################
class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, old_session):
        super(MyMainWindow, self).__init__()
        self.setupUi(self)
        # activeX控件
        self.axWidget = QAxContainer.QAxWidget(self.centralwidget)
        self.axWidget.setGeometry(QRect(-25, -20, 1024, 700))
        self.axWidget.setControl("{8856F961-340A-11D0-A96B-00C04FD705A2}")
        self.axWidget.setProperty("DisplayAlerts", False)
        self.axWidget.setProperty("DisplayScrollBars", False)

        # 登录和刷新
        self.old_session = old_session
        self.navigate_to_target()
        self.ReFresh.triggered.connect(self.refresh_page)
        # 菜单
        self.SpeedChange.triggered.connect(self.open_speed_dialog)
        self.SoundOff.triggered.connect(self.set_sound_off)
        self.StayTop.triggered.connect(self.stay_on_top)
        # 功能
        self.Calculator.triggered.connect(self.open_calculator)
        # 脚本
        self.EnableScripts.triggered.connect(self.enable_script)
        self.LoadCustomScript.triggered.connect(self.open_load_script_dialog)
        self.confirmExitDialog = ConfirmExitDialog()  # 脚本运行过程中的确认退出对话框
        if not dm:
            self.EnableScripts.setEnabled(False)
            self.LoadCustomScript.setEnabled(False)
            QMessageBox.warning(self, "提示", "脚本功能需要以管理员权限运行")
            print("大漠插件未加载，禁用脚本功能按钮")

    ######################菜单######################
    def navigate_to_target(self):
        """登录"""
        url = f'https://fanyi.youdao.com/#/TextTranslate'
        # url = f'http://b2.sjcmc.cn:16484/?sid={self.old_session}'
        print(f"生成URL: {url}")
        self.axWidget.dynamicCall("Navigate(const QString&)", url)

    def refresh_page(self):
        """刷新"""
        url = f'http://b2.sjcmc.cn:16484/?sid={self.old_session}'
        print(f"刷新URL: {url}")
        self.axWidget.dynamicCall("Navigate(const QString&)", url)

    def open_speed_dialog(self):
        """打开变速窗口"""
        dialog = SpeedControlDialog(self)
        if dialog.exec_():
            pass

    def set_sound_off(self):
        """静音"""
        global launcher_name
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.name() == f"{launcher_name}.exe":
                volume_interface = session.SimpleAudioVolume
                current_mute = volume_interface.GetMute()
                if current_mute:
                    volume_interface.SetMute(0, None)
                    self.SoundOff.setText("静音")
                else:
                    volume_interface.SetMute(1, None)
                    self.SoundOff.setText("√静音")
                break

    def stay_on_top(self):
        """主窗口置顶"""
        global global_is_stay_on_top
        if global_is_stay_on_top:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.StayTop.setText("置顶")
            global_is_stay_on_top = False
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.StayTop.setText("√置顶")
            global_is_stay_on_top = True
        # 刷新窗口状态
        self.show()

    ######################功能######################
    def open_calculator(self):
        """打开精灵计算器窗口"""
        try:
            # 检查计算器窗口是否已经存在并且是可见的
            if hasattr(self, "calculator_window") and self.calculator_window.isVisible():
                # 如果计算器窗口已打开，则将其激活并置于最前端
                self.calculator_window.activateWindow()
                self.calculator_window.raise_()
            else:
                # 创建计算器窗口实例并保存为类的属性
                self.calculator_window = CalculatorWindow(self)  # 将主窗口作为父窗口
                self.calculator_window.setWindowIcon(self.windowIcon())  # 设置与主窗口相同的图标
                self.calculator_window.show()  # 显示计算器窗口
        except Exception as e:
            # 捕获异常并显示错误消息
            QtWidgets.QMessageBox.critical(self, "错误", f"打开计算器窗口失败: {e}")
            print(f"Error: {e}")  # 打印详细错误信息到控制台

    ######################脚本######################
    def enable_script(self):
        """启用脚本"""
        global global_is_scripts_enabled, global_script_path, script_thread
        if not global_is_scripts_enabled:
            if not global_script_path:
                QMessageBox.warning(self, "提示", "请先选择脚本文件")
                return

            print("脚本功能已启用")
            self.EnableScripts.setText("√启用脚本功能")
            global_is_scripts_enabled = True

            # 创建并启动脚本线程
            script_thread = threading.Thread(target=self.run_script, daemon=True)  # 设置为守护线程
            script_thread.start()
        else:
            print("脚本功能已禁用")
            self.EnableScripts.setText("启用脚本功能")
            global_is_scripts_enabled = False

    def open_load_script_dialog(self):
        global global_script_path
        dialog = LoadScriptDialog(self)
        if dialog.exec_():
            global_script_path = dialog.get_selected_script_path()
            if global_script_path:
                print(f"加载脚本: {global_script_path}")

    def load_script_config(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return None

    def run_script(self):
        """运行脚本"""
        global global_is_scripts_enabled, dm

        try:
            if not dm:
                print("大漠插件未加载")
                QMessageBox.warning(self, "提示", "该功能需要以管理员权限运行")
                global_is_scripts_enabled = False
                return

            hwnd = int(self.winId())
            bind_result = dm.BindWindow(hwnd, "normal", "normal", "normal", 0)
            if not bind_result:
                print("窗口绑定失败")
                global_is_scripts_enabled = False
                return

            config = self.load_script_config(global_script_path)
            if not config:
                print("无法加载脚本配置文件，脚本终止")
                global_is_scripts_enabled = False
                return

            print("\n=====================脚本开始运行=====================\n")

            tasks = config.get("tasks", [])
            start_task_name = config.get("start_task", "")
            task_map = {task.get("name", f"task_{i + 1}"): task for i, task in enumerate(tasks)}
            current_task_name = start_task_name
            task_loop_counts = {}

            while global_is_scripts_enabled:
                if not current_task_name or current_task_name not in task_map:
                    print("当前任务无效，返回起始任务")
                    current_task_name = start_task_name
                    continue

                current_task = task_map.get(current_task_name, {})
                target_image = current_task.get("image", "")
                click_coords = current_task.get("coords", [])
                next_task_name = current_task.get("next_task", start_task_name)
                task_interval = current_task.get("interval", 1)
                use_image_recognition = current_task.get("use_image_recognition", True)

                if use_image_recognition and target_image:
                    # 使用图像识别定位目标
                    found = dm.FindPic(0, 0, 4000, 4000, resource_path(f"img/{target_image}"), "000000", 0.9, 0)
                    if found[1] == -1 and found[2] == -1:
                        print(f"任务 [{current_task_name}] 超时未找到图片 {target_image}，跳过此任务")
                        current_task_name = next_task_name
                        continue
                    else:
                        print(f"任务 [{current_task_name}] 识别到 {target_image}")
                        click_x, click_y = found[1], found[2]
                else:
                    # 不使用图像识别，直接使用预定义坐标
                    if isinstance(click_coords[0], int):
                        click_x, click_y = click_coords
                    elif isinstance(click_coords[0], list):
                        click_x, click_y = click_coords[0]  # 使用第一个坐标

                # 执行点击操作
                dm.MoveTo(click_x, click_y)
                dm.LeftClick()
                print(f"任务 [{current_task_name}] 点击坐标: ({click_x}, {click_y})")

                # 更新循环计数
                task_loop_counts[current_task_name] = task_loop_counts.get(current_task_name, 0) + 1
                loop_count = task_loop_counts[current_task_name]
                print(
                    f"\n=====================任务 [{current_task_name}] 当前循环计数: {loop_count} =====================\n")

                # 检查是否需要执行额外操作
                extra_action_config = current_task.get("extra_action", {})
                if extra_action_config:
                    trigger_interval = extra_action_config.get("trigger_interval", 7)
                    if loop_count % trigger_interval == 0:
                        print("[额外操作] 条件满足，准备执行额外操作")
                        self.perform_extra_action(extra_action_config)
                        print("[额外操作] 额外操作完成，继续循环")

                # 更新当前任务
                current_task_name = next_task_name

                # 等待一段时间以确保下一步目标出现
                if global_is_scripts_enabled:
                    print(f"任务 [{current_task_name}] 等待 {task_interval} 秒以确保下一步目标出现")
                    time.sleep(task_interval)

        except Exception as e:
            import traceback
            print(f"运行脚本时发生错误: {e}")
            traceback.print_exc()  # 打印完整的堆栈信息
            QMessageBox.critical(None, "错误", "脚本运行失败，请检查设置或重试！")
            global_is_scripts_enabled = False  # 确保全局状态被禁用
        finally:
            print("\n=====================脚本线程已终止=====================\n")
            global_is_scripts_enabled = False
            # 确保释放大漠插件资源

    def perform_extra_action(self, extra_action_config):
        """达到循环次数后的额外操作"""
        actions = extra_action_config.get("actions", [])
        if not actions:
            print("[额外操作] 未定义任何动作")
            return

        for i, action in enumerate(actions):
            target_image = action.get("image", "")  # 获取图片路径
            coords = action.get("coords", [])  # 获取点击坐标
            delay = action.get("delay", 0.2)  # 获取延迟时间
            use_image_recognition = action.get("use_image_recognition", False)  # 是否启用图像识别

            if use_image_recognition and target_image:
                # 使用图像识别定位目标
                if not target_image.strip():  # 检查图片路径是否为空
                    print(f"[额外操作 第{i + 1}步] 图片路径为空，跳过图像识别")
                    continue

                found = dm.FindPic(0, 0, 4000, 4000, resource_path(f"img/{target_image}"), "000000", 0.9, 0)
                if found[1] == -1 and found[2] == -1:
                    print(f"[额外操作 第{i + 1}步] 未找到图片 {target_image}，跳过此动作")
                    continue
                else:
                    print(f"[额外操作 第{i + 1}步] 识别到 {target_image}")
                    click_x, click_y = found[1], found[2]
            else:
                # 不使用图像识别，直接使用预定义坐标
                if isinstance(coords[0], int):
                    click_x, click_y = coords
                elif isinstance(coords[0], list):
                    click_x, click_y = coords[0]  # 使用第一个坐标

            try:
                print(f"[额外操作 第{i + 1}步] 点击坐标: ({click_x}, {click_y}), 延迟: {delay} 秒")
                dm.MoveTo(click_x, click_y)
                dm.LeftClick()
                time.sleep(delay)
            except Exception as e:
                print(f"[额外操作 第{i + 1}步] 执行失败: {e}")

    def closeEvent(self, event):
        """捕获窗口关闭事件"""
        global global_is_scripts_enabled, script_thread

        # 如果脚本正在运行，则弹出确认退出对话框
        if global_is_scripts_enabled and (script_thread and script_thread.is_alive()):
            try:
                # 显示确认退出对话框
                result = self.confirmExitDialog.exec_()  # 获取对话框的返回值
                if result == QtWidgets.QDialog.Accepted:  # 用户点击了“确定”
                    # 禁用脚本功能
                    global_is_scripts_enabled = False
                    print("等待脚本线程安全退出")
                    script_thread.join(timeout=5)  # 设置超时时间，防止阻塞
                    if script_thread.is_alive():
                        print("脚本线程未能及时退出，强制终止程序")
                    else:
                        print("脚本线程已终止")

                    # 关闭所有子窗口并退出程序
                    self.close_all_child_windows()
                    event.accept()  # 接受关闭事件
                else:
                    event.ignore()  # 忽略关闭事件（用户点击了“取消”或关闭了对话框）
            except Exception as e:
                print(f"关闭窗口时发生错误: {e}")
                event.ignore()  # 发生错误时忽略关闭事件
        else:
            print("脚本未运行，直接关闭窗口")
            # 如果脚本未运行，则直接关闭窗口和所有子窗口
            self.close_all_child_windows()
            event.accept()

    def close_all_child_windows(self):
        """关闭所有子窗口"""
        # 遍历所有子窗口并关闭它们
        for child_window in self.findChildren(QtWidgets.QWidget):
            if isinstance(child_window, QtWidgets.QDialog) and child_window.isVisible():
                print(f"关闭子窗口: {child_window.windowTitle()}")
                child_window.close()


##################### 重写全局异常处理函数 #####################
def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    global global_is_scripts_enabled, script_thread
    print("发生未捕获的异常，正在注销大漠插件并终止线程")
    global_is_scripts_enabled = False
    if script_thread and script_thread.is_alive():
        script_thread.join()  # 确保线程安全退出
    unregister_dm()
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


##################### 设置全局异常处理函数 #####################
sys.excepthook = handle_uncaught_exception


##################### 主函数 #####################
if __name__ == '__main__':
    # 创建应用程序实例
    app = QApplication(sys.argv)
    app_icon_path = resource_path('img/logo.ico')
    app.setWindowIcon(QIcon(app_icon_path))

    # 注册大漠插件，这里先注册是因为要在主窗口类里判断dm并禁用脚本功能按钮
    if initialize_dm():
        atexit.register(unregister_dm)

    # 如果点击了登录按钮，则弹出主窗口
    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        # 显示主窗口
        mainWindow = login_dialog.main_window
        mainWindow.setWindowIcon(QIcon(app_icon_path))
        mainWindow.show()
        # 进入主程序循环
        sys.exit(app.exec_())

    # 用户关闭了登录窗口或点击了“取消”
    else:
        print("用户关闭登录窗口，程序退出")
        sys.exit(0)  # 直接退出程序
