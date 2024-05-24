import sys
from collections import deque

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from numpy import abs as np_abs
import win32api
import win32con
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QApplication, QDialog, QVBoxLayout, QLabel, \
    QLineEdit, QDialogButtonBox, QComboBox
from PyQt5.QtCore import QThread, QEvent, Qt, QTimer, QSize
from os import chdir as os_chdir, path as os_path, remove as os_remove, rename as os_rename

from matplotlib import pyplot as plt
from ThreadCheckDevicesConnected import ThreadCheckDevicesConnected
from Definitions import (kill_sentinel, start_sentinel_modbus, start_sentinel_d, scale_app, center_on_screen,
                         load_all_config_files, set_wavelengths, get_params, copy_files, save_statistics_to_csv,
                         show_add_dialog, open_folder_in_explorer, save_error, format_serial_number)
from SensAcc.MySettingsWindow import MySettingsWindow as MySettingsWindowAcc
from matplotlib.pyplot import close as pyplot_close
import ctypes
from ctypes import wintypes, byref as ctypes_byref
from SensAcc.SettingsParams import MySettings
from SensAcc.ThreadControlFuncGenStatements import ThreadControlFuncGenStatements
from re import search as re_search
from DatabaseCom import DatabaseCom
from SensAcc.PlotOut import MyPlottingWindow
from SensAcc.PlotSlope import PlotSlope
from webbrowser import open_new as open_new_pdf

from MyGeneralPopUp import MyGeneralPopUp
from gui.autoCalibration import Ui_AutoCalibration


