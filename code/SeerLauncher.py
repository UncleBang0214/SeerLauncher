import requests
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
from PyQt5.QtWidgets import QMainWindow, QApplication, QDialog, QMessageBox, QFileDialog, QComboBox, QVBoxLayout, \
    QScrollArea, QWidget, QLabel, QDialogButtonBox, QGraphicsDropShadowEffect
from PyQt5.QtGui import QIcon, QColor
from Ui_MainWindow import Ui_MainWindow
from Ui_OnStartDialogWindow import Ui_OnStartDialogWindow
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


class OnStartDialog(QtWidgets.QDialog, Ui_OnStartDialogWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.ok_btn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Ok)
        self.ok_btn.setText("同意并继续")
        self.cancel_btn = self.buttonBox.button(QtWidgets.QDialogButtonBox.Cancel)
        self.cancel_btn.setText("拒绝并退出")


class LoginService:
    LOGIN_URL = "http://m9.ctymc.cn:20672/seer/customer/login"
    GAME_URL_TEMPLATE = "http://b2.sjcmc.cn:16484/?sid={session}"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
            "Origin": "http://http://seer.xin/",
            "Referer": "http://http://seer.xin/",
            "Content-Type": "application/json;charset=UTF-8"
        })

    def login(self, email: str, password: str) -> dict:
        """执行登录并返回认证数据"""
        payload = {
            "email": email,
            "password": password.strip()
        }

        try:
            response = self.session.post(
                self.LOGIN_URL,
                json=payload,
                timeout=10,
                verify=False  # 忽略SSL证书验证
            )

            if response.status_code != 200:
                raise Exception(f"HTTP错误码: {response.status_code}")

            result = response.json()
            if result.get('code') != 200:
                raise Exception(result.get('msg', '未知登录错误'))

            return {
                "session": result['session'],
                "token": result['token'],
                "permissions": result['permissions']
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"网络请求失败: {str(e)}")


def string_to_hex(s):
    """处理账号密码字符串"""
    hex_string = ''.join([format(ord(c), '02x') for c in s])
    while len(hex_string) < 24:
        hex_string = '0' + hex_string
    return hex_string


class ConfirmExitDialog(QDialog):
    """确认退出对话框定义"""

    def __init__(self, parent=None):
        super(ConfirmExitDialog, self).__init__(parent)
        self.ui = Ui_ConfirmExitDialogWindow()
        self.ui.setupUi(self)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)


