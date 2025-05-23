# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Ui_LoginWindow.ui'
#
# Created by: PyQt5 UI code generator 5.15.6
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_LoginWindow(object):
    def setupUi(self, LoginWindow):
        LoginWindow.setObjectName("LoginWindow")
        LoginWindow.resize(490, 300)
        LoginWindow.setMinimumSize(QtCore.QSize(490, 300))
        LoginWindow.setMaximumSize(QtCore.QSize(490, 300))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("img/logo.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        LoginWindow.setWindowIcon(icon)
        self.accountEdit = QtWidgets.QComboBox(LoginWindow)
        self.accountEdit.setGeometry(QtCore.QRect(100, 110, 290, 42))
        self.accountEdit.setToolTip("")
        self.accountEdit.setStyleSheet("/* 基础字体调整 */\n"
"                    QComboBox {\n"
"                    font-size: 17px;\n"
"                    border: 1px solid #D8DEE9;\n"
"                    }\n"
"                    /* 下拉列表样式 */\n"
"                    QComboBox QAbstractItemView {\n"
"                    font-size: 20px;\n"
"                    min-width: 100px; /* 最小下拉列表宽度 */\n"
"                    min-height: 50px; /* 每个选项的最小高度 */\n"
"                    outline: none; /* 移除选中虚线框 */\n"
"                    border: 1px solid #D8DEE9;\n"
"                    }\n"
"                ")
        self.accountEdit.setEditable(True)
        self.accountEdit.setInsertPolicy(QtWidgets.QComboBox.InsertAtTop)
        self.accountEdit.setObjectName("accountEdit")
        self.passwordEdit = QtWidgets.QLineEdit(LoginWindow)
        self.passwordEdit.setGeometry(QtCore.QRect(100, 170, 290, 40))
        self.passwordEdit.setStyleSheet("/* 输入框样式 */\n"
"                    QLineEdit {\n"
"                    border: 1px solid #D8DEE9;\n"
"                    padding: 5px;\n"
"                    border-radius: 3px;\n"
"                    }\n"
"                ")
        self.passwordEdit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.passwordEdit.setObjectName("passwordEdit")
        self.confirmButton = QtWidgets.QPushButton(LoginWindow)
        self.confirmButton.setGeometry(QtCore.QRect(180, 230, 121, 51))
        self.confirmButton.setStyleSheet("/* 按钮通用样式 */\n"
"                    QPushButton {\n"
"                    background-color: #5E81AC;\n"
"                    color: white;\n"
"                    border: none;\n"
"                    padding: 8px 15px;\n"
"                    border-radius: 4px;\n"
"                    min-width: 80px;\n"
"                    }\n"
"\n"
"                    QPushButton:hover {\n"
"                    background-color: #81A1C1;\n"
"                    }\n"
"\n"
"                    QPushButton:pressed {\n"
"                    background-color: #4C6A8C;\n"
"                    }\n"
"                ")
        self.confirmButton.setObjectName("confirmButton")
        self.label = QtWidgets.QLabel(LoginWindow)
        self.label.setGeometry(QtCore.QRect(195, 10, 91, 81))
        self.label.setStyleSheet("image: url(:/login_logo/logo.png);")
        self.label.setText("")
        self.label.setObjectName("label")
        self.RememberPassWord = QtWidgets.QCheckBox(LoginWindow)
        self.RememberPassWord.setGeometry(QtCore.QRect(400, 170, 71, 16))
        self.RememberPassWord.setIconSize(QtCore.QSize(16, 16))
        self.RememberPassWord.setObjectName("RememberPassWord")
        self.LauncherMode = QtWidgets.QCheckBox(LoginWindow)
        self.LauncherMode.setGeometry(QtCore.QRect(400, 195, 81, 16))
        self.LauncherMode.setObjectName("LauncherMode")

        self.retranslateUi(LoginWindow)
        QtCore.QMetaObject.connectSlotsByName(LoginWindow)

    def retranslateUi(self, LoginWindow):
        _translate = QtCore.QCoreApplication.translate
        LoginWindow.setWindowTitle(_translate("LoginWindow", "登录"))
        self.accountEdit.setPlaceholderText(_translate("LoginWindow", "请输入账号"))
        self.passwordEdit.setPlaceholderText(_translate("LoginWindow", "请输入密码"))
        self.confirmButton.setText(_translate("LoginWindow", "登录"))
        self.RememberPassWord.setText(_translate("LoginWindow", "记住密码"))
        self.LauncherMode.setText(_translate("LoginWindow", "Chrome内核"))
import login_logo_rc