class MyMainWindow(QMainWindow):
    from MyStartUpWindow import MyStartUpWindow

    def __init__(self, window: MyStartUpWindow, my_settings: MySettings):
        super().__init__()
        print("LOADING MAIN WINDOW ACC")
        self.block_signals_update = False
        self.wls_were_set = False
        self.box_close_event = None
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowMaximizeButtonHint)
        self.pid = None
        self.data = deque(maxlen=10000)
        self.first_show = True
        self.block_write = False
        self.s_n_export = None
        self.opt_force = False
        self.sensor_gen_error = False
        self.thcfgs = ThreadControlFuncGenStatements()
        self.my_settings = my_settings
        self.window = window
        self.out_bro = 0
        self.sensor_gen_check = True
        self.thread_check_new_file = None
        self.config_file_path = None
        self.config_file = None
        self.settings_window = None
        self.measure = False
        self.s_n = None
        self.check_cnt = 0
        self.ref_init = 0
        self.remaining_time = 3
        self.sensor_ref_check = -1
        self.sensor_opt_check = -1

        self.ui = Ui_AutoCalibration()
        self.ui.setupUi(self)

        layout = QVBoxLayout()

        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.line, = self.ax.plot([], [])
        self.ax.xaxis.set_visible(False)
        self.ax.yaxis.set_visible(False)
        self.ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False)

        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)

        layout.addWidget(self.canvas)

        self.ui.widget_graph.setLayout(layout)

        self.ui.widget_graph.setHidden(True)

        self.ui.just_box_6.setEnabled(False)
        self.ui.just_box_7.setEnabled(False)

        self.orig_wid_gen_pos_x = self.ui.widget_gen.pos().x()
        self.orig_wid_gen_pos_y = self.ui.widget_gen.pos().y()
        # open_action = QAction("Options", self)
        # open_action.triggered.connect(self.open_settings_window)
        # self.ui.menuSettings.addAction(open_action)
        self.autoCalib = AutoCalibMain(self, self.my_settings, self.thcfgs)
        path = os_path.join(self.my_settings.starting_folder, "images/logo.png")
        self.ui.logo_label.setPixmap(QPixmap(path))

        self.ui.S_N_line.editingFinished.connect(self.set_s_n)
        self.ui.S_N_line.textChanged.connect(self.check_s_n)

        self.ui.start_btn.clicked.connect(self.autoCalib.on_btn_start_clicked)
        self.ui.stop_btn.clicked.connect(self.stop_clicked)
        self.ui.plot_graph_check.stateChanged.connect(self.plot_check_changed)
        self.ui.select_config.currentTextChanged.connect(self.config_changed)
        self.ui.btn_load_wl.clicked.connect(self.btn_connect_load_wl)
        self.ui.btn_settings.clicked.connect(self.open_settings_window)
        self.ui.export_pass_btn.clicked.connect(self.exp_btn_clicked)
        self.ui.export_fail_btn.clicked.connect(self.exp_btn_clicked)
        self.ui.export_fail_btn.installEventFilter(self)
        self.ui.export_pass_btn.installEventFilter(self)

        self.ui.actionwith_project.triggered.connect(self.open_sentinel_app_with_proj)
        self.ui.actionwithout_project.triggered.connect(self.open_sentinel_app_no_proj)

        self.ui.actionOPEN_PP.triggered.connect(self.open_procedure)

        self.ui.actionmain_folder.triggered.connect(self.open_main_folder)
        self.ui.actioncalibration_folder.triggered.connect(self.open_calib_folder)
        self.ui.actionraw_opt.triggered.connect(self.open_folder_opt_raw)
        self.ui.actionraw_ref.triggered.connect(self.open_folder_opt)
        self.ui.actionwith_header_opt.triggered.connect(self.open_folder_opt)
        self.ui.actionwith_header_ref.triggered.connect(self.open_folder_ref)

        self.ui.actionAdd_new_operator.triggered.connect(self.add_new_operator)
        self.ui.actionChange_operator.triggered.connect(self.change_operator)

        self.ui.actionopen.triggered.connect(self.open_help)

        self.ui.progressBar.setValue(0)
        self.ui.start_btn.setEnabled(False)
        font = QFont("Arial", 10)
        font2 = QFont("Arial", 12)
        self.ui.output_browser_2.setFont(font)
        self.ui.output_browser.setFont(font)
        self.ui.output_browser_3.setFont(font2)

        if my_settings is None or my_settings.check_if_none():
            self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["load_error"])
        self.ui.widget_help.setHidden(True)
        self.ui.stop_btn.setHidden(True)
        self.ui.gen_status_label.setHidden(False)
        self.ui.gen_status_label_2.setHidden(True)
        self.change_sens_type_label()
        path = os_path.join(self.my_settings.starting_folder, "images", "icon.png")
        self.setWindowIcon(QIcon(path))
        path2 = os_path.join(self.my_settings.starting_folder, "images", "unlock.png")
        icon = QIcon(QPixmap(path2))
        self.ui.btn_opt_unlocked.setIcon(icon)
        icon_size = QSize(24, 24)  # For example, 24x24 pixels
        self.ui.btn_opt_unlocked.setIconSize(icon_size)
        self.ui.btn_opt_unlocked.setStyleSheet("background: transparent; border: none; text-align: center;")
        self.ui.btn_opt_unlocked.clicked.connect(self.opt_sens_is_already_unlocked)
        self.ui.btn_opt_unlocked.setHidden(True)
        path = os_path.join(self.my_settings.starting_folder, "images/setting_btn.png")
        icon = QIcon(QPixmap(path))
        self.ui.btn_settings.setIcon(icon)
        self.ui.btn_settings.setIconSize(self.ui.btn_opt_unlocked.size())
        self.ui.btn_settings.setStyleSheet("background: transparent; border: none; text-align: center;")

        self.prev_opt_channel = self.my_settings.opt_channels
        # Load the User32.dll
        user32 = ctypes.WinDLL('user32', use_last_error=True)

        # Declare the Windows API methods
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetKeyboardLayout.argtypes = [wintypes.DWORD]
        user32.GetKeyboardLayout.restype = wintypes.HKL
        self.start_width = self.width()
        self.start_height = self.height()
        self.ui.S_N_line.installEventFilter(self)

        def get_current_keyboard_layout():
            hwnd = user32.GetForegroundWindow()
            thread_id, process_id = wintypes.DWORD(), wintypes.DWORD()
            thread_id = user32.GetWindowThreadProcessId(hwnd, ctypes_byref(process_id))
            hkl = user32.GetKeyboardLayout(thread_id)
            hkl_hex = hex(hkl & 0xFFFF)
            layout_id = f"0000{hkl_hex[2:]}".zfill(8)
            return layout_id

        self.native_keyboard_layout = get_current_keyboard_layout()
        if not win32api.LoadKeyboardLayout('00000409', win32con.KLF_ACTIVATE):
            self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["key_board_err"])
        self.setWindowTitle(" ")
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.KeyPress and not self.isHidden() and not self.ui.S_N_line.hasFocus()
                and not self.block_write):
            # Manually updating QLineEdit
            current_text = self.ui.S_N_line.text()
            if event.key() == Qt.Key_Backspace:
                new_text = current_text[:-1]  # Remove the last character
            else:
                new_text = current_text + event.text()
            self.set_s_n(new_text)
            return True  # Event was handled
        elif event.type() == QEvent.MouseButtonDblClick and obj is self.ui.S_N_line:
            # Handle the double-click event, e.g., set the text of the QLineEdit
            self.ui.S_N_line.setText(self.autoCalib.last_s_n if self.autoCalib.last_s_n is not None else "")
            return True  # Return True to indicate the event has been handled

        if obj == self.ui.export_pass_btn and self.ui.fail_status_label.text() == "NOTE":
            if event.type() == QEvent.Enter:
                self.ui.fail_status_label.setStyleSheet("color: black;")
                return True
            elif event.type() == QEvent.Leave:
                self.ui.fail_status_label.setStyleSheet("color: grey;")
                return True
        elif obj == self.ui.export_fail_btn and self.ui.pass_status_label.text() == "EXPORT":
            if event.type() == QEvent.Enter:
                self.ui.pass_status_label.setStyleSheet("color: black;")
                return True
            elif event.type() == QEvent.Leave:
                self.ui.pass_status_label.setStyleSheet("color: grey;")
                return True
        return super().eventFilter(obj, event)

    def open_procedure(self):
        """Funckia otvorí pracovný postup v predvolenom programe"""
        pdf_path = os_path.join(self.my_settings.starting_folder, r"procedures\acc_procedure.pdf")
        if os_path.exists(pdf_path):
            # Open the PDF file in the default viewer
            open_new_pdf(pdf_path)
        else:
            print(f"The file {pdf_path} does not exist.")

    def update_data(self, new_data, max_g, value):
        """Aktualizuje graf zrýchlenia ref. senzora a aj zobrazované zrýchlenie """

        self.data.extend(new_data[-self.data.maxlen:])
        print(f"Existing data: {len(self.data)}")

        self.line.set_ydata(self.data)
        self.line.set_xdata(range(len(self.data)))

        self.ax.relim()
        self.ax.autoscale_view()

        self.canvas.draw()

        self.ui.ref_value_max_g_label.setText(max_g)
        self.update_progress_bar(value)

    def open_help(self):
        """Otvorí krátky pracovný postup"""
        print("Open help --------------------------------------------")
        if self.ui.widget_help.isHidden():
            self.ui.widget_gen.move(-22, self.ui.widget_gen.pos().y())
            self.ui.widget_help.setHidden(False)
            self.setFixedSize(int(self.width() * 1.434), self.height())
            self.ui.actionopen.setText(self.window.translations[self.window.lang]["actionopen_close"])
        else:
            self.setFixedSize(int(self.start_width * self.window.window_scale), self.height())
            self.ui.widget_help.setHidden(True)
            self.ui.widget_gen.move(int(self.orig_wid_gen_pos_x * self.window.window_scale),
                                    int(self.orig_wid_gen_pos_y * self.window.window_scale))
            self.ui.actionopen.setText(self.window.translations[self.window.lang]["actionopen_open"])

    def open_folder_opt_raw(self):
        """Otvorí priečinok s nameranými dátami"""
        open_folder_in_explorer(self.my_settings.folder_opt_export_raw)

    def open_folder_opt(self):
        """Otvorí priečinok s nameranými dátami"""
        open_folder_in_explorer(self.my_settings.folder_opt_export)

    def open_folder_ref_raw(self):
        """Otvorí priečinok s nameranými dátami"""
        open_folder_in_explorer(self.my_settings.folder_ref_export_raw)

    def open_folder_ref(self):
        """Otvorí priečinok s nameranými dátami"""
        open_folder_in_explorer(self.my_settings.folder_ref_export)

    def open_main_folder(self):
        """Otvorí priečinok s podpriečinkami"""
        open_folder_in_explorer(self.my_settings.folder_main)

    def open_calib_folder(self):
        """Otvorí priečinok s výsledkami kalibrácii"""
        open_folder_in_explorer(self.my_settings.folder_calibration_export)

    def open_sentinel_app_with_proj(self):
        """Otvorí sentinel-d s predvoleným projektom"""
        self.pid = start_sentinel_d(self.my_settings.opt_project, self.my_settings.folder_sentinel_D_folder,
                                    self.my_settings.subfolder_sentinel_project, no_log=True, get_pid=True)
        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["open_sentinel"])

    def open_sentinel_app_no_proj(self):
        """Otvorí sentinel-d bez projktu"""
        self.pid = start_sentinel_d(self.my_settings.opt_project, self.my_settings.folder_sentinel_D_folder,
                                    self.my_settings.subfolder_sentinel_project, no_log=True,
                                    no_proj=True, get_pid=True)
        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["open_sentinel"])

    def change_operator(self):
        """Otvorí okno pre zmenu operátora"""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.window.translations[self.window.lang]["choose_op"])

        vbox = QVBoxLayout()

        label = QLabel(self.window.translations[self.window.lang]["sel_op"])
        vbox.addWidget(label)

        combo_box = QComboBox()
        for operator in self.window.operators:
            combo_box.addItem(operator)
        vbox.addWidget(combo_box)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        vbox.addWidget(button_box)

        dialog.setLayout(vbox)

        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.window.operator = combo_box.currentText()
            self.ui.menuOperator.setTitle(f"Operator: {self.window.operator}")

    def add_new_operator(self):
        """Otvorí okno pre pridanie operátora"""
        self.block_write = True
        operator = show_add_dialog(self, self.window.starting_folder, self.window.lang, self.window.translations,
                                   start=False)
        if operator:
            self.window.operators.append(operator)
            self.window.operator = operator
            self.ui.menuOperator.setTitle(f"Operator: {self.window.operator}")
        self.block_write = False

    def exp_btn_clicked(self):
        """Otovrí okno pre export dát a pridanie poznámky"""
        self.block_write = True
        dialog = QDialog(self)
        dialog.setWindowTitle("Export calibration" if not self.autoCalib.export_status else "Add note")

        dialog_layout = QVBoxLayout()

        label = QLabel(self.window.translations[self.window.lang]["add_note"])
        dialog_layout.addWidget(label)

        text_input = QLineEdit()
        dialog_layout.addWidget(text_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)

        dialog.setLayout(dialog_layout)

        result = dialog.exec_()
        if result == QDialog.Accepted:
            self.autoCalib.export_to_database(text_input.text(), True)
        self.block_write = False

    def opt_sens_is_already_unlocked(self):
        self.opt_force = True

    def plot_check_changed(self, state):
        """Riadi zobrazenie grafov"""
        try:
            # self.calib_figure.hide()
            self.autoCalib.plot1.hide()
            self.autoCalib.plot2.hide()
        except:
            pass
        if state == 2:
            self.my_settings.calib_plot = True
            if self.autoCalib.calib_output:
                self.autoCalib.plot2.show()
                self.autoCalib.plot1.show()
        else:
            self.my_settings.calib_plot = False
        self.my_settings.save_config_file(True, self.window.config_file_path)

    def write_to_output_browser(self, text):
        """Pomocné vypisovanie"""
        self.out_bro += 1
        i = 0

        if (self.out_bro % 15) == 0:
            tmp = self.out_bro / 15
            while i < tmp:
                text += "."
                i += 1
            if tmp >= 3:
                self.out_bro = 0
            self.ui.output_browser_3.setText(text)
        elif self.out_bro == 0:
            self.ui.output_browser_3.setText(text)

    def change_sens_type_label(self):
        """Mení popis pre typ senzora"""
        self.ui.label_opt_sens_type_label.setText(
            self.my_settings.opt_sensor_type + f" {self.window.translations[self.window.lang]['config']}")

    def stop_clicked(self):
        """Vykoná ukončenie kalibrácie"""
        print("STOP")
        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["emergency_stop_engaged"])
        self.thcfgs.set_emergency_stop(True)
        kill_sentinel(True, False)
        self.measure = False
        if not self.thcfgs.get_start_measuring():
            self.ui.S_N_line.setEnabled(True)
            self.ui.btn_settings.setEnabled(True)
            self.ui.select_config.setEnabled(True)
            self.ui.plot_graph_check.setEnabled(True)
            self.ui.menubar.setEnabled(True)

    def first_sentinel_start(self, op):
        """Funkcia kontroluje spustenie sentinel-d pri prvom spustení"""
        self.ui.menuOperator.setTitle(f"Operator: {op}")
        from SensAcc.ThreadSentinelCheckNewFile import ThreadSentinelCheckNewFile
        self.thread_check_new_file = ThreadSentinelCheckNewFile(self.my_settings.folder_opt_export)
        self.thread_check_new_file.finished_signal.connect(lambda: self.start_modbus())
        self.thread_check_new_file.start()

    def start_modbus(self):
        """Funkia spúšťa modbus aplikáciu"""
        print("START MODBUS + KILL SENTINEL + START")
        opt_sentinel_file_name = self.thread_check_new_file.opt_sentinel_file_name
        kill_sentinel(True, False)
        QThread.msleep(100)
        start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                              self.my_settings.subfolder_sentinel_project,
                              self.my_settings.opt_project, self.my_settings.opt_channels)

        os_chdir(self.my_settings.folder_opt_export)

        if os_path.exists(opt_sentinel_file_name + '.csv'):
            os_remove(opt_sentinel_file_name + '.csv')
        QThread.msleep(100)
        self.show_back()
        self.window.hide()
        self.window.movie.stop()
        QThread.msleep(100)
        self.autoCalib.start()

    def opt_emit(self, is_ready):
        self.sensor_opt_check = is_ready

    def gen_emit(self, is_ready):
        self.sensor_gen_check = is_ready

    def ref_emit(self, is_ready):
        self.sensor_ref_check = is_ready

    def gen_error_emit(self, is_error):
        self.sensor_gen_error = is_error

    def update_wl_values(self, text):
        self.ui.opt_value_wl_label.setText(text)

    def update_ref_value(self, text):
        self.ui.ref_value_max_g_label.setText(text)

    def check_sensors_ready(self, check_status):
        """Kontrola pripravenosti spustenia kalibrácie"""
        if self.my_settings.opt_channels != 0 and self.ui.S_N_line.text().strip():
            if self.my_settings.opt_channels >= 2 and self.ui.stop_btn.isHidden():
                self.ui.btn_load_wl.setEnabled(True)
            else:
                self.ui.btn_load_wl.setEnabled(False)
            if self.sensor_opt_check == 1 and self.sensor_ref_check == 1 and self.sensor_gen_check and not self.measure and not self.sensor_gen_error:
                self.ui.start_btn.setEnabled(True)
            else:
                self.ui.start_btn.setEnabled(False)
        else:
            self.ui.start_btn.setEnabled(False)
            self.ui.btn_load_wl.setEnabled(False)
        if self.sensor_ref_check == 2 and (self.sensor_opt_check == 5 or self.opt_force):
            # print("TERMINATION ------------------------")
            # self.autoCalib.thread_check_sin_opt.termination = True
            # self.autoCalib.thread_check_sin_ref.termination = True
            self.block_signals_update = True
            self.thcfgs.set_end_sens_test(True)
            self.sensor_ref_check = 2
            self.sensor_opt_check = 5
            self.ui.opt_sens_status_label.setText(
                self.window.translations[self.window.lang]["opt_sens_status_label"]["ready"])
            self.ui.opt_sens_status_label.setStyleSheet("color: green;")
            self.ui.ref_sens_status_label.setText(
                self.window.translations[self.window.lang]["ref_sens_status_label"]["ready"])
            self.ui.ref_sens_status_label.setStyleSheet("color: green;")
            self.ui.btn_opt_unlocked.setHidden(True)

        if (check_status or (self.sensor_ref_check == 2 and (
                self.sensor_opt_check == 5 or self.opt_force))) and not self.block_signals_update:
            if self.sensor_opt_check != 0:
                if self.sensor_opt_check == 1 or self.sensor_opt_check == 11:
                    self.ui.btn_opt_unlocked.setHidden(True)
                    self.ui.opt_sens_status_label.setText(
                        self.window.translations[self.window.lang]["opt_sens_status_label"]["connected"])
                    self.ui.opt_sens_status_label.setStyleSheet("color: blue;")
                elif self.sensor_opt_check == 3:
                    self.ui.btn_opt_unlocked.setHidden(True)
                    self.ui.opt_sens_status_label.setText(
                        self.window.translations[self.window.lang]["opt_sens_status_label"]["usb_disconnected"])
                    if self.ui.opt_sens_status_label.isEnabled():
                        self.ui.opt_sens_status_label.setStyleSheet("color: red;")
                        self.ui.opt_sens_status_label.setEnabled(False)
                    else:
                        self.ui.opt_sens_status_label.setStyleSheet("color: black;")
                        self.ui.opt_sens_status_label.setEnabled(True)
                elif self.sensor_opt_check == 4 and not self.opt_force:
                    if self.my_settings.opt_channels == 2:
                        self.ui.btn_opt_unlocked.setHidden(False)
                        self.check_cnt += 1
                        if self.ui.opt_sens_status_label.isEnabled() and self.check_cnt >= 3:
                            self.ui.opt_sens_status_label.setText(
                                self.window.translations[self.window.lang]["opt_sens_status_label"]["not_ready"])
                            self.ui.opt_sens_status_label.setStyleSheet("color: red;")
                            self.ui.opt_sens_status_label.setEnabled(False)
                            self.check_cnt = 0
                        elif self.check_cnt >= 3:
                            self.ui.opt_sens_status_label.setText(
                                self.window.translations[self.window.lang]["opt_sens_status_label"]["unlock"])
                            self.ui.opt_sens_status_label.setStyleSheet("color: red;")
                            self.ui.opt_sens_status_label.setEnabled(True)
                            self.check_cnt = 0
                    else:
                        self.ui.opt_sens_status_label.setText(
                            self.window.translations[self.window.lang]["opt_sens_status_label"]["not_ready"])
                        self.ui.opt_sens_status_label.setStyleSheet("color: red;")
                elif self.sensor_opt_check == 5 or self.opt_force:
                    self.ui.btn_opt_unlocked.setHidden(True)
                    self.ui.opt_sens_status_label.setText(
                        self.window.translations[self.window.lang]["opt_sens_status_label"]["ready"])
                    self.ui.opt_sens_status_label.setStyleSheet("color: green;")
                elif self.sensor_opt_check == 10:
                    self.ui.btn_opt_unlocked.setHidden(True)
                    if self.my_settings.opt_channels == 2:
                        self.check_cnt += 1
                        if self.ui.opt_sens_status_label.isEnabled() and self.check_cnt >= 3:
                            self.ui.opt_sens_status_label.setText(
                                self.window.translations[self.window.lang]["opt_sens_status_label"]["connected"])
                            self.ui.opt_sens_status_label.setStyleSheet("color: orange;")
                            self.ui.opt_sens_status_label.setEnabled(False)
                            self.check_cnt = 0
                        elif self.check_cnt >= 3:
                            self.ui.opt_sens_status_label.setText(
                                self.window.translations[self.window.lang]["opt_sens_status_label"]["load_wl"])
                            self.ui.opt_sens_status_label.setStyleSheet("color: orange;")
                            self.ui.opt_sens_status_label.setEnabled(True)
                            self.check_cnt = 0
                    else:
                        self.ui.btn_opt_unlocked.setHidden(True)
                        self.ui.opt_sens_status_label.setText(
                            self.window.translations[self.window.lang]["opt_sens_status_label"]["not_connected"])
                        self.ui.opt_sens_status_label.setStyleSheet("color: orange;")
                elif self.sensor_opt_check == -1:
                    self.ui.btn_opt_unlocked.setHidden(True)
                    self.ui.opt_sens_status_label.setText(
                        self.window.translations[self.window.lang]["opt_sens_status_label"]["init"])
                    self.ui.opt_sens_status_label.setStyleSheet("color: black;")
            else:
                if self.my_settings.opt_channels == 2:
                    self.ui.btn_opt_unlocked.setHidden(True)
                    self.check_cnt += 1
                    if self.ui.opt_sens_status_label.isEnabled() and self.check_cnt >= 3:
                        self.ui.opt_sens_status_label.setText(
                            self.window.translations[self.window.lang]["opt_sens_status_label"]["not_connected"])
                        self.ui.opt_sens_status_label.setStyleSheet("color: orange;")
                        self.ui.opt_sens_status_label.setEnabled(False)
                        self.check_cnt = 0
                    elif self.check_cnt >= 3:
                        self.ui.opt_sens_status_label.setText(
                            self.window.translations[self.window.lang]["opt_sens_status_label"]["try_load_wl"])
                        self.ui.opt_sens_status_label.setStyleSheet("color: orange;")
                        self.ui.opt_sens_status_label.setEnabled(True)
                        self.check_cnt = 0
                else:
                    self.ui.btn_opt_unlocked.setHidden(True)
                    self.ui.opt_sens_status_label.setText(
                        self.window.translations[self.window.lang]["opt_sens_status_label"]["not_connected"])
                    self.ui.opt_sens_status_label.setStyleSheet("color: orange;")

            if self.sensor_ref_check != 0:
                if self.sensor_ref_check == 1:
                    self.ui.ref_sens_status_label.setText(
                        self.window.translations[self.window.lang]["ref_sens_status_label"]["connected"])
                    self.ui.ref_sens_status_label.setStyleSheet("color: blue;")
                elif self.sensor_ref_check == 2:
                    self.ui.ref_sens_status_label.setText(
                        self.window.translations[self.window.lang]["ref_sens_status_label"]["ready"])
                    self.ui.ref_sens_status_label.setStyleSheet("color: green;")
                elif self.sensor_ref_check == 6:
                    self.ui.ref_sens_status_label.setText(
                        self.window.translations[self.window.lang]["ref_sens_status_label"]["not_ready"])
                    self.ui.ref_sens_status_label.setStyleSheet("color: red;")
                elif self.sensor_ref_check == 3:
                    self.ui.ref_sens_status_label.setText(
                        self.window.translations[self.window.lang]["ref_sens_status_label"]["usb_disconnected"])
                    if self.ui.ref_sens_status_label.isEnabled():
                        self.ui.ref_sens_status_label.setStyleSheet("color: red;")
                        self.ui.ref_sens_status_label.setEnabled(False)
                    else:
                        self.ui.ref_sens_status_label.setStyleSheet("color: black;")
                        self.ui.ref_sens_status_label.setEnabled(True)
                elif self.sensor_ref_check == -1:
                    self.ui.ref_sens_status_label.setText(
                        self.window.translations[self.window.lang]["ref_sens_status_label"]["init"])
                    self.ui.ref_sens_status_label.setStyleSheet("color: black;")
            else:
                self.ui.ref_sens_status_label.setText(
                    self.window.translations[self.window.lang]["ref_sens_status_label"]["not_connected"])
                self.ui.ref_sens_status_label.setStyleSheet("color: orange;")

            if not self.sensor_gen_check:
                self.ui.gen_status_label_2.setHidden(False)
                if self.ui.gen_status_label.isEnabled():
                    self.ui.gen_status_label_2.setText(
                        self.window.translations[self.window.lang]["gen_status_label"]["disconnected"])
                    self.ui.gen_status_label.setStyleSheet("color: red;")
                    self.ui.gen_status_label_2.setStyleSheet("color: red;")
                    self.ui.gen_status_label.setEnabled(False)
                else:
                    self.ui.gen_status_label_2.setText(
                        self.window.translations[self.window.lang]["gen_status_label"]["connect_it"])
                    self.ui.gen_status_label.setStyleSheet("color: black;")
                    self.ui.gen_status_label_2.setStyleSheet("color: black;")
                    self.ui.gen_status_label.setEnabled(True)
            else:
                if self.sensor_gen_error:
                    self.ui.gen_status_label_2.setHidden(False)
                    if self.ui.gen_status_label.isEnabled():
                        self.ui.gen_status_label_2.setText(
                            self.window.translations[self.window.lang]["gen_status_label"]["disconnected"])
                        self.ui.gen_status_label.setStyleSheet("color: red;")
                        self.ui.gen_status_label_2.setStyleSheet("color: red;")
                        self.ui.gen_status_label.setEnabled(False)
                    else:
                        self.ui.gen_status_label_2.setText(
                            self.window.translations[self.window.lang]["gen_status_label"]["restart"])
                        self.ui.gen_status_label.setStyleSheet("color: black;")
                        self.ui.gen_status_label_2.setStyleSheet("color: black;")
                        self.ui.gen_status_label.setEnabled(True)
                else:
                    self.ui.gen_status_label.setStyleSheet("color: black;")
                    self.ui.gen_status_label_2.setHidden(True)

    def config_changed(self, text):
        """Reštartuje modbus pri zmene konfiguračného súboru"""
        self.window.current_conf = False
        self.my_settings.save_config_file(False, self.window.config_file_path)

        self.config_file = text + ".yaml"
        self.config_file_path = os_path.join(self.my_settings.subfolderConfig_path, self.config_file)
        self.window.config_file_path = self.config_file_path
        self.my_settings.load_config_file(self.window.config_file_path)

        self.window.current_conf = True
        self.my_settings.save_config_file(True, self.window.config_file_path)
        self.ui.plot_graph_check.setChecked(self.my_settings.calib_plot)
        kill_sentinel(False, True)
        start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                              self.my_settings.subfolder_sentinel_project,
                              self.my_settings.opt_project,
                              self.my_settings.opt_channels)
        if self.my_settings.opt_channels >= 2:
            self.ui.btn_load_wl.setHidden(False)
        else:
            self.ui.btn_load_wl.setHidden(True)
        self.load_gen_params_labels()

    def check_s_n(self, text=None):
        """Kontroluje správnosť sériového čísla"""
        if text is None:
            text = self.ui.S_N_line.text()
        if len(text) == 11 and text is not None:
            text = format_serial_number(text, "/")
            try:
                params, params2 = get_params(text, self.my_settings.starting_folder)
            except Exception:
                params = [None]
            if params[0] is None:
                self.ui.sn_check_label.setText(self.window.translations[self.window.lang]["sensor_id_bad"])
                self.ui.sn_check_label.show()
            else:
                self.ui.sn_check_label.hide()
        elif len(text) != 0 and text is not None:
            self.ui.sn_check_label.setText(self.window.translations[self.window.lang]["sensor_id_bad_format"])
            self.ui.sn_check_label.show()
        else:
            self.ui.sn_check_label.hide()

    def set_s_n(self, text=None):
        """Upravuje sériové číslo"""
        if text is None:
            text = self.ui.S_N_line.text()

        self.s_n_export = format_serial_number(text, "/")
        self.s_n = format_serial_number(text, "_")
        self.ui.S_N_line.blockSignals(True)
        self.ui.S_N_line.setText(self.s_n)
        self.ui.S_N_line.blockSignals(False)

    def btn_connect_load_wl(self):
        """Upraví sentinel-d projekt vlnové dĺžky"""
        kill_sentinel(False, True)
        attempt_count = 0
        max_attempts = 2
        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["load_wl_inter"])
        while attempt_count < max_attempts:
            try:
                order_id = re_search(r'(-?\d+(\.\d+)?)', self.s_n).group(1)
                if self.my_settings.opt_channels not in [0, 1]:
                    result = set_wavelengths(order_id, self.my_settings.subfolder_sentinel_project,
                                             self.my_settings.opt_project, self.my_settings.starting_folder)
                    if result == 0:
                        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["load_wl_error_1"])
                    elif result == -1:
                        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["load_wl_error_2"])
                    elif result == -2:
                        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["load_wl_error_3"])
                    else:
                        self.wls_were_set = True
                        self.ui.output_browser_3.setText(self.window.translations[self.window.lang]["load_wl_success"])
                    break
                else:
                    break
            except Exception as e:
                attempt_count += 1
                if attempt_count >= max_attempts:
                    self.ui.output_browser_3.setText(
                        f"{self.window.translations[self.window.lang]['load_wl_error_4']}\n{e}")
                    break
        start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                              self.my_settings.subfolder_sentinel_project,
                              self.my_settings.opt_project, self.my_settings.opt_channels)

    def open_settings_window(self):
        """Otvorí okno s nastaveniami"""
        self.settings_window = MySettingsWindowAcc(False, self.window, self.my_settings)
        self.hide()
        self.settings_window.show_back()

    def update_progress_bar(self, value):
        """Aktualizácia progress baru"""
        progress_sec = value / 10
        if progress_sec < self.my_settings.ref_measure_time:
            self.ui.progressBar.setValue(int(100 * progress_sec / self.my_settings.ref_measure_time))
        else:
            prog_finish = int(100 * progress_sec / self.my_settings.ref_measure_time)
            if prog_finish < 100:
                self.ui.progressBar.setValue(int(100 * progress_sec / self.my_settings.ref_measure_time))
            else:
                self.ui.progressBar.setValue(100)

    def enable_stop_btn(self):
        self.ui.stop_btn.setEnabled(True)

    def load_gen_params_labels(self):
        self.ui.label_start_freq.setText(str(self.my_settings.generator_sweep_start_freq) + " Hz")
        self.ui.label_stop_freq.setText(str(self.my_settings.generator_sweep_stop_freq) + " Hz")
        self.ui.label_mvpp.setText(str(self.my_settings.generator_max_mvpp) + " mVpp")
        self.ui.label_sweep_type.setText(self.my_settings.generator_sweep_type)
        self.ui.label_sweep_time.setText(str(self.my_settings.generator_sweep_time) + " s")

    def show_back(self):
        """Funkcia sa používa namiesto zákaldnej show() funkcie"""
        if self.box_close_event is None:
            self.box_close_event = MyGeneralPopUp(parent=self, start_window=self.window,
                                                  left_btn=self.window.translations[self.window.lang][
                                                      'close_event_yes'],
                                                  right_btn=self.window.translations[self.window.lang][
                                                      'close_event_no'],
                                                  label=self.window.translations[self.window.lang]['close_event_b'],
                                                  show_exit=True)
        self.set_language()
        if self.my_settings.opt_channels >= 2:
            self.ui.btn_load_wl.setHidden(False)
        else:
            self.ui.btn_load_wl.setHidden(True)
        self.ui.plot_graph_check.setChecked(self.my_settings.calib_plot)
        load_all_config_files(self.ui.select_config, self.window.config_file_path,
                              self.my_settings.opt_sensor_type,
                              self.my_settings.subfolderConfig_path)
        # label info o opt senz

        self.load_gen_params_labels()

        if self.prev_opt_channel != self.my_settings.opt_channels:
            kill_sentinel(False, True)
            start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                                  self.my_settings.subfolder_sentinel_project,
                                  self.my_settings.opt_project, self.my_settings.opt_channels)
        if self.first_show:
            self.window.window_scale_delta = self.window.window_scale
            self.first_show = False
        self.setFixedSize(int(self.width() * self.window.window_scale_delta),
                          int(self.height() * self.window.window_scale_delta))
        scale_app(self, self.window.window_scale_delta)

        def bad_scales():
            font = self.ui.btn_load_wl.font()
            font.setPointSize(int(9 * self.window.window_scale))
            self.ui.btn_load_wl.setFont(font)

            font = self.ui.plot_graph_check.font()
            font.setPointSize(int(9 * self.window.window_scale))
            self.ui.plot_graph_check.setFont(font)

        QTimer.singleShot(0, bad_scales)
        self.window.window_scale_delta = 1
        QTimer.singleShot(0, lambda: center_on_screen(self))

    def closeEvent(self, event):
        """Override pre closeEvent, vykonáva správne vypnutie vlákien a aplikácii"""
        self.box_close_event.show_modal()
        result = self.box_close_event.continue_code

        if result:
            self.hide()
            # Clean up resources or save any data if needed before exiting
            kill_sentinel(True, True)
            pyplot_close('all')
            try:
                self.autoCalib.thread_check_sin_opt.termination = True
                self.autoCalib.thread_check_sin_ref.termination = True
            except:
                pass
            win32api.LoadKeyboardLayout(self.native_keyboard_layout, win32con.KLF_ACTIVATE)
            sys.stdout.close()
            self.autoCalib.plot1.close()
            self.autoCalib.plot2.close()
            event.accept()
        else:
            event.ignore()

    def set_language(self):
        """Nastavuje jazyk okna"""
        trans = self.window.translations
        lang = self.window.lang

        def set_tool_tips():
            self.ui.btn_load_wl.setToolTip(trans[lang]["toolTip_btn_load_wl"])
            self.ui.plot_graph_check.setToolTip(trans[lang]["toolTip_plot_graph_check"])
            self.ui.select_config.setToolTip(trans[lang]["toolTip_select_config"])
            self.ui.btn_opt_unlocked.setToolTip(trans[lang]["toolTip_btn_opt_unlock"])
            self.ui.btn_settings.setToolTip(trans[lang]["toolTip_btn_settings"])
            self.ui.ref_sens_status_label.setToolTip(trans[lang]["toolTip_ref_status"])
            self.ui.opt_sens_status_label.setToolTip(trans[lang]["toolTip_opt_status"])
            self.ui.start_btn.setToolTip(trans[lang]["toolTip_btn_start"])
            self.ui.stop_btn.setToolTip(trans[lang]["toolTip_btn_stop"])
            self.ui.progressBar.setToolTip(trans[lang]["toolTip_progress_bar"])
            self.ui.just_box_6.setToolTip(trans[lang]["toolTip_box_gen"])
            self.ui.just_box_7.setToolTip(trans[lang]["toolTip_box_values"])

        self.ui.ref_sens_status_label.setText(trans[lang]["ref_sens_status_label"]["init"])
        self.ui.opt_sens_status_label.setText(trans[lang]["opt_sens_status_label"]["init"])
        self.ui.label_name_sweep_type.setText(trans[lang]["label_name_sweep_type"])
        self.ui.label_name_sweep_time.setText(trans[lang]["label_name_sweep_time"])
        self.ui.label_name_stop_freq.setText(trans[lang]["label_name_stop_freq"])
        self.ui.label_name_vpp.setText(trans[lang]["label_name_vpp"])
        self.ui.label_name_start_freq.setText(trans[lang]["label_name_start_freq"])
        self.ui.start_btn.setText(trans[lang]["start_btn"])
        self.ui.plot_graph_check.setText(trans[lang]["plot_graph_check"])
        self.ui.actionAdd_new_operator.setText(trans[lang]["actionAdd_new_operator"])
        self.ui.actionChange_operator.setText(trans[lang]["actionChange_operator"])
        self.ui.label_opt_sens_type_label.setText(
            self.my_settings.opt_sensor_type + f" {self.window.translations[self.window.lang]['config']}")
        if self.ui.widget_help.isHidden():
            self.ui.actionopen.setText(trans[lang]["actionopen_open"])
        else:
            self.ui.actionopen.setText(trans[lang]["actionopen_close"])
        self.ui.menuHelp.setTitle(trans[lang]["menuHelp"])
        self.ui.menuAbout.setTitle(trans[lang]["menuAbout"])

        self.ui.actioncalibration_folder.setText(trans[lang]["actioncalibration_folder"])
        self.ui.actionmain_folder.setText(trans[lang]["actionmain_folder"])
        self.ui.menuOpen_export_folder.setTitle(trans[lang]["menuOpen_export_folder"])

        self.ui.actionwith_project.setText(trans[lang]["actionwith_project"])
        self.ui.actionwithout_project.setText(trans[lang]["actionwithout_project"])
        self.ui.menuOpen_Sentinel_D.setTitle(trans[lang]["menuOpen_Sentinel_D"])

        self.ui.menuoptical_folder_2.setTitle(trans[lang]["menuoptical_folder_2"])
        self.ui.actionraw_opt.setText(trans[lang]["actionraw_opt"])
        self.ui.actionwith_header_opt.setText(trans[lang]["actionwith_header_opt"])

        self.ui.menureference_folder.setTitle(trans[lang]["menureference_folder"])
        self.ui.actionraw_ref.setText(trans[lang]["actionraw_ref"])
        self.ui.actionwith_header_ref.setText(trans[lang]["actionwith_header_ref"])

        self.ui.S_N_line.setPlaceholderText(trans[lang]["S_N_line_placeholder"])

        self.ui.help_text_browser.setText(f"<font><b>{trans[lang]['help_browser']['0']}</b></font>"
                                          f"<font><b>1.</b></font>{trans[lang]['help_browser']['1']}"
                                          f"<font><b>2.</b></font>{trans[lang]['help_browser']['2']}"
                                          f"<font><b>3.</b></font>{trans[lang]['help_browser']['3']}"
                                          f"<font><b>4.</b></font>{trans[lang]['help_browser']['4']}"
                                          f"<font><b>5.</b></font>{trans[lang]['help_browser']['5']}"
                                          f"<font><b>6.</b></font>{trans[lang]['help_browser']['6']}"
                                          f"<font><b>7.</b></font>{trans[lang]['help_browser']['7']}"
                                          f"<font><b>{trans[lang]['help_browser']['a']}</b></font>"
                                          f"<span style='color:green; font-style:italic;'>PASS</span>"
                                          f"{trans[lang]['help_browser']['b']}"
                                          f"<span style='color:red; font-style:italic;'>FAIL</span>"
                                          f"{trans[lang]['help_browser']['c']}"
                                          )
        set_tool_tips()