class LoginDialog(QDialog, Ui_LoginWindow):

    def __init__(self, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.setupUi(self)

        # 初始化存储配置
        self.history_file = resource_path('ini/login.json')
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

        # 初始化界面
        self.init_ui()
        self.load_history()

        # 连接信号
        self.confirmButton.clicked.connect(self.handle_login)
        self.accountEdit.currentTextChanged.connect(self.clear_password)

    def init_ui(self):
        """初始化界面设置"""
        # 设置下拉框特性
        self.accountEdit.setEditable(True)
        self.accountEdit.setInsertPolicy(QComboBox.InsertAtTop)

        # 保持你原有的窗口图标设置
        self.setWindowIcon(self.windowIcon())

    def load_history(self):
        """加载历史账号"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.accountEdit.addItems(data.get("history_accounts", []))
        except Exception as e:
            QMessageBox.warning(self, "警告", f"历史记录加载失败: {str(e)}")

    def save_history(self, account):
        """保存账号到历史记录"""
        try:
            # 获取现有账号（去重处理）
            history = []
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f).get("history_accounts", [])

            # 更新历史记录
            if account not in history:
                history.insert(0, account)
                history = history[:10]  # 保留最近10个账号

                # 写入文件
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump({"history_accounts": history}, f, indent=2)

                # 更新下拉框
                self.accountEdit.insertItem(0, account)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存失败: {str(e)}")

    def clear_password(self):
        """切换账号时清空密码"""
        self.passwordEdit.clear()

    def handle_login(self):
        """处理登录按钮点击"""
        account = self.accountEdit.currentText().strip()
        password = self.passwordEdit.text().strip()

        if not self._validate_input(account, password):
            return

        try:
            service = LoginService()
            auth_data = service.login(account, password)
            self.save_history(account)
            # 拼接URL
            game_url = service.GAME_URL_TEMPLATE.format(session=auth_data['session'])
            print("生成地址:", game_url)

            # 启动主窗口
            self.main_window = MyMainWindow(auth_data)
            self.main_window.show()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "登录失败", f"错误详情: {str(e)}")
            self._clear_password_field()

    def _validate_input(self, email: str, password: str) -> bool:
        """输入验证"""
        if not email or not password:
            QMessageBox.warning(self, "输入错误", "邮箱或密码不能为空")
            return False

        if "@" not in email or "." not in email.split("@")[-1]:
            QMessageBox.warning(self, "格式错误", "请输入有效的邮箱地址")
            return False

        if len(password) < 6:
            QMessageBox.warning(self, "密码过短", "密码长度不能少于6位")
            return False

        return True

    def _clear_password_field(self):
        """清空密码输入"""
        self.passwordEdit.clear()
        self.passwordEdit.setFocus()


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
    """精灵大全（完整功能版）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_EncyclopediaWindow()
        self.ui.setupUi(self)

        # 初始化数据
        self.elf_data = []
        self.current_filtered_data = []

        # 初始化界面
        self._setup_table()
        self.load_data()

        # 连接信号
        self.ui.searchEdit.textChanged.connect(self.filter_table)
        self.ui.TurnToCalculator.clicked.connect(self.open_calculator_with_data)

    def _setup_table(self):
        """配置表格属性"""
        self.ui.tableWidget.setColumnCount(10)
        self.ui.tableWidget.setHorizontalHeaderLabels([
            "序号", "名称", "体力", "攻击", "特攻",
            "防御", "特防", "速度", "总和", "学习力掉落"
        ])
        self.ui.tableWidget.setSortingEnabled(True)
        self.ui.tableWidget.setAlternatingRowColors(True)
        self.ui.tableWidget.verticalHeader().setVisible(False)
        self.ui.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

    def load_data(self):
        """加载数据"""
        try:
            with open(self._get_data_path(), 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                self._validate_data(raw_data)
                self.elf_data = raw_data
                self.current_filtered_data = raw_data.copy()
                self.populate_table(raw_data)
        except Exception as e:
            self._handle_load_error(e)

    def _get_data_path(self):
        data_path = resource_path("ini/encyclopedia.json")
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"数据文件缺失: {data_path}")
        return data_path

    def _validate_data(self, data):
        """数据验证"""
        required_fields = ["序号", "名称", "体力", "攻击", "特攻",
                           "防御", "特防", "速度", "学习力掉落"]
        for idx, item in enumerate(data):
            for field in required_fields:
                if field not in item:
                    raise ValueError(f"数据格式错误：第 {idx + 1} 条数据缺少 '{field}' 字段")

    def populate_table(self, data):
        """填充表格"""
        self.ui.tableWidget.setRowCount(len(data))
        for row, elf in enumerate(data):
            self._add_table_row(row, elf)

    def _add_table_row(self, row, elf):
        """添加单行数据（含总和计算）"""
        # 计算种族值总和
        total = sum([
            elf["体力"], elf["攻击"], elf["特攻"],
            elf["防御"], elf["特防"], elf["速度"]
        ])

        columns = [
            str(elf["序号"]), elf["名称"],
            str(elf["体力"]), str(elf["攻击"]),
            str(elf["特攻"]), str(elf["防御"]),
            str(elf["特防"]), str(elf["速度"]),
            str(total),  # 总和列
            elf["学习力掉落"]
        ]

        for col, value in enumerate(columns):
            item = QtWidgets.QTableWidgetItem(value)
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            if col == 0:  # 序号列存储原始数据
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
        """打开计算器窗口"""
        selected = self.ui.tableWidget.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选择精灵")
            return

        try:
            row = selected[0].row()
            elf_id = int(self.ui.tableWidget.item(row, 0).text())
            selected_elf = next(elf for elf in self.elf_data if elf["序号"] == elf_id)

            # 创建计算器窗口
            self.calculator_window = CalculatorWindow()
            self.calculator_window.set_race_values(
                hp=selected_elf["体力"],
                attack=selected_elf["攻击"],
                sp_attack=selected_elf["特攻"],
                defense=selected_elf["防御"],
                sp_defense=selected_elf["特防"],
                speed=selected_elf["速度"]
            )
            self.calculator_window.show()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"无法打开计算器: {str(e)}")

    def _handle_load_error(self, error):
        """处理加载错误"""
        error_msg = {
            FileNotFoundError: "找不到数据文件：encyclopedia.json",
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


class CalculatorWindow(QtWidgets.QMainWindow, Ui_CalculatorWindow):
    """精灵计算器（完整功能版）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        # 初始化设置
        self._connect_signals()
        self._init_character_box()

        # 设置默认值
        self.LevelEdit.setText("100")
        self.IndividualEdit.setText("31")
        self._init_default_values()

    def _connect_signals(self):
        """连接信号"""
        # 种族值变化信号
        race_edits = [
            self.RaceEdit_1, self.RaceEdit_2, self.RaceEdit_3,
            self.RaceEdit_4, self.RaceEdit_5, self.RaceEdit_6
        ]
        for edit in race_edits:
            edit.textChanged.connect(self._update_total)

        # 计算按钮
        self.CalculateButton.clicked.connect(self.calculate_stats)

        # 性格选择
        self.CharacterComboBox.currentTextChanged.connect(self.update_character_modifiers)

    def _init_character_box(self):
        """初始化性格下拉框"""
        self.CharacterComboBox.addItems([
            "固执", "孤独", "调皮", "勇敢", "保守", "稳重",
            "马虎", "冷静", "胆小", "开朗", "急躁", "天真",
            "大胆", "顽皮", "无虑", "悠闲", "沉着", "慎重",
            "温顺", "狂妄", "害羞", "实干", "认真", "浮躁", "坦率"
        ])

    def _init_default_values(self):
        """初始化默认值"""
        for edit in [self.RaceEdit_1, self.RaceEdit_2, self.RaceEdit_3,
                     self.RaceEdit_4, self.RaceEdit_5, self.RaceEdit_6]:
            edit.setText("0")
        self._update_total()

    def _update_total(self):
        """更新种族值总和"""
        try:
            total = sum([
                int(self.RaceEdit_1.text() or 0),
                int(self.RaceEdit_2.text() or 0),
                int(self.RaceEdit_3.text() or 0),
                int(self.RaceEdit_4.text() or 0),
                int(self.RaceEdit_5.text() or 0),
                int(self.RaceEdit_6.text() or 0)
            ])
            self.SumEdit.setText(str(total))
        except ValueError:
            self.SumEdit.setText("0")

    def set_race_values(self, hp, attack, sp_attack, defense, sp_defense, speed):
        """设置种族值"""
        self.RaceEdit_1.setText(str(hp))
        self.RaceEdit_2.setText(str(attack))
        self.RaceEdit_3.setText(str(sp_attack))
        self.RaceEdit_4.setText(str(defense))
        self.RaceEdit_5.setText(str(sp_defense))
        self.RaceEdit_6.setText(str(speed))
        self._update_total()

    def calculate_stats(self):
        """计算能力值"""
        try:
            # 获取基础值
            level = int(self.LevelEdit.text())
            iv = int(self.IndividualEdit.text())

            # 获取种族值
            race_values = {
                "体力": int(self.RaceEdit_1.text()),
                "攻击": int(self.RaceEdit_2.text()),
                "特攻": int(self.RaceEdit_3.text()),
                "防御": int(self.RaceEdit_4.text()),
                "特防": int(self.RaceEdit_5.text()),
                "速度": int(self.RaceEdit_6.text())
            }

            # 获取性格修正
            nature = self.CharacterComboBox.currentText()
            modifiers = self.get_nature_modifiers(nature)

            # 计算各项能力值
            results = {}
            for stat in ["体力", "攻击", "特攻", "防御", "特防", "速度"]:
                base = (race_values[stat] * 2 + iv + int(self._get_effort(stat)) // 4) * level // 100

                if stat == "体力":
                    results[stat] = base + 10 + level
                else:
                    results[stat] = int((base + 5) * modifiers[stat])

            # 更新界面
            self.HPLabel.setText(str(results["体力"]))
            self.AttackLabel.setText(str(results["攻击"]))
            self.SpAttackLabel.setText(str(results["特攻"]))
            self.DefenseLabel.setText(str(results["防御"]))
            self.SpDefenseLabel.setText(str(results["特防"]))
            self.SpeedLabel.setText(str(results["速度"]))

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "计算错误", f"输入数据无效: {str(e)}")

    def _get_effort(self, stat):
        """获取努力值输入"""
        effort_mapping = {
            "体力": self.EffortEdit_1,
            "攻击": self.EffortEdit_2,
            "特攻": self.EffortEdit_3,
            "防御": self.EffortEdit_4,
            "特防": self.EffortEdit_5,
            "速度": self.EffortEdit_6
        }
        return effort_mapping[stat].text() or "0"

    def get_nature_modifiers(self, nature):
        """获取性格修正系数"""
        nature_table = {
            # 攻击↑ 特攻↓
            "固执": {"攻击": 1.1, "特攻": 0.9},
            "孤独": {"攻击": 1.1, "防御": 0.9},
            "调皮": {"攻击": 1.1, "特防": 0.9},
            "勇敢": {"攻击": 1.1, "速度": 0.9},

            # 特攻↑ 攻击↓
            "保守": {"特攻": 1.1, "攻击": 0.9},
            "稳重": {"特攻": 1.1, "防御": 0.9},
            "马虎": {"特攻": 1.1, "特防": 0.9},
            "冷静": {"特攻": 1.1, "速度": 0.9},

            # 速度↑
            "胆小": {"速度": 1.1, "攻击": 0.9},
            "开朗": {"速度": 1.1, "特攻": 0.9},
            "急躁": {"速度": 1.1, "防御": 0.9},
            "天真": {"速度": 1.1, "特防": 0.9},

            # 防御↑
            "大胆": {"防御": 1.1, "攻击": 0.9},
            "顽皮": {"防御": 1.1, "特攻": 0.9},
            "无虑": {"防御": 1.1, "特防": 0.9},
            "悠闲": {"防御": 1.1, "速度": 0.9},

            # 特防↑
            "沉着": {"特防": 1.1, "攻击": 0.9},
            "慎重": {"特防": 1.1, "特攻": 0.9},
            "温顺": {"特防": 1.1, "防御": 0.9},
            "狂妄": {"特防": 1.1, "速度": 0.9},

            # 无修正
            "害羞": {},
            "实干": {},
            "认真": {},
            "浮躁": {},
            "坦率": {}
        }
        modifiers = {"体力": 1.0, "攻击": 1.0, "特攻": 1.0,
                     "防御": 1.0, "特防": 1.0, "速度": 1.0}
        if nature in nature_table:
            modifiers.update(nature_table[nature])
        return modifiers

    def update_character_modifiers(self):
        """更新性格修正显示"""
        try:
            nature = self.CharacterComboBox.currentText()
            modifiers = self.get_nature_modifiers(nature)

            self.CharacterEdit_1.setText(f"{modifiers['攻击']:.1f}")
            self.CharacterEdit_2.setText(f"{modifiers['特攻']:.1f}")
            self.CharacterEdit_3.setText(f"{modifiers['防御']:.1f}")
            self.CharacterEdit_4.setText(f"{modifiers['特防']:.1f}")
            self.CharacterEdit_5.setText(f"{modifiers['速度']:.1f}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "错误", f"无法更新性格修正: {str(e)}")


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


class MessageDialog(QDialog):
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 300)

        # 主布局
        main_layout = QVBoxLayout()

        # 滚动区域
        scroll = QScrollArea()
        content_widget = QWidget()
        content_layout = QVBoxLayout()

        # 内容标签
        lbl_content = QLabel(content)
        lbl_content.setWordWrap(True)
        lbl_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lbl_content.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # 组装滚动区域
        content_layout.addWidget(lbl_content)
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        scroll.setWidgetResizable(True)

        # 按钮组
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Close)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        ok_btn.setText('确定')
        close_btn = btn_box.button(QDialogButtonBox.Close)
        close_btn.setText('关闭')

        # 最终布局
        main_layout.addWidget(scroll)
        main_layout.addWidget(btn_box)
        self.setLayout(main_layout)


class MyMainWindow(QMainWindow, Ui_MainWindow):
    """主窗口定义及初始化"""

    def __init__(self, auth_data: dict):
        super(MyMainWindow, self).__init__()
        self.setupUi(self)

        # 登录
        self.auth_data = auth_data
        self.init_components()
        self.ReFresh.triggered.connect(self.refresh_page)
        # 菜单
        self.SpeedChange.triggered.connect(self.open_speed_dialog)
        # self.SpeedChange.setEnabled(False) # 后续可能要关闭变速功能
        self.SoundOff.triggered.connect(self.set_sound_off)
        self.StayTop.triggered.connect(self.stay_on_top)
        self.CleanCache.triggered.connect(self.clear_cache)
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
        # 关于
        self.About.triggered.connect(self.open_about)
        self.UpdateLog.triggered.connect(self.open_updatelog)

    def init_components(self):
        """初始化浏览器组件"""
        self.axWidget = QAxContainer.QAxWidget(self.centralwidget)
        self.axWidget.setGeometry(QRect(-25, -20, 1024, 700))
        self.axWidget.setControl("{8856F961-340A-11D0-A96B-00C04FD705A2}")
        self.navigate_to_game()

    # 登录
    def navigate_to_game(self):
        game_url = LoginService.GAME_URL_TEMPLATE.format(session=self.auth_data['session'])
        print("加载:", game_url)
        self.axWidget.dynamicCall("Navigate(const QString&)", game_url)

    # 刷新
    def refresh_page(self):
        game_url = LoginService.GAME_URL_TEMPLATE.format(session=self.auth_data['session'])
        print("刷新:", game_url)
        self.axWidget.dynamicCall("Navigate(const QString&)", game_url)

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

    # 清理IE浏览器缓存
    def clear_cache(self):
        try:
            # 使用系统命令清理IE缓存（需要管理员权限）
            # 255对应所有缓存类型：历史记录、Cookies、临时文件、表单数据、密码等
            command = 'RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess 255'

            # 执行清理命令
            result = os.system(command)

            # 检查执行结果
            if result == 0:
                QMessageBox.information(
                    self,
                    "清理成功",
                    "IE浏览器缓存已清理！\n\n注意：部分系统可能需要管理员权限才能完全清除",
                    QMessageBox.Ok
                )
            else:
                QMessageBox.warning(
                    self,
                    "清理失败",
                    "缓存清理未完全成功，请尝试：\n1. 以管理员身份运行登录器\n2. 手动清理浏览器缓存",
                    QMessageBox.Ok
                )

            # 附加清理：删除Temporary Internet Files目录内容
            temp_path = os.path.join(
                os.environ['USERPROFILE'],
                'AppData\\Local\\Microsoft\\Windows\\INetCache\\IE'
            )
            if os.path.exists(temp_path):
                for root, dirs, files in os.walk(temp_path):
                    for file in files:
                        try:
                            os.remove(os.path.join(root, file))
                        except Exception as e:
                            print(f"删除文件失败 {file}: {str(e)}")
                    for dir in dirs:
                        try:
                            os.rmdir(os.path.join(root, dir))
                        except Exception as e:
                            print(f"删除目录失败 {dir}: {str(e)}")
                print("已手动清理临时文件目录")

        except Exception as e:
            QMessageBox.critical(
                self,
                "发生错误",
                f"清理过程中出现异常：{str(e)}",
                QMessageBox.Ok
            )

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

    # 关于登录器
    def open_about(self):
        about_content = """
        <h2>关于茶杯登录器</h2>
        <p>版本：v1.0.0</p>
        <p>开发者：小茶杯</p>
        <p>描述：</p>
        <p>下班闲暇之余制作，开发该登录器旨在优化各位的游玩体验</p>
        <p>纯公益项目，不接受任何形式的赞助！！！</p>
        <p>通过任何付费途径获得此软件均为上当受骗！！！</p>
        """

        dialog = MessageDialog("关于", about_content, self)
        dialog.exec_()

    # 关于更新日志
    def open_updatelog(self):
        update_content = """
        <h2>登录器更新日志</h2>
        <h3>v1.0.0 (2025-03-03)</h3>
        <ul>
            <li>新增清理缓存功能、UI美化、免责条款</li>
        </ul>
        <h3>v0.9.9 (2025-02-28)</h3>
        <ul>
            <li>新增本地账号存储（不包含密码）、登录器信息</li>
        </ul>
        <h3>v0.9.8 (2025-02-27)</h3>
        <ul>
            <li>新增爬虫，完善精灵大全格式，重构登录逻辑</li>
        </ul>
        <h3>v0.9.7 (2025-02-25)</h3>
        <ul>
            <li>新增精灵大全，支持查询、计算器联动</li>
        </ul>
        <h3>v0.9.6 (2025-02-23)</h3>
        <ul>
            <li>新增快捷键启停脚本，完善识图点击逻辑，额外操作支持识图和循环执行</li>
        </ul>
        <h3>v0.9.5 (2025-02-19)</h3>
        <ul>
            <li>新增精灵能力值计算器</li>
        </ul>
        <h3>v0.9.4 (2025-02-14)</h3>
        <ul>
            <li>新增加载定义脚本功能，支持自主启停，支持自定义编写json脚本</li>
        </ul>
        <h3>v0.9.3 (2025-02-10)</h3>
        <ul>
            <li>新增静音功能，制作识图点击脚本雏形</li>
        </ul>
        <h3>v0.9.2 (2025-02-07)</h3>
        <ul>
            <li>基于1920*1080分辨率调整窗口大小，添加窗口logo</li>
        </ul>
        <h3>v0.9.1 (2025-02-05)</h3>
        <ul>
            <li>新增独立的登录窗口，实现了变速功能</li>
        </ul>
        <h3>v0.9.0 (2025-02-04)</h3>
        <ul>
            <li>实现了加载页面、刷新和绕过登录</li>
        </ul>
        """

        dialog = MessageDialog("更新日志", update_content, self)
        dialog.exec_()

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
                    found = dm.FindPic(0, 0, 4000, 4000, resource_path(target_image), "000000", 0.9, 0)
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
                found = dm.FindPic(0, 0, 4000, 4000, resource_path(target_image), "000000", 0.9, 0)
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

    # 免责声明
    start_dialog = OnStartDialog()
    if start_dialog.exec_() != QDialog.Accepted:
        print("用户取消启动流程")
        sys.exit(0)

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
