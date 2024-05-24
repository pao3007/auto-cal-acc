from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMainWindow, QApplication, QDesktopWidget
from PyQt5.QtCore import Qt

from Definitions import centerWindow
from gui.general_popup_input import Ui_Setup as GeneralUiPopup


class MyGeneralInputPopUp(QMainWindow):

    def __init__(self, parent=None, left_btn="OK", right_btn="CLOSE", label="Exit?", label_text_size=12):
        super().__init__(parent)
        self.sensor_data = None
        self.ui = GeneralUiPopup()
        self.ui.setupUi(self)
        self.value = None
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
        self.ui.ok_btn.setDefault(True)
        self.ui.input_line.returnPressed.connect(self.ok_btn)

    def ok_btn(self):
        self.continue_code = True
        self.value = self.ui.input_line.text()
        self.close()

    def show_modal(self):
        centerWindow(self)
        self.continue_code = False
        self.ui.input_line.clear()
        self.setWindowModality(Qt.ApplicationModal)
        self.show()
        self.exec_ = True
        while self.exec_:
            QApplication.instance().processEvents()

    def closeEvent(self, event):
        self.exec_ = False
        super().closeEvent(event)
