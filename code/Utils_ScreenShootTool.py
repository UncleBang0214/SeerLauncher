import sys
import win32api
import win32gui
import win32con
from PIL import ImageGrab
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize
from PyQt5.QtGui import QPixmap, QPainter, QPen, QCursor, QColor


class CaptureTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.bound_hwnd = None
        self.capture_rect = None
        self.drawing = False
        self.start_pos = QPoint()
        self.end_pos = QPoint()
        self.is_binding = False  # 绑定状态标志

        # 设置定时器刷新截图
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        self.timer.start(100)  # 100ms刷新间隔

    def init_ui(self):
        self.setWindowTitle("茶杯截图工具 - V1.1")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # 主控件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # 控件布局
        layout = QVBoxLayout()
        self.preview_label = QLabel("请先绑定窗口")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(QSize(400, 300))

        # 信息显示栏
        info_layout = QHBoxLayout()
        self.status_label = QLabel("未绑定窗口")
        self.coord_label = QLabel("坐标：N/A")
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        info_layout.addWidget(self.coord_label)

        # 按钮组
        btn_layout = QHBoxLayout()
        self.bind_btn = QPushButton("绑定窗口")
        self.bind_btn.clicked.connect(self.start_bind_window)
        self.save_btn = QPushButton("保存截图")
        self.save_btn.clicked.connect(self.save_screenshot)
        btn_layout.addWidget(self.bind_btn)
        btn_layout.addWidget(self.save_btn)

        layout.addWidget(self.preview_label)
        layout.addLayout(info_layout)
        layout.addLayout(btn_layout)
        main_widget.setLayout(layout)

        # 初始化保存按钮状态
        self.save_btn.setEnabled(False)

    def start_bind_window(self):
        """开始绑定窗口的改进流程"""
        self.is_binding = True
        self.status_label.setText("请点击要绑定的窗口...")

        # 隐藏主窗口以便选择其他窗口
        self.hide()  # 关键改进：隐藏自身窗口
        QApplication.processEvents()  # 立即处理界面更新

        # 设置系统级鼠标钩子（需要管理员权限）
        self.setMouseTracking(True)
        win32api.SetCursor(win32api.LoadCursor(0, win32con.IDC_CROSS))

    def update_preview(self):
        if self.bound_hwnd and win32gui.IsWindow(self.bound_hwnd):
            try:
                # 获取窗口位置和大小
                rect = win32gui.GetWindowRect(self.bound_hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top

                # 截图并显示
                screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
                qim = QPixmap.fromImage(
                    screenshot.toqimage().copy(0, 0, width, height))

                # 绘制光标坐标
                painter = QPainter(qim)
                pen = QPen(QColor(255, 0, 0, 150), 2)  # 半透明红色
                painter.setPen(pen)

                # 获取相对坐标
                cursor_pos = win32api.GetCursorPos()
                rel_x = cursor_pos[0] - left
                rel_y = cursor_pos[1] - top

                # 绘制十字线
                painter.drawLine(rel_x, 0, rel_x, height)
                painter.drawLine(0, rel_y, width, rel_y)
                painter.end()

                self.preview_label.setPixmap(qim.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))

                # 更新坐标显示
                self.coord_label.setText(f"坐标：({rel_x}, {rel_y})")
                self.save_btn.setEnabled(True)
            except Exception as e:
                print(f"更新预览失败: {str(e)}")
        else:
            self.preview_label.clear()
            self.coord_label.setText("坐标：N/A")
            self.save_btn.setEnabled(False)

    def save_screenshot(self):
        if self.bound_hwnd:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存截图", "", "PNG图片 (*.png);;JPEG图片 (*.jpg)")
            if file_path:
                rect = win32gui.GetWindowRect(self.bound_hwnd)
                screenshot = ImageGrab.grab(bbox=rect)
                screenshot.save(file_path)

    def nativeEvent(self, eventType, message):
        """Windows消息处理（关键改进）"""
        msg = message[0]
        if self.is_binding and msg.message == win32con.WM_LBUTTONDOWN:
            # 转换坐标
            x = win32api.LOWORD(msg.lParam)
            y = win32api.HIWORD(msg.lParam)

            # 获取窗口句柄
            hwnd = win32gui.WindowFromPoint((x, y))
            self.bound_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)

            # 恢复界面状态
            self.is_binding = False
            self.show()
            self.setMouseTracking(False)
            win32api.SetCursor(win32api.LoadCursor(0, win32con.IDC_ARROW))

            # 更新状态显示
            if self.bound_hwnd:
                title = win32gui.GetWindowText(self.bound_hwnd)
                self.status_label.setText(f"已绑定窗口：{title[:20]}...")
            return True, 0
        return super().nativeEvent(eventType, message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CaptureTool()
    window.show()
    sys.exit(app.exec_())