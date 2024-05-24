from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QDialog, QMainWindow, QApplication, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer
from os.path import join as os_path_join, exists as os_path_exists

from MyStartUpWindow import MyStartUpWindow
from Definitions import centerWindow
from gui.general_popup import Ui_Setup as GeneralUiPopup


class MyGeneralPopUp(QMainWindow):

    def __init__(self, parent=None, start_window: MyStartUpWindow = None, left_btn="OK", right_btn="CLOSE", label="Exit?", label_text_size=12, timer=0, show_exit=False):
        super().__init__(parent)
        self.sensor_data = None
        self.ui = GeneralUiPopup()
        self.ui.setupUi(self)
        self.start_window = start_window
        self.ui.close_btn.setText(right_btn)
        self.ui.ok_btn.setText(left_btn)
        self.ui.label.setText(label)
        self.continue_code = False
        self.exec_ = False
        original_font = self.ui.label.font()
        modified_font = QFont(original_font)
        modified_font.setPointSize(label_text_size)
        self.ui.label.setFont(modified_font)

        self.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setWindowTitle(" ")

        self.ui.ok_btn.clicked.connect(self.ok_btn)
        self.ui.close_btn.clicked.connect(self.close)
        self.timer = None
        if timer == 0:
            self.ui.countdown_label.setHidden(True)
        else:
            self.ui.ok_btn.setEnabled(False)
            self.ui.countdown_label.setText(str(timer))
            self.timer = timer
        if show_exit:
            path = os_path_join(self.start_window.starting_folder, "images", "exit.png")

            # Check if the file exists
            if os_path_exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    resized_pixmap = pixmap.scaled(45, 45, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.ui.countdown_label.setPixmap(resized_pixmap)
                    # self.ui.countdown_label.setFixedSize(pixmap.size())
                    self.ui.countdown_label.show()
                else:
                    print("The image is not valid or corrupted.")
            else:
                print("The specified file does not exist.")

    def ok_btn(self):
        self.continue_code = True
        self.close()

    def show_modal(self):
        centerWindow(self)
        self.setWindowModality(Qt.ApplicationModal)
        self.show()
        self.exec_ = True
        if self.timer:
            QTimer.singleShot(1000, lambda: self.countdown())
        while self.exec_:
            QApplication.instance().processEvents()

    def countdown(self):
        print("COUNTDOWN")
        self.timer -= 1
        self.ui.countdown_label.setText(str(self.timer))
        if self.timer == 0:
            self.ui.ok_btn.setEnabled(True)
            self.ui.countdown_label.setHidden(True)
        else:
            QTimer.singleShot(1000, lambda: self.countdown())

    def closeEvent(self, event):
        self.exec_ = False
        super().closeEvent(event)