#  meranie + kalibrácia
class AutoCalibMain:
    from SensAcc.ThreadControlFuncGen import ThreadControlFuncGen
    from SensAcc.ThreadRefSensDataCollection import ThreadRefSensDataCollection
    from SensAcc.ThreadOptAndGenCheckIfReady import ThreadOptAndGenCheckIfReady
    from SensAcc.ThreadSentinelCheckNewFile import ThreadSentinelCheckNewFile
    from SensAcc.ThreadSensorsCheckIfReady import ThreadSensorsCheckIfReady
    from SensAcc.ThreadRefCheckIfReady import ThreadRefCheckIfReady

    def __init__(self, calib_window: MyMainWindow, my_settings: MySettings, thcfgs: ThreadControlFuncGenStatements):
        self.ow_export = False
        self.last_validation = None
        self.wl_slopes = None
        self.offset = None
        self.last_s_n_export = None
        self.last_s_n = None
        self.export_folder = None
        self.calib_result = True
        self.export_status = True
        self.my_settings = my_settings
        self.database = DatabaseCom(self.my_settings.starting_folder)
        self.time_stamp = None
        self.calibration_profile = None
        self.calib_output = None
        self.calib_window = calib_window
        self.start_window = calib_window.window

        self.thcfgs = thcfgs

        self.acc_calib = None

        self.current_date = None
        self.time_string = None
        self.opt_sentinel_file_name = None
        self.thread_check_opt_usb = ThreadCheckDevicesConnected(self.my_settings, self.start_window, True)
        self.thread_control_gen = self.ThreadControlFuncGen(self.my_settings.generator_id,
                                                            self.my_settings.generator_sweep_time,
                                                            self.my_settings.generator_sweep_start_freq,
                                                            self.my_settings.generator_sweep_stop_freq,
                                                            self.my_settings.generator_sweep_type,
                                                            self.my_settings.generator_max_mvpp,
                                                            self.thcfgs,
                                                            self.my_settings.opt_project,
                                                            self.my_settings.opt_channels,
                                                            self.my_settings.folder_sentinel_D_folder,
                                                            self.start_window,
                                                            self.my_settings)
        self.thread_check_new_file = self.ThreadSentinelCheckNewFile(self.my_settings.folder_opt_export)
        self.thread_ref_sens = self.ThreadRefSensDataCollection(self.start_window, self.thcfgs,
                                                                self.calib_window.s_n, self.my_settings,
                                                                self.calib_window.s_n_export)

        self.thread_check_sensors = self.ThreadSensorsCheckIfReady(self.thcfgs, self.my_settings)
        self.thread_check_sin_opt = self.ThreadOptAndGenCheckIfReady("127.0.0.1", 501, 1,
                                                                     100, 25, 0.003,
                                                                     self.start_window, self.my_settings, self.thcfgs)
        self.thread_check_sin_ref = self.ThreadRefCheckIfReady(self.thcfgs, self.start_window, self.my_settings)

        self.sensitivities_file = "sensitivities.csv"
        self.time_corrections_file = "time_corrections.csv"
        self.plot1 = MyPlottingWindow(self.calib_window, self.start_window, self.my_settings)
        self.plot2 = PlotSlope(self.calib_window, self.start_window, self.my_settings)

    def ref_check_finished(self):
        """Vykonáne pri ukončení vlákna ThreadRefCheckIfReady"""
        # print("END -------> REF CHECK")
        try:
            self.thread_check_sin_ref.task_sin.close()
        except:
            pass
        # self.thcfgs.set_end_sens_test(True)
        self.thread_check_new_file.start()
        self.calib_window.ui.ref_value_max_g_label.setText("-")
        self.calib_window.ui.opt_value_wl_label.setText("-")

        from nidaqmx import Task as nidaqmx_Task
        from nidaqmx.constants import AcquisitionType

        self.thread_ref_sens.task = nidaqmx_Task(new_task_name='RefMeasuring')
        self.thread_ref_sens.task.ai_channels.add_ai_accel_chan(
            self.my_settings.ref_device_name + '/' + self.my_settings.ref_channel,
            sensitivity=self.my_settings.calib_reference_sensitivity * 9.80665)
        # časovanie resp. vzorkovacia freqvencia, pocet vzoriek
        self.thread_ref_sens.task.timing.cfg_samp_clk_timing(self.my_settings.ref_sample_rate,
                                                             sample_mode=AcquisitionType.CONTINUOUS)

    def start(self):
        """Spustenie a reset logiky, spúšťa sa pri zapnutí aplikácie a vyhodnotení kalibrácie"""
        self.calib_window.block_signals_update = False
        self.thcfgs.enable_safety_check = False
        self.calib_window.wls_were_set = False
        self.calib_window.ui.S_N_line.clear()
        self.thcfgs.set_finished_measuring(False)
        self.thcfgs.set_start_sens_test(False)
        self.thcfgs.set_end_sens_test(False)
        self.thcfgs.set_start_measuring(False)
        self.calib_window.ui.progressBar.setValue(0)
        self.calib_window.opt_force = False
        self.calib_window.sensor_ref_check = -1
        self.calib_window.sensor_opt_check = -1
        self.thcfgs.set_finished_measuring(False)

        self.calib_window.measure = False

        self.thread_check_sin_ref = self.ThreadRefCheckIfReady(self.thcfgs, self.start_window, self.my_settings)
        self.thread_check_sin_ref.check_ready.connect(self.calib_window.ref_emit)
        self.thread_check_sin_ref.finished.connect(self.ref_check_finished)
        self.thread_check_sin_ref.out_value.connect(self.calib_window.update_ref_value)
        self.thread_check_sin_ref.emit_stop.connect(self.calib_window.stop_clicked)

        self.thread_check_sin_opt = self.ThreadOptAndGenCheckIfReady("127.0.0.1", 501, 1,
                                                                     100, 25, 0.003,
                                                                     self.start_window, self.my_settings, self.thcfgs)
        self.thread_check_sin_opt.check_ready_opt.connect(self.calib_window.opt_emit)
        self.thread_check_sin_opt.check_ready_gen.connect(self.calib_window.gen_emit)
        self.thread_check_sin_opt.check_gen_error.connect(self.calib_window.gen_error_emit)
        self.thread_check_sin_opt.finished.connect(self.opt_finished)
        self.thread_check_sin_opt.out_value.connect(self.calib_window.update_wl_values)
        if self.thread_check_sensors is None:
            print("BUILDING SENS CHECK....")
            self.thread_check_sensors = self.ThreadSensorsCheckIfReady(self.thcfgs, self.my_settings, auto_calib=self)
            self.thread_check_sensors.check_ready.connect(self.calib_window.check_sensors_ready)
            # self.thread_check_sensors.finished.connect(self.thread_end_check_sens)
            self.thread_check_sensors.start()
        else:
            if not self.thread_check_sensors.isRunning():
                print("STARTING SENS CHECK....")
                self.thread_check_sensors = self.ThreadSensorsCheckIfReady(self.thcfgs, self.my_settings,
                                                                           auto_calib=self)
                self.thread_check_sensors.check_ready.connect(self.calib_window.check_sensors_ready)
                # self.thread_check_sensors.finished.connect(self.thread_end_check_sens)
                self.thread_check_sensors.start()
            else:
                print("SENSORS CHECK IS RUNNING....")

        self.thread_check_sin_ref.start()
        self.thread_check_sin_opt.start()
        self.calib_window.ui.start_btn.setEnabled(False)
        self.calib_window.ui.start_btn.setHidden(False)
        self.calib_window.ui.stop_btn.setHidden(True)
        self.calib_window.ui.stop_btn.setEnabled(True)

        self.calib_window.ui.stop_btn.setEnabled(False)
        self.calib_window.ui.S_N_line.setEnabled(True)
        self.calib_window.ui.btn_settings.setEnabled(True)
        self.calib_window.ui.select_config.setEnabled(True)
        self.calib_window.ui.plot_graph_check.setEnabled(True)
        self.calib_window.ui.menubar.setEnabled(True)

    def opt_finished(self):
        self.calib_window.ui.opt_value_wl_label.setText("-")

    def thread_control_gen_finished(self):
        """Spustený po ukoncení vlákna ThreadControlFuncGen"""
        print("END -------> CONTROL GEN")
        self.calib_window.ui.progressBar.setValue(0)
        self.calib_window.data.clear()
        self.calib_window.line.set_ydata([])  # Clear line y-data
        self.calib_window.line.set_xdata([])  # Clear line x-data
        self.calib_window.ax.relim()  # Recalculate axis limits
        self.calib_window.ax.autoscale_view()  # Rescale axis
        self.calib_window.canvas.draw()  # Redraw canvas
        self.thread_check_opt_usb.termination = True
        if self.thcfgs.get_emergency_stop():
            self.calib_window.ui.start_btn.setEnabled(False)
            self.calib_window.ui.start_btn.setHidden(False)
            self.calib_window.ui.stop_btn.setHidden(True)
            self.calib_window.ui.stop_btn.setEnabled(True)

            if not self.thcfgs.get_start_measuring() and self.thcfgs.get_end_sens_test():
                self.thread_ref_sens.task.close()
                self.start()
            if self.thread_check_new_file is not None and self.thread_check_new_file.isRunning():
                self.thread_check_new_file.termination = True
            self.thcfgs.set_finished_measuring(False)
            self.thcfgs.set_start_sens_test(False)
            self.thcfgs.set_end_sens_test(False)
            self.thcfgs.set_start_measuring(False)
        else:
            self.calib_window.ui.output_browser_3.setText(
                self.start_window.translations[self.start_window.lang]["out_brow_calib"])

    def terminate_measure_threads(self):
        """Ukoncí vlákno ThreadRefSensDataCollection a sentinel-d"""
        self.thread_ref_sens.terminate()
        kill_sentinel(True, False)

    def on_btn_start_clicked(self):  # start merania
        """Kontrola pre zahajením kalibrácie"""
        self.thcfgs.set_emergency_stop(False)
        self.plot1.hide()
        self.plot2.hide()
        attempt_count = 0
        max_attempts = 5
        msg_box = None
        try:
            # self.calib_figure.hide()
            start_calibration = True
            print(os_path.exists(
                os_path.join(self.my_settings.folder_calibration_export,
                             self.calib_window.s_n + '.csv')))
            print(self.export_status)
            print(self.calib_result)

            while attempt_count < max_attempts:
                print("ATTEMPT COUNT: ", attempt_count)
                try:
                    if not self.export_status and self.calib_result:
                        self.calib_window.setEnabled(False)
                        # msg_box = QMessageBox()
                        # msg_box.setIcon(QMessageBox.Information)
                        # msg_box.setText(self.start_window.translations[self.start_window.lang]["forgot_export"])
                        # msg_box.setWindowTitle(self.start_window.translations[self.start_window.lang]["export_proceed"])
                        # msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                        # export_button = msg_box.addButton("Export", QMessageBox.ActionRole)
                        # return_value = msg_box.exec()
                        trans = self.start_window.translations
                        lang = self.start_window.lang
                        msg_box = MyGeneralPopUp(parent=self.calib_window, start_window=self.start_window,
                                                 left_btn=trans[lang][
                                                     'close_event_yes'],
                                                 right_btn=trans[lang][
                                                     'close_event_no'],
                                                 label=trans[lang][
                                                     "forgot_export"],
                                                 show_exit=False)
                        msg_box.show_modal()
                        result = msg_box.continue_code
                        if result:
                            start_calibration = True
                        else:
                            start_calibration = False
                        self.calib_window.setEnabled(True)
                    elif (os_path.exists(
                            os_path.join(self.my_settings.folder_calibration_export,
                                         self.calib_window.s_n + '.csv')) or os_path.exists(
                        os_path.join(self.my_settings.folder_calibration_export,
                                     self.calib_window.s_n + '_FAIL.csv'))):
                        self.calib_window.setEnabled(False)
                        # msg_box = QMessageBox()
                        # msg_box.setIcon(QMessageBox.Information)
                        # msg_box.setText(self.start_window.translations[self.start_window.lang]["recalibrate"])
                        # msg_box.setWindowTitle(self.start_window.translations[self.start_window.lang]["recalibrate_2"])
                        # msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                        # return_value = msg_box.exec()
                        trans = self.start_window.translations
                        lang = self.start_window.lang
                        msg_box = MyGeneralPopUp(parent=self.calib_window, start_window=self.start_window,
                                                 left_btn=trans[lang][
                                                     'close_event_yes'],
                                                 right_btn=trans[lang][
                                                     'close_event_no'],
                                                 label=trans[lang][
                                                     "forgot_export"],
                                                 show_exit=False)
                        msg_box.show_modal()
                        result = msg_box.continue_code
                        if result:
                            start_calibration = True
                        else:
                            start_calibration = False
                        self.calib_window.setEnabled(True)

                    break  # Exit the loop if successful
                except Exception as e:
                    attempt_count += 1
                    if msg_box:
                        msg_box.close()
                    if attempt_count >= max_attempts:
                        self.calib_window.ui.output_browser_3.setText(
                            f"{self.start_window.translations[self.start_window.lang]['rand_error']}\n{e}")
                        return
            if start_calibration:
                self.calib_window.ui.output_browser.clear()
                self.calib_window.ui.output_browser_2.clear()
                self.thcfgs.set_start_measuring(False)
                self.thcfgs.set_start_sens_test(False)
                self.thcfgs.set_end_sens_test(False)
                self.calib_window.ui.pass_status_label.setText("PASS")
                self.calib_window.ui.fail_status_label.setText("FAIL")
                self.calib_window.ui.pass_status_label.setStyleSheet("color: rgba(170, 170, 127,150);")
                self.calib_window.ui.fail_status_label.setStyleSheet("color: rgba(170, 170, 127,150);")
                self.calib_window.ui.export_fail_btn.setEnabled(False)
                self.calib_window.ui.export_pass_btn.setEnabled(False)
                self.calib_window.measure = True
                self.calib_window.ui.S_N_line.setEnabled(False)
                self.calib_window.ui.btn_settings.setEnabled(False)
                self.calib_window.ui.btn_load_wl.setEnabled(False)
                self.calib_window.ui.select_config.setEnabled(False)
                self.calib_window.ui.plot_graph_check.setEnabled(False)
                self.calib_window.ui.menubar.setEnabled(False)
                self.calib_window.ui.start_btn.setEnabled(False)
                # if self.my_settings.opt_channels > 1:
                if self.my_settings.opt_channels == 2 and not self.calib_window.wls_were_set:
                    self.calib_window.btn_connect_load_wl()
                    QTimer.singleShot(1000, self.cont_start_calibration)
                else:
                    self.cont_start_calibration()

        except Exception as e:
            save_error(self.my_settings.starting_folder, e)
            self.calib_window.ui.output_browser_3.setText(f"Error occurred, (try again) :\n{e}")
        print("START CALIB END LINE")

    def cont_start_calibration(self):
        """Spustenie kalibrácie"""
        self.thread_check_opt_usb = ThreadCheckDevicesConnected(self.my_settings, self.start_window, True)
        self.thread_check_opt_usb.opt_connected.connect(self.check_usb_opt)
        self.thread_control_gen = self.ThreadControlFuncGen(self.my_settings.generator_id,
                                                            self.my_settings.generator_sweep_time,
                                                            self.my_settings.generator_sweep_start_freq,
                                                            self.my_settings.generator_sweep_stop_freq,
                                                            self.my_settings.generator_sweep_type,
                                                            self.my_settings.generator_max_mvpp,
                                                            self.thcfgs,
                                                            self.my_settings.opt_project,
                                                            self.my_settings.opt_channels,
                                                            self.my_settings.folder_sentinel_D_folder,
                                                            self.start_window,
                                                            self.my_settings)
        self.thread_control_gen.connected_status.connect(self.calib_window.gen_emit)
        self.thread_control_gen.step_status.connect(self.calib_window.write_to_output_browser)
        self.thread_control_gen.finished.connect(self.thread_control_gen_finished)
        self.thread_control_gen.set_btn.connect(self.calib_window.enable_stop_btn)
        self.thread_check_new_file = self.ThreadSentinelCheckNewFile(
            self.my_settings.folder_opt_export)
        self.thread_check_new_file.finished.connect(self.thread_check_new_file_finished)
        self.thread_ref_sens = self.ThreadRefSensDataCollection(self.start_window, self.thcfgs,
                                                                self.calib_window.s_n, self.my_settings,
                                                                self.calib_window.s_n_export)
        self.thread_ref_sens.finished.connect(self.thread_ref_sens_finished)
        self.thread_ref_sens.out_value.connect(self.calib_window.update_data)
        self.thread_ref_sens.emit_stop.connect(self.calib_window.stop_clicked)
        self.thread_control_gen.start()
        self.thread_check_opt_usb.start()
        self.calib_window.ui.stop_btn.setHidden(False)
        self.calib_window.ui.start_btn.setHidden(True)
        self.calib_window.ui.start_btn.setEnabled(False)
        self.calibration_profile = f"{self.my_settings.generator_sweep_start_freq}-{self.my_settings.generator_sweep_stop_freq}Hz; {self.my_settings.generator_max_mvpp}mVpp; {self.my_settings.generator_sweep_time}s; {self.my_settings.generator_sweep_type}"
        self.calib_window.ui.widget_graph.setHidden(False)
        self.plot1 = MyPlottingWindow(self.calib_window, self.start_window, self.my_settings)
        self.plot2 = PlotSlope(self.calib_window, self.start_window, self.my_settings)

    def check_usb_opt(self, opt):
        if not opt:
            self.thcfgs.set_emergency_stop(True)

    def thread_ref_sens_finished(self):
        """Vykonáva sa po ukončení vlákna pre meranie referenčného snímača a vyhodnotenie kalibrácie"""
        print("END -------> REF MEASURE")
        # print("EMERGENCY STOP : " + str(self.thcfgs.get_emergency_stop()))
        if not self.thcfgs.get_emergency_stop():
            self.wl_slopes = self.thread_ref_sens.wl_slopes
            acc_calib = self.thread_ref_sens.acc_calib
            sens_diff = np_abs(self.my_settings.calib_optical_sensitivity - acc_calib[1])
            strike = 0

            if sens_diff < self.my_settings.calib_optical_sens_tolerance:
                sens_color = "black"
            elif sens_diff < self.my_settings.calib_optical_sens_tolerance * 1.005:
                sens_color = "orange"
                strike += 0.5
            else:
                sens_color = "red"
                strike += 2

            if np_abs(acc_calib[7]) < 2.5:
                symm_color = "black"
            elif np_abs(acc_calib[7]) < 3.0:
                symm_color = "orange"
                strike += 0.5
            else:
                symm_color = "red"
                strike += 2

            if np_abs(self.wl_slopes[1]) < self.my_settings.slope_check:
                diff1_color = "black"
            elif np_abs(self.wl_slopes[1]) < self.my_settings.slope_check * 1.01:
                diff1_color = "orange"
                strike += 0.5 if (self.my_settings.opt_channels >= 2) else 1
            else:
                diff1_color = "red"
                strike += 2
            if self.my_settings.opt_channels >= 2:
                if np_abs(self.wl_slopes[4]) < self.my_settings.slope_check:
                    diff2_color = "black"
                elif np_abs(self.wl_slopes[4]) < self.my_settings.slope_check * 1.01:
                    diff2_color = "orange"
                    strike += 0.5
                else:
                    diff2_color = "red"
                    strike += 2

            fltnss_color = "black"
            self.calib_window.ui.widget_graph.setHidden(True)
            self.calib_window.ui.output_browser_2.setText(":")
            self.calib_window.ui.output_browser_2.append(f"<font><b>{self.calib_window.s_n_export}</b></font>")
            self.calib_window.ui.output_browser.setText(
                f"{self.start_window.translations[self.start_window.lang]['out_cal_res']}")
            self.calib_window.ui.output_browser.append("# SN :")
            self.calib_window.ui.output_browser.append(
                self.start_window.translations[self.start_window.lang]["center_wl"])

            if len(acc_calib) <= 9:
                self.calib_window.ui.output_browser_2.append(str(acc_calib[0]) + ' nm')
            else:
                self.calib_window.ui.output_browser_2.append(str(acc_calib[0]) + '; ' + str(acc_calib[9]) +
                                                             ' nm')

            self.calib_window.ui.output_browser.append(
                f"{self.start_window.translations[self.start_window.lang]['sens']}" + '\n' +
                f"{self.start_window.translations[self.start_window.lang]['flatness']}" + '\n' +
                f"{self.start_window.translations[self.start_window.lang]['symm']}" + '\n' +
                f"{self.start_window.translations[self.start_window.lang]['slope_check']}")

            self.calib_window.ui.output_browser_2.append(
                f"<font color='{sens_color}'>{str(round(acc_calib[1], 3))} pm/g at {str(self.my_settings.calib_gain_mark)} Hz</font>"
            )

            self.calib_window.ui.output_browser_2.append(
                f"<font color='{fltnss_color}'>{str(acc_calib[4])} between {str(acc_calib[2])} Hz and  {str(acc_calib[3])} Hz</font>"
            )

            self.calib_window.ui.output_browser_2.append(f"<font color='{symm_color}'>{str(acc_calib[7])} %</font>")

            text_to_append = f"<font color='{diff1_color}'>{str(self.wl_slopes[1])}</font>"
            if self.my_settings.opt_channels >= 2:
                text_to_append += f", <font color='{diff2_color}'>{str(self.wl_slopes[4])}</font>"

            self.calib_window.ui.output_browser_2.append(text_to_append)

            self.last_validation = self.check_if_calib_is_valid(strike)
            with open(self.thread_ref_sens.ref_file_path, 'a') as file:
                file.write("Validation: " + ("PASS" if self.last_validation else "FAIL") + '\n')
            self.calib_window.ui.S_N_line.setEnabled(True)
            self.calib_window.ui.btn_settings.setEnabled(True)
            self.calib_window.ui.select_config.setEnabled(True)
            self.calib_window.ui.plot_graph_check.setEnabled(True)
            self.calib_window.ui.menubar.setEnabled(True)
            self.calib_output = self.thread_ref_sens.out
            self.time_stamp = self.thread_ref_sens.time_stamp
            self.acc_calib = self.thread_ref_sens.acc_calib
            self.last_s_n = self.calib_window.s_n
            self.last_s_n_export = self.calib_window.s_n_export
            self.plot_graphs()
            if self.my_settings.calib_plot:
                self.plot2.show()
                self.plot1.show()
            if self.my_settings.auto_export:
                self.export_to_database()
            else:
                self.calib_window.ui.output_browser_3.setText(
                    self.start_window.translations[self.start_window.lang]["auto_export_off"])
        else:
            self.calib_window.ui.output_browser_3.setText(
                self.start_window.translations[self.start_window.lang]["emergency_finished"])
            start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                                  self.my_settings.subfolder_sentinel_project,
                                  self.my_settings.opt_project, self.my_settings.opt_channels)
        self.rename_files()
        self.start()

    def rename_files(self):
        """Premenuje súbory"""
        print(self.last_validation)
        if not self.last_validation:
            # List of folder names where the renaming should take place
            folder_names = ["calibration", "optical", "optical_raw", "reference", "reference_raw"]

            for folder_name in folder_names:
                # Construct the full path for each folder
                folder_path = os_path.join(self.my_settings.folder_main, folder_name)
                # Construct the old and new file names
                old_name = os_path.join(folder_path, self.last_s_n + ".csv")
                new_name = os_path.join(folder_path, self.last_s_n + "-FAIL.csv")

                # Check if the new file name already exists, if so, remove it
                if os_path.exists(new_name):
                    os_remove(new_name)

                # Rename the old file to the new file name, if it exists
                if os_path.exists(old_name):
                    os_rename(old_name, new_name)

    def plot_graphs(self):
        """Vykreslí grafy"""
        self.plot2.plot_graphs(self.wl_slopes)
        w = self.plot1.plot_graphs(self.calib_output)
        current_y = self.calib_window.y()
        self.calib_window.move(w, current_y)

    def thread_prog_bar_finished(self):
        print("END ------> PROG BAR")
        self.calib_window.ui.progressBar.setValue(0)

    def thread_check_new_file_finished(self):
        """Po kontrole spustenia sentinel-d"""
        print("END ----------->check_new_file")
        if not self.thcfgs.get_emergency_stop():
            self.thread_ref_sens.start()
            self.opt_sentinel_file_name = self.thread_check_new_file.opt_sentinel_file_name
            # self.thread_prog_bar.start()
            self.thcfgs.set_start_measuring(True)
        else:
            print("KILL SENTINEL START MODBUS")
            kill_sentinel(True, True)
            start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                                  self.my_settings.subfolder_sentinel_project, self.my_settings.opt_project,
                                  self.my_settings.opt_channels)

    def check_if_calib_is_valid(self, acc_calib):
        """Kontrola či je kalibrácia OK"""
        self.ow_export = False
        if acc_calib <= 1:
            self.calib_window.ui.pass_status_label.setStyleSheet("color: green;")
            if self.my_settings.auto_export:
                self.calib_window.ui.fail_status_label.setText("NOTE")
            else:
                self.calib_window.ui.fail_status_label.setText("EXPORT")
            self.calib_window.ui.fail_status_label.setStyleSheet("color: grey;")
            self.calib_window.ui.export_pass_btn.setEnabled(True)
            self.calib_window.ui.export_fail_btn.setEnabled(False)
            self.export_status = False
            self.calib_result = True
        else:
            self.calib_window.ui.fail_status_label.setStyleSheet("color: red;")
            self.calib_window.ui.pass_status_label.setText("EXPORT")
            self.calib_window.ui.pass_status_label.setStyleSheet("color: grey;")
            self.calib_window.ui.export_fail_btn.setEnabled(True)
            self.calib_window.ui.export_pass_btn.setEnabled(False)
            self.export_status = False
            self.calib_result = False
            res = self.database.use_fetch_records_by_sylexsn(self.last_s_n_export, "ACC")
            if res == 0:
                self.ow_export = True
        return self.calib_result

    def export_to_database(self, notes="", btn=False):
        """Vykonáva export dát do SQL databázy"""
        if self.calib_result or btn or self.ow_export:
            if not self.export_status:
                params, params2 = get_params(self.last_s_n, self.my_settings.starting_folder)
                self.calib_window.ui.output_browser_3.clear()
                if self.my_settings.export_local_server:
                    if params[0] is not None:
                        export_folder = self.export_to_local_db(str(params[0]))
                    else:
                        self.calib_window.ui.output_browser_3.setText(
                            f"{self.start_window.translations[self.start_window.lang]['sensor_id_not_found']}")
                        export_folder = "ERROR/NO ID"
                else:
                    self.calib_window.ui.output_browser_3.setText(
                        f"{self.start_window.translations[self.start_window.lang]['export_to_local_server']}")
                    export_folder = "VYPNUTE/OFF"
                add = [self.last_s_n_export, None, None, True, self.acc_calib[1], self.acc_calib[0],
                       self.acc_calib[9] if (len(self.acc_calib) >= 10) else None, self.acc_calib[4],
                       self.acc_calib[10] if (len(self.acc_calib) >= 10) else None,
                       self.acc_calib[7], export_folder,
                       self.calibration_profile, None, None, notes, self.time_stamp, self.start_window.operator, ]
                params.extend(add)
                params.extend(params2)
                params.append("PASS" if self.calib_result else "FAIL")
                res, e = self.database.export_to_database_acc_strain(params=params, sensor="ACC")
            else:
                res, e = self.database.update_export_note(self.last_s_n_export, notes, sensor="ACC")
            if res == 0:
                self.calib_window.ui.output_browser_3.append(
                    f"{self.start_window.translations[self.start_window.lang]['out_export']}\n")
                self.export_status = True
            elif res == 1:
                self.calib_window.ui.output_browser_3.setText(
                    f"{self.start_window.translations[self.start_window.lang]['out_note_succ']}\n")
            elif res == -1:
                save_error(self.my_settings.starting_folder, e)
                self.calib_window.ui.output_browser_3.setText(
                    self.start_window.translations[self.start_window.lang]['load_wl_error_2'])
            else:
                save_error(self.my_settings.starting_folder, e)
                self.calib_window.ui.output_browser_3.setText("Unexpected error!")

    def export_to_local_db(self, idcko):
        """Vykonáva export dát na lokálny disk"""
        source_folders = {'optical': self.my_settings.folder_opt_export,
                          'reference': self.my_settings.folder_ref_export,
                          'calibration': self.my_settings.folder_calibration_export}
        if os_path.exists(self.my_settings.folder_db_export_folder):
            name = self.last_s_n
            if not self.last_validation:
                name += "-FAIL"
            res, text, export_folder = copy_files(name, idcko, source_folders,
                                                  self.my_settings.folder_db_export_folder)
            if res == 0:
                self.calib_window.ui.output_browser_3.setText(
                    self.start_window.translations[self.start_window.lang]["export_to_local_server_success"])
            elif res == -1:
                export_folder = "Súbor so zakázkou nenájdený/Folder with order not found"
                if isinstance(text, list):
                    # If 'text' is a list, join its elements into a single string with newline characters
                    text_str = "\n".join(
                        map(str, text))  # Using map(str, text) to ensure all elements are converted to strings
                else:
                    # If 'text' is not a list (e.g., already a string or another type), convert it to a string just in case
                    text_str = str(text)
                save_error(self.my_settings.starting_folder, text)
                self.calib_window.ui.output_browser_3.setText(text_str)
                self.calib_window.ui.output_browser.clear()
                self.calib_window.ui.output_browser_2.clear()
        else:
            export_folder = "Cielova cesta nenájdena/Path not found"
            self.calib_window.ui.output_browser_3.setText(
                self.start_window.translations[self.start_window.lang]["db_file_path_not_found"])
        if os_path.exists(self.my_settings.folder_statistics):
            file_name_with_extension = os_path.basename(self.start_window.config_file_path)
            file_name = os_path.splitext(file_name_with_extension)[0]
            if self.my_settings.opt_channels >= 2:
                res = save_statistics_to_csv(self.my_settings.folder_statistics, file_name, self.time_stamp,
                                             self.last_s_n_export, self.acc_calib[1], self.acc_calib[0],
                                             self.acc_calib[9])
            else:
                res = save_statistics_to_csv(self.my_settings.folder_statistics, file_name, self.time_stamp,
                                             self.last_s_n_export, self.acc_calib[1], self.acc_calib[0])
            if res != 0:
                save_error(self.my_settings.starting_folder, res)
                self.calib_window.ui.output_browser_3.setText(res)
                self.calib_window.ui.output_browser.clear()
                self.calib_window.ui.output_browser_2.clear()
        else:
            self.calib_window.ui.output_browser_3.append(
                self.start_window.translations[self.start_window.lang]["statistics_file_path_not_found"])
        return export_folder
