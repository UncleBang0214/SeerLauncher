from pynput.keyboard import Listener, Key
import threading
import time
import atexit
import json
import sys
import os
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
from Ui_EncyclopediaWindow import Ui_EncyclopediaWindow

# 全局变量定义
launcher_name = "茶杯登录器"  # 登录器名称
global_is_stay_on_top = False  # 窗口置顶状态标志
dm = None  # 大漠插件对象
global_is_scripts_enabled = False  # 脚本功能是否启用
global_script_path = None  # 当前脚本路径
script_thread = None  # 脚本线程
is_running = False  # 快捷键启停标志


def resource_path(relative_path):
    """获取资源路径"""
    if getattr(sys, 'frozen', False):  # 判断是否为打包后的exe文件
        base_path = os.path.dirname(sys.executable)  # exe文件所在目录
    else:
        base_path = os.path.abspath(".")  # 开发环境下的项目根目录
    resource_path = os.path.join(base_path, relative_path)
    return resource_path


def initialize_dm():
    """初始化大漠插件并注册为全局变量"""
    global dm
    try:
        dll_path = resource_path('ini/dm.dll')
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


def unregister_dm():
    """注销大漠插件"""
    global dm
    if dm is not None:
        print("正在注销大漠插件")
        try:
            dll_path = resource_path('ini/dm.dll')
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


def string_to_hex(s):
    """处理账号密码字符串"""
    hex_string = ''.join([format(ord(c), '02x') for c in s])
    while len(hex_string) < 24:
        hex_string = '0' + hex_string
    return hex_string


def generate_old_session(account, password):
    """根据账号密码生成oldSession"""
    account_bytes = string_to_hex(password)
    num = int(account)
    hex_string = format(num, '08x')
    old_session = hex_string + hex_string + account_bytes
    return old_session


class ConfirmExitDialog(QDialog):
    """确认退出对话框定义"""

    def __init__(self, parent=None):
        super(ConfirmExitDialog, self).__init__(parent)
        self.ui = Ui_ConfirmExitDialogWindow()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


class LoginDialog(QDialog, Ui_LoginWindow):
    """登录窗口定义及初始化"""

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


class SpeedControlDialog(QDialog, Ui_SpeedControlWindow):
    """变速窗口定义及初始化"""

    def __init__(self, parent=None):
        super(SpeedControlDialog, self).__init__(parent)
        self.setupUi(self)
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


