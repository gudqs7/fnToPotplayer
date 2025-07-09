import logging
import sys
import os

# 获取脚本所在目录
exe_name = os.path.basename(sys.executable)

if exe_name == 'fn2PotPlayerGUI.exe':
    # 切换工作目录到脚本所在目录
    exe_dir = os.path.dirname(sys.executable)
    os.chdir(exe_dir)

from utils.log import logger, formatter
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton,
                             QCheckBox, QTextEdit, QLabel, QSystemTrayIcon, QMenu, QDesktopWidget)
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QIcon
from app import flash_app

from PyQt5.QtCore import pyqtSignal, QObject


def resource_path(relative_path):
    """ 获取资源的绝对路径 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class QTextEditLogger(logging.Handler, QObject):
    append_log = pyqtSignal(str)

    def __init__(self, log_widget):
        super().__init__()
        QObject.__init__(self)
        self.widget = log_widget
        self.append_log.connect(self.append_msg)

    def emit(self, record):
        msg = self.format(record)
        self.append_log.emit(msg)

    def append_msg(self, msg):
        self.widget.append(msg)
        self.widget.verticalScrollBar().setValue(
            self.widget.verticalScrollBar().maximum()
        )


class FlaskController(QMainWindow):
    def __init__(self):
        super().__init__()

        # Flask应用
        self.log_display = None
        self.log_signal = None
        self.app = flash_app
        self.server_thread = None
        self.server_running = False

        # 注册表设置 (Windows开机自启动)
        self.settings = QSettings("FnToPotPlayer", "FnToPotPlayer")

        self.init_ui()
        self.init_logging()
        self.init_tray_icon()
        self.load_settings()

        # 定时器用于检查服务器状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_server_status)
        self.status_timer.start(10000)

    def init_logging(self):
        # 添加自定义处理器
        qt_handler = QTextEditLogger(self.log_display)
        qt_handler.setFormatter(formatter)
        logger.addHandler(qt_handler)

    def center(self):
        """将窗口居中显示"""
        # 获取屏幕几何信息
        screen = QDesktopWidget().screenGeometry()
        # 计算居中位置
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        # 移动窗口到中心位置
        self.move(x, y)

    def init_ui(self):
        self.setWindowTitle("飞牛跳转PotPlayer服务端")
        # self.setGeometry(300, 300, 500, 400)
        # 设置窗口大小
        self.resize(500, 500)

        # 调用居中方法
        self.center()

        # 主窗口布局
        main_widget = QWidget()
        layout = QVBoxLayout()

        # 控制按钮
        self.start_btn = QPushButton("启动服务器")
        self.start_btn.clicked.connect(self.toggle_server)
        self.stop_btn = QPushButton("停止服务器")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)

        # 复选框
        self.auto_start_cb = QCheckBox("开机自启动")
        self.auto_start_cb.stateChanged.connect(self.toggle_auto_start)

        self.minimize_to_tray_cb = QCheckBox("最小化到托盘")
        self.minimize_to_tray_cb.stateChanged.connect(self.toggle_minimize_to_tray)

        self.tip_label = QLabel("若PotPlayer提示错误，打开详细错误信息，找到对应文件路径到文件管理器打开试试！")
        self.tip_label.setStyleSheet("color: red;")

        # 日志显示
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)

        # 布局
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.auto_start_cb)
        button_layout.addWidget(self.minimize_to_tray_cb)
        button_layout.addWidget(self.tip_label)

        layout.addLayout(button_layout)
        layout.addWidget(self.log_display)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def init_tray_icon(self):
        # 加载图标
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = resource_path("icon.png")
        if not os.path.exists(icon_path):
            logger.info(f"图标文件不存在: {icon_path}")
            # 使用空路径，系统会提供默认图标
            icon_path = ""

        self.tray_icon.setIcon(QIcon(icon_path))

        # 创建托盘菜单
        tray_menu = QMenu()

        open_action = tray_menu.addAction("打开")
        open_action.triggered.connect(self.show_normal)

        # toggle_auto_start_action = tray_menu.addAction("切换开机自启动")
        # toggle_auto_start_action.triggered.connect(self.toggle_auto_start_from_menu)

        exit_action = tray_menu.addAction("退出")
        exit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_normal()

    def toggle_auto_start_from_menu(self):
        self.auto_start_cb.setChecked(not self.auto_start_cb.isChecked())
        self.toggle_auto_start()

    def toggle_auto_start(self):
        auto_start = self.auto_start_cb.isChecked()
        self.settings.setValue("auto_start", auto_start)

        # Windows开机自启动设置
        if sys.platform == "win32":
            import winreg
            key = winreg.HKEY_CURRENT_USER
            subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                with winreg.OpenKey(key, subkey, 0, winreg.KEY_ALL_ACCESS) as reg_key:
                    if auto_start:
                        winreg.SetValueEx(reg_key, "fn2PotPlayer", 0, winreg.REG_SZ,
                                          f'"{sys.executable}" "{os.path.abspath(__file__)}"')
                        logger.info(
                            r'设置开机启动成功！ 见 HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run 下 fn2PotPlayer 项')
                    else:
                        try:
                            winreg.DeleteValue(reg_key, "fn2PotPlayer")
                            logger.info('已关闭开机启动！')
                        except WindowsError:
                            pass
            except Exception as e:
                logger.error(f"设置开机自启动失败: {e}")

    def toggle_minimize_to_tray(self):
        minimize_to_tray = self.minimize_to_tray_cb.isChecked()
        self.settings.setValue("minimize_to_tray", minimize_to_tray)

    def load_settings(self):
        # 加载设置
        self.auto_start_cb.setChecked(self.settings.value("auto_start", False, type=bool))
        self.minimize_to_tray_cb.setChecked(self.settings.value("minimize_to_tray", False, type=bool))

        # 如果设置了开机自启动，自动启动服务器
        if self.auto_start_cb.isChecked():
            QTimer.singleShot(1000, lambda: self.start_server(True))

    def start_server(self, hide_after_start=False):
        if self.server_running:
            return

        def run_flask():
            mode = os.environ.get("fnToPotPlayer-mode", "pro")
            if mode == 'dev':
                self.app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=False)
            else:
                self.app.run(host='0.0.0.0', port=5050)

        self.server_thread = threading.Thread(target=run_flask)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.server_running = True

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        logger.info("Flask服务器已启动: http://127.0.0.1:5050")
        if hide_after_start:
            logger.info("开机自启立刻隐藏窗口")
            self.hide()

    def stop_server(self):
        # 实际上Flask的开发服务器没有官方停止方法
        # 这里我们只是标记状态并终止线程
        if self.server_thread and self.server_thread.is_alive():
            # 这不是一个干净的停止方式，但在开发环境中可用
            import ctypes
            tid = ctypes.c_long(self.server_thread.ident)
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(SystemExit))
            if res == 0:
                logger.error("无效的线程ID")
            elif res != 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
                logger.error("停止线程失败")

        self.server_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        logger.info("Flask服务器已停止")

    def toggle_server(self):
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def update_server_status(self):
        # 更新按钮状态
        if self.server_running:
            self.start_btn.setText("服务器运行中")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.start_btn.setText("启动服务器")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def hideEvent(self, event):
        if self.minimize_to_tray_cb.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "飞牛跳转PotPlayer",
                "程序已最小化到托盘",
                QSystemTrayIcon.Information,
                2000
            )

    def closeEvent2(self, event):
        if self.minimize_to_tray_cb.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "飞牛跳转PotPlayer",
                "程序已最小化到托盘",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.quit_app()

    def show_normal(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()

    def quit_app(self):
        if self.server_running:
            self.stop_server()
        self.tray_icon.hide()
        QApplication.quit()


# 自定义日志处理器，将日志输出到QTextEdit
class QtLogHandler(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)


if __name__ == "__main__":
    # 高DPI适配设置
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    if sys.platform == "win32":
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    app = QApplication(sys.argv)

    # 设置应用程序图标
    icon_path = resource_path("icon.png")
    if not os.path.exists(icon_path):
        logger.info(f"图标文件不存在: {icon_path}")
        # 使用空路径，系统会提供默认图标
        icon_path = ""

    app.setWindowIcon(QIcon(icon_path))

    # 设置应用程序字体（可选）
    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    controller = FlaskController()
    controller.show()

    sys.exit(app.exec_())