class EncyclopediaWindow(QtWidgets.QMainWindow):
    """精灵大全"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # 初始化UI
        self.ui = Ui_EncyclopediaWindow()
        self.ui.setupUi(self)

        # 初始化配置
        self.elf_data = []
        self.current_filtered_data = []

        # 初始化表格
        self._setup_table()

        # 连接信号
        self.ui.searchEdit.textChanged.connect(self.filter_table)
        self.ui.TurnToCalculator.clicked.connect(self.open_calculator_with_data)

        # 加载数据
        self.load_data()

        self.calculator_window = None

    def _setup_table(self):
        """配置表格属性"""
        self.ui.tableWidget.setAlternatingRowColors(True)
        self.ui.tableWidget.verticalHeader().setVisible(False)
        self.ui.tableWidget.setSortingEnabled(True)
        self.ui.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.ui.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

    def load_data(self):
        """加载精灵数据"""
        try:
            data_path = self._get_data_path()

            if not os.path.exists(data_path):
                raise FileNotFoundError("数据文件不存在")

            with open(data_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                self._validate_data(raw_data)
                self.elf_data = raw_data
                self.current_filtered_data = raw_data.copy()
                self.populate_table(raw_data)

        except Exception as e:
            self._handle_load_error(e)

    def _get_data_path(self):
        """获取数据文件路径"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "ini", "encyclopedia_data.json")

    def _validate_data(self, data):
        """验证数据格式"""
        required_fields = ["序号", "名称", "体力", "攻击", "特攻", "防御", "特防", "速度", "学习力掉落"]

        for idx, item in enumerate(data):
            for field in required_fields:
                if field not in item:
                    raise ValueError(f"数据格式错误：第 {idx + 1} 条数据缺少 '{field}' 字段")

    def _handle_load_error(self, error):
        """处理加载错误"""
        error_msg = {
            FileNotFoundError: "找不到数据文件：encyclopedia_data.json",
            json.JSONDecodeError: "数据文件格式错误，请检查JSON格式",
            ValueError: str(error)
        }.get(type(error), f"未知错误：{str(error)}")

        QtWidgets.QMessageBox.critical(
            self,
            "数据加载失败",
            error_msg,
            QtWidgets.QMessageBox.Ok
        )
        self.close()

    def populate_table(self, data):
        """填充表格数据"""
        self.ui.tableWidget.setRowCount(len(data))

        for row, elf in enumerate(data):
            self._add_table_row(row, elf)

    def _add_table_row(self, row, elf):
        """添加单行数据"""
        columns = [
            str(elf["序号"]), elf["名称"],
            str(elf["体力"]), str(elf["攻击"]),
            str(elf["特攻"]), str(elf["防御"]),
            str(elf["特防"]), str(elf["速度"]),
            elf["学习力掉落"]
        ]

        for col, value in enumerate(columns):
            item = QtWidgets.QTableWidgetItem(value)
            item.setTextAlignment(QtCore.Qt.AlignCenter)

            # 序号列特殊处理
            if col == 0:
                item.setData(QtCore.Qt.UserRole, elf["序号"])

            self.ui.tableWidget.setItem(row, col, item)

    def filter_table(self, text):
        """过滤表格内容"""
        search_text = text.strip().lower()

        if not search_text:
            self.current_filtered_data = self.elf_data.copy()
        else:
            self.current_filtered_data = [
                elf for elf in self.elf_data
                if (search_text in elf["名称"].lower()) or
                   (search_text == str(elf["序号"]))
            ]

        self.populate_table(self.current_filtered_data)

    def open_calculator_with_data(self):
        """修复版本：正确传递字典参数"""
        selected = self.ui.tableWidget.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择精灵")
            return

        try:
            # 获取选中行的数据索引
            row = selected[0].row()
            elf_id = int(self.ui.tableWidget.item(row, 0).text())  # 假设第一列是序号

            # 在原始数据中查找对应的精灵
            selected_elf = next(
                elf for elf in self.elf_data
                if elf["序号"] == elf_id
            )

            # 构建参数字典
            race_data = {
                "hp": selected_elf["体力"],
                "attack": selected_elf["攻击"],
                "sp_attack": selected_elf["特攻"],
                "defense": selected_elf["防御"],
                "sp_defense": selected_elf["特防"],
                "speed": selected_elf["速度"]
            }

            # 创建/显示计算器窗口
            self.calculator_window = CalculatorWindow()

            self.calculator_window.set_race_values(**race_data)
            self.calculator_window.show()

        except StopIteration:
            QtWidgets.QMessageBox.critical(self, "错误", "找不到对应的精灵数据")
        except KeyError as e:
            QtWidgets.QMessageBox.critical(self, "数据错误", f"缺失必要字段: {str(e)}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"未知错误: {str(e)}")

    def _open_calculator(self, elf_data):
        """打开计算器窗口"""
        calculator = CalculatorWindow()
        calculator.set_race_values(
            hp=elf_data["体力"],
            attack=elf_data["攻击"],
            sp_attack=elf_data["特攻"],
            defense=elf_data["防御"],
            sp_defense=elf_data["特防"],
            speed=elf_data["速度"]
        )
        calculator.show()


class CalculatorWindow(QtWidgets.QMainWindow, Ui_CalculatorWindow):
    """计算器窗口定义及初始化"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # 添加关闭时清理引用的逻辑
        self.destroyed.connect(self._on_destroy)

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
            if field:
                field.setAlignment(QtCore.Qt.AlignCenter)

        self.CalculateButton.clicked.connect(self.calculate_stats)
        self.CharacterComboBox.currentTextChanged.connect(self.update_character_modifiers)

    # 能力值=[(种族值*2+个体值+学习力/4)×等级/100+5]*性格补正
    # HP=(种族值*2+个体值+学习力/4)×等级/100+10+等级
    def calculate_stats(self):
        try:
            level = int(self.LevelEdit.text().strip() or 100)
            iv_value = int(self.IndividualEdit.text().strip() or 31)
            stats = {
                "体力": (self.RaceEdit_1, self.EffortEdit_1, None, self.HPLabel),
                "攻击": (self.RaceEdit_2, self.EffortEdit_2, self.CharacterEdit_1, self.AttackLabel),
                "特攻": (self.RaceEdit_3, self.EffortEdit_3, self.CharacterEdit_2, self.SpAttackLabel),
                "防御": (self.RaceEdit_4, self.EffortEdit_4, self.CharacterEdit_3, self.DefenseLabel),
                "特防": (self.RaceEdit_5, self.EffortEdit_5, self.CharacterEdit_4, self.SpDefenseLabel),
                "速度": (self.RaceEdit_6, self.EffortEdit_6, self.CharacterEdit_5, self.SpeedLabel),
            }
            current_nature = self.CharacterComboBox.currentText()
            nature_modifiers = self.get_nature_modifiers(current_nature)
            for stat_name, (race_edit, effort_edit, char_edit, result_label) in stats.items():
                race_value = int(race_edit.text().strip() or 0)
                effort_value = int(effort_edit.text().strip() or 0)
                nature_modifier = nature_modifiers.get(stat_name, 1.0)
                if char_edit and stat_name != "体力":
                    char_edit.setText(f"{nature_modifier:.1f}")
                base_stat = ((race_value * 2 + iv_value + effort_value // 4) * level) // 100
                if stat_name == "体力":
                    stat_value = base_stat + level + 10
                else:
                    stat_value = base_stat + 5
                if stat_name != "体力":
                    stat_value = int(stat_value * nature_modifier)
                result_label.setText(f"{stat_value}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"计算失败: {e}")
            print(f"Error: {e}")

    def get_nature_modifiers(self, nature):
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
        modifiers = {"体力": 1.0, "攻击": 1.0, "特攻": 1.0, "防御": 1.0, "特防": 1.0, "速度": 1.0}
        if nature in nature_table:
            for stat, modifier in nature_table[nature].items():
                modifiers[stat] = modifier
        return modifiers

    def update_character_modifiers(self):
        try:
            current_nature = self.CharacterComboBox.currentText()
            nature_modifiers = self.get_nature_modifiers(current_nature)
            char_edit_mapping = {
                "攻击": self.CharacterEdit_1,
                "特攻": self.CharacterEdit_2,
                "防御": self.CharacterEdit_3,
                "特防": self.CharacterEdit_4,
                "速度": self.CharacterEdit_5,
            }
            for stat_name, char_edit in char_edit_mapping.items():
                modifier = nature_modifiers.get(stat_name, 1.0)
                if char_edit:
                    char_edit.setText(f"{modifier:.1f}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"更新性格修正失败: {e}")
            print(f"Error: {e}")

    def set_race_values(self, hp, attack, sp_attack, defense, sp_defense, speed):
        """设置种族值"""
        self.RaceEdit_1.setText(str(hp))
        self.RaceEdit_2.setText(str(attack))
        self.RaceEdit_3.setText(str(sp_attack))
        self.RaceEdit_4.setText(str(defense))
        self.RaceEdit_5.setText(str(sp_defense))
        self.RaceEdit_6.setText(str(speed))

    def _on_destroy(self):
        # 通知父窗口释放引用
        if self.parent():
            self.parent().calculator_ref = None


class LoadScriptDialog(QDialog):
    """加载自定义脚本窗口定义及初始化"""

    def __init__(self, parent=None):
        super(LoadScriptDialog, self).__init__(parent)
        self.ui = Ui_LoadScriptDialogWindow()
        self.ui.setupUi(self)
        self.selected_script_path = None
        self.ui.selectFileButton.clicked.connect(self.select_file)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def select_file(self):
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


class MyMainWindow(QMainWindow, Ui_MainWindow):
    """主窗口定义及初始化"""

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
        self.Encyclopedia.triggered.connect(self.open_encyclopedia)
        self.Calculator.triggered.connect(self.open_calculator)
        # 脚本
        self.EnableScripts.triggered.connect(self.enable_script)
        self.LoadCustomScript.triggered.connect(self.open_load_script_dialog)
        self.confirmExitDialog = ConfirmExitDialog()
        if not dm:
            self.EnableScripts.setEnabled(False)
            self.LoadCustomScript.setEnabled(False)
            QMessageBox.warning(self, "提示", "脚本功能需要以管理员权限运行")
            print("大漠插件未加载，禁用脚本功能按钮")
        # 键盘监听器
        self.start_keyboard_listener()

    # 登录
    def navigate_to_target(self):
        # url = f'https://fanyi.youdao.com/#/TextTranslate'
        url = f'http://b2.sjcmc.cn:16484/?sid={self.old_session}'
        print(f"生成URL: {url}")
        self.axWidget.dynamicCall("Navigate(const QString&)", url)

    # 刷新
    def refresh_page(self):
        url = f'http://b2.sjcmc.cn:16484/?sid={self.old_session}'
        print(f"刷新URL: {url}")
        self.axWidget.dynamicCall("Navigate(const QString&)", url)

    # 变速输入框
    def open_speed_dialog(self):
        dialog = SpeedControlDialog(self)
        if dialog.exec_():
            pass

    # 静音
    def set_sound_off(self):
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

    # 窗口置顶
    def stay_on_top(self):
        global global_is_stay_on_top
        if global_is_stay_on_top:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            self.StayTop.setText("置顶")
            global_is_stay_on_top = False
        else:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.StayTop.setText("√置顶")
            global_is_stay_on_top = True
        self.show()

    # 精灵大全窗口
    def open_encyclopedia(self):
        self.encyclopedia_window = EncyclopediaWindow(self)
        self.encyclopedia_window.setWindowIcon(self.windowIcon())
        self.encyclopedia_window.show()

    # 精灵计算器窗口
    def open_calculator(self):
        self.calculator_window = CalculatorWindow(self)
        self.calculator_window.setWindowIcon(self.windowIcon())
        self.calculator_window.show()

    # 启停脚本
    def enable_script(self):
        global global_is_scripts_enabled, global_script_path, script_thread, is_running
        if not global_is_scripts_enabled:
            if not global_script_path:
                QMessageBox.warning(self, "提示", "请先选择脚本文件")
                return
            print("脚本功能已启用")
            self.EnableScripts.setText("√启用脚本功能")
            global_is_scripts_enabled = True
            is_running = True
            script_thread = threading.Thread(target=self.run_script, daemon=True)
            script_thread.start()
        else:
            print("脚本功能已禁用")
            self.EnableScripts.setText("启用脚本功能")
            global_is_scripts_enabled = False
            is_running = False

    # 选定脚本窗口
    def open_load_script_dialog(self):
        global global_script_path
        dialog = LoadScriptDialog(self)
        if dialog.exec_():
            global_script_path = dialog.get_selected_script_path()
            if global_script_path:
                print(f"加载脚本: {global_script_path}")

    # 加载脚本
    def load_script_config(self, config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return None

    # 键盘监听器
    def start_keyboard_listener(self):
        listener = Listener(on_press=self.on_press)
        listener.start()

    # 快捷键启停脚本
    def on_press(self, key):
        global is_running, global_is_scripts_enabled
        try:
            if key == Key.f9:
                if is_running:
                    # 如果脚本正在运行，停止脚本
                    is_running = False
                    global_is_scripts_enabled = False
                    self.EnableScripts.setText("启用脚本功能")
                    print("脚本已通过快捷键停止")
                else:
                    # 如果脚本未运行，启动脚本
                    if not global_script_path:
                        return
                    is_running = True
                    global_is_scripts_enabled = True
                    self.EnableScripts.setText("√启用脚本功能")
                    print("脚本已通过快捷键启动")
                    # 启动脚本线程
                    script_thread = threading.Thread(target=self.run_script, daemon=True)
                    script_thread.start()
        except AttributeError:
            pass

    # 识图点击逻辑
    def run_script(self):
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

            # 加载脚本配置
            config = self.load_script_config(global_script_path)
            if not config:
                print("无法加载脚本配置文件，脚本终止")
                global_is_scripts_enabled = False
                return

            print("=====================脚本开始运行=====================")

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

                print(f"\n=====================任务 [{current_task_name}] 开始执行=====================")

                # 图像识别逻辑
                if use_image_recognition and target_image:
                    found = dm.FindPic(0, 0, 4000, 4000, resource_path(f"img/{target_image}"), "000000", 0.9, 0)
                    if found[1] == -1 and found[2] == -1:
                        print(f"任务 [{current_task_name}] 超时未找到图片 {target_image}，跳过此任务")
                        current_task_name = next_task_name
                        continue
                    else:
                        print(f"任务 [{current_task_name}] 识别到 {target_image}")

                # 点击坐标逻辑
                if isinstance(click_coords[0], int):  # 单个坐标
                    click_x, click_y = click_coords
                    dm.MoveTo(click_x, click_y)
                    dm.LeftClick()
                    print(f"任务 [{current_task_name}] 点击坐标: ({click_x}, {click_y})")
                elif isinstance(click_coords[0], list):  # 多个坐标
                    for i, coord in enumerate(click_coords):
                        click_x, click_y = coord
                        dm.MoveTo(click_x, click_y)
                        dm.LeftClick()
                        print(f"任务 [{current_task_name}] 第 {i + 1} 次点击坐标: ({click_x}, {click_y})")
                        time.sleep(0.2)  # 添加短暂停顿以避免过于频繁的操作

                # 更新循环计数
                task_loop_counts[current_task_name] = task_loop_counts.get(current_task_name, 0) + 1
                loop_count = task_loop_counts[current_task_name]
                print(
                    f"\n=====================任务 [{current_task_name}] 当前循环计数: {loop_count} =====================\n")

                # 执行额外操作
                extra_action_config = current_task.get("extra_action", {})
                if extra_action_config:
                    trigger_interval = extra_action_config.get("trigger_interval", 7)
                    if loop_count % trigger_interval == 0:
                        print(
                            f"[额外操作] 条件满足 (循环计数 {loop_count} % 触发间隔 {trigger_interval} == 0)，准备执行额外操作")
                        self.perform_extra_action(extra_action_config)
                        print("[额外操作] 额外操作完成，继续循环")
                    else:
                        print(
                            f"[额外操作] 当前循环计数 {loop_count} 不满足触发条件 (触发间隔 {trigger_interval})，跳过额外操作")
                else:
                    print(f"[额外操作] 当前任务 [{current_task_name}] 未配置额外操作，跳过")

                # 跳转到下一个任务
                current_task_name = next_task_name
                if global_is_scripts_enabled:
                    print(f"任务 [{current_task_name}] 等待 {task_interval} 秒以确保下一步目标出现")
                    time.sleep(task_interval)

        except Exception as e:
            import traceback
            print(f"运行脚本时发生错误: {e}")
            traceback.print_exc()
            QMessageBox.critical(None, "错误", "脚本运行失败，请检查设置或重试！")
            global_is_scripts_enabled = False
        finally:
            print("\n=====================脚本线程已终止=====================\n")
            global_is_scripts_enabled = False

    # 执行额外操作逻辑
    def perform_extra_action(self, extra_action_config):
        steps = extra_action_config.get("actions", [])  # 使用 "actions" 字段
        if not steps:
            print("[额外操作] 未配置任何操作步骤，跳过额外操作")
            return

        for step_index, step in enumerate(steps):
            target_image = step.get("image", "")
            click_coords = step.get("coords", [])
            use_image_recognition = step.get("use_image_recognition", "True") == "True"
            delay = step.get("delay", 0.3)

            print(f"[额外操作 第{step_index + 1}步] 开始执行")

            # 图像识别逻辑
            if use_image_recognition and target_image:
                found = dm.FindPic(0, 0, 4000, 4000, resource_path(f"img/{target_image}"), "000000", 0.9, 0)
                if found[1] == -1 and found[2] == -1:
                    print(f"[额外操作 第{step_index + 1}步] 未找到图片 {target_image}，跳过点击")
                else:
                    print(f"[额外操作 第{step_index + 1}步] 识别到 {target_image}")

            # 点击坐标逻辑
            if isinstance(click_coords[0], int):  # 单个坐标
                click_x, click_y = click_coords
                dm.MoveTo(click_x, click_y)
                dm.LeftClick()
                print(f"[额外操作 第{step_index + 1}步] 点击坐标: ({click_x}, {click_y}), 延迟: {delay} 秒")
            elif isinstance(click_coords[0], list):  # 多个坐标
                for i, coord in enumerate(click_coords):
                    click_x, click_y = coord
                    dm.MoveTo(click_x, click_y)
                    dm.LeftClick()
                    print(
                        f"[额外操作 第{step_index + 1}步] 第 {i + 1} 次点击坐标: ({click_x}, {click_y}), 延迟: {delay} 秒")
                    time.sleep(delay)

            # 等待延迟
            time.sleep(delay)

        print("[额外操作] 额外操作完成，继续循环")

    # 重写关闭窗口事件
    def closeEvent(self, event):
        global global_is_scripts_enabled, script_thread
        if global_is_scripts_enabled and (script_thread and script_thread.is_alive()):
            try:
                result = self.confirmExitDialog.exec_()
                if result == QtWidgets.QDialog.Accepted:
                    global_is_scripts_enabled = False
                    print("等待脚本线程安全退出")
                    script_thread.join(timeout=5)
                    if script_thread.is_alive():
                        print("脚本线程未能及时退出，强制终止程序")
                    else:
                        print("脚本线程已终止")
                    self.close_all_child_windows()
                    event.accept()
                else:
                    event.ignore()
            except Exception as e:
                print(f"关闭窗口时发生错误: {e}")
                event.ignore()
        else:
            print("脚本未运行，直接关闭窗口")
            self.close_all_child_windows()
            event.accept()

    # 关闭所有子窗口
    def close_all_child_windows(self):
        for child_window in self.findChildren(QtWidgets.QWidget):
            if isinstance(child_window, QtWidgets.QDialog) and child_window.isVisible():
                print(f"关闭子窗口: {child_window.windowTitle()}")
                child_window.close()
        for window in QApplication.topLevelWidgets():
            if window != self and window.isVisible():
                print(f"关闭游离窗口: {window.windowTitle()}")
                window.close()


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """重写全局异常处理函数"""
    global global_is_scripts_enabled, script_thread
    print("发生未捕获的异常，正在注销大漠插件并终止线程")
    global_is_scripts_enabled = False
    if script_thread and script_thread.is_alive():
        script_thread.join()
    unregister_dm()
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


# 注册全局异常处理函数
sys.excepthook = handle_uncaught_exception

if __name__ == '__main__':
    """主函数"""
    app = QApplication(sys.argv)
    app_icon_path = resource_path('img/logo.ico')
    app.setWindowIcon(QIcon(app_icon_path))
    if initialize_dm():
        atexit.register(unregister_dm)
    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        mainWindow = login_dialog.main_window
        mainWindow.setWindowIcon(QIcon(app_icon_path))
        mainWindow.show()
        sys.exit(app.exec_())
    else:
        print("用户关闭登录窗口，程序退出")
        sys.exit(0)
