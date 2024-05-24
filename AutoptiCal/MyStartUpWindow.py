import sys

from PyQt5.QtCore import QTimer, QDate, Qt, QRect, QThread
from PyQt5.QtGui import QPixmap, QMovie
from codecs import open as codecs_open
from configparser import ConfigParser
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QSplashScreen, QLabel, QMenu
from yaml import safe_load as yaml_safe_load, safe_dump as yaml_safe_dump
from os import path as os_path, getcwd as os_getcwd

from gui.start_up import Ui_Setup
from Definitions import scale_app, center_on_screen, load_all_config_files, kill_sentinel
from SensAcc.SettingsParams import MySettings as MySettings_acc
from json import load as json_load
from Definitions import start_sentinel_d


def blink_red(label):
    en = label.isEnabled()
    if en:
        label.setEnabled(False)
        label.setStyleSheet("color: black;")
    else:
        label.setEnabled(True)
        label.setStyleSheet("color: #EE1918;")
    return en


class MyStartUpWindow(QMainWindow):
    """SK: Trieda ktorá nám vytvorí úvodné okno, kontrolujeme stav pripojených nastavení,
    voľba typu senzora a konfiguračného súboru pre senzor, možnosť otvoriť nastavenia, výber/úprava operátorov.
    EN: A class that creates the initial window, checks the status of connected settings,
    selects the type of sensor and the configuration file for the sensor, offers the option to open settings,
    and the selection/editing of operators"""

    def __init__(self, splash: QSplashScreen):
        super().__init__()

        self.result_window = None
        self.start_peaklogger_thread = None
        self.probe = False
        self.chmbr = False
        self.settings_window_temp = None
        self.my_settings_window_temp = None
        self.app_name_abbre = None
        self.app_name = None
        self.movie = None
        self.loadingLabel = None
        self.box_remove_op = None
        self.box_start_strain = None
        self.box_close_event = None
        self.pass_window = None
        self.MyGeneralPopUp = None

        def connect_set_buttons():
            self.ui.start_app.setEnabled(False)
            self.ui.open_settings_btn.clicked.connect(self.open_settings_window)
            self.ui.start_app.clicked.connect(self.start_calib_app)
            self.ui.btn_add_operator.clicked.connect(self.add_remove_operator)
            self.ui.actionStrain_ON.triggered.connect(self.enable_strain_triggered)
            self.ui.actionAccelerometer_ON.triggered.connect(self.enable_accelerometer_triggered)

        def connect_combo_boxes():
            self.ui.sens_type_comboBox.currentTextChanged.connect(self.sens_type_combobox_changed)
            self.ui.opt_config_combobox.currentTextChanged.connect(self.config_combobox_changed)
            self.ui.combobox_sel_operator.currentIndexChanged.connect(self.operator_changed)

        def load_images_icons():
            self.ui.logo_label.setPixmap(QPixmap("images/logo.png"))
            icon = QIcon(QPixmap("images/setting_btn.png"))
            self.ui.open_settings_btn.setIcon(icon)
            self.ui.open_settings_btn.setIconSize(self.ui.open_settings_btn.sizeHint())
            self.ui.open_settings_btn.setStyleSheet("""QPushButton {border: 1px solid gray;
                                                    border-color:rgb(208,208,208);
                                                    border-radius: 3px;
                                                    background-color: rgb(245, 245, 245);
                                                    color: rgb(0, 0, 0);}
                                                    QPushButton:hover {
                                                    background-color: rgba(150, 190, 13, 100);
                                                    }
                                                    QPushButton:disabled {
                                                    color: rgb(156, 156, 156);
                                                    background-color: rgb(220, 220, 220);
                                                    }""")
            self.setWindowIcon(QIcon('images/icon.png'))

        def setup_window():
            self.setWindowFlags(
                self.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowMaximizeButtonHint)
            self.setWindowTitle(" ")
            self.setFixedSize(self.width(), int(self.height() * 0.95))
            scale_app(self, self.window_scale)
            self.setFixedSize(int(self.width() * self.window_scale),
                              int(self.height() * self.window_scale))

        def set_labels():
            self.ui.null_detect_label.setHidden(True)
            self.ui.status_opt_label.setStyleSheet("color: black;")
            self.ui.status_ref_label.setStyleSheet("color: black;")
            self.ui.status_gen_label.setStyleSheet("color: black;")
            self.ui.open_settings_btn.setStyleSheet("QPushButton {border: 1px solid gray;"
                                                    "text-align: center;"
                                                    "border-color:rgb(208,208,208);"
                                                    "border-radius: 3px;"
                                                    "background-color: rgb(245, 245, 245);"
                                                    "color: rgb(0, 0, 0);}"
                                                    "QPushButton:hover {"
                                                    "background-color: rgba(150, 190, 13, 100);}")

        self.is_accelerometer_enabled = True
        self.is_strain_enabled = True
        self.is_temperature_enabled = True

        self.block_status_update = False
        self.my_main_window_strain = None
        self.my_main_window_acc = None
        self.my_settings_window_strain = None
        self.my_settings_window_acc = None
        self.worker = None
        self.bad_ref = False
        self.check_status = False
        self.gen_error = False
        self.gen_connected = False
        self.opt_connected = False
        self.lang = "sk"
        self.version = None
        self.last_ref_calib = None
        self.translations = None
        self.calib_treshold = 180
        self.operators = []
        self.thread_check_usb_devices = None
        self.splash = splash
        self.window_scale_delta = 1
        self.window_scale = 1
        self.yaml_devices_vendor = 'devices_vendor_ids.yaml'
        self.yaml_database_com = 'database_com.yaml'
        self.opt_dev_vendor = None
        self.ref_dev_vendor = None
        self.opt_first_start = True
        self.check_usbs_first_start = True
        self.calib_window = None
        self.settings_window_acc = None
        self.settings_window_strain = None
        self.S_N = None
        self.operator = None
        self.current_conf = None
        self.ref_connected = False
        self.sens_type = None
        self.starting_folder = os_getcwd()
        self.load_global_settings()
        self.ui = Ui_Setup()
        self.ui.setupUi(self)
        self.load_sens_types()
        if self.sens_type == "Accelerometer":
            self.my_settings = MySettings_acc(self.starting_folder)
        else:
            self.my_settings = None
        self.config = None
        self.config_contains_none = True

        self.set_language()
        connect_set_buttons()
        connect_combo_boxes()
        self.load_operators()
        set_labels()
        load_images_icons()
        if self.my_settings:
            self.config_file_path = self.check_config_if_selected()
            self.check_devices_load_comboboxes_load_config_file()
            self.load_usb_dev_vendors()
        setup_window()
        kill_sentinel(True, True)
        self.ui.ver_label.setText(f"v.{self.version}")
        # self.statusBar = QStatusBar()
        # self.setStatusBar(self.statusBar)
        self.loading_gif()
        self.ui.app_label.setText(self.app_name)
        self.show_back()

    def enable_temperature_triggered(self):
        """SK: Povolenie/zakazanie funkcionality accelerometer kalibracie.
        EN: Enabling/disabling the functionality of the accelerometer calibration."""
        self.is_temperature_enabled = False if self.is_temperature_enabled else True
        with open("global_settings.yaml", 'r') as file:
            config = yaml_safe_load(file)
        config['enabled_functionalities']['temperature'] = self.is_temperature_enabled
        with open("global_settings.yaml", 'w') as file:
            yaml_safe_dump(config, file)

    def enable_strain_triggered(self):
        """SK: Povolenie/zakazanie funkcionality accelerometer kalibracie.
        EN: Enabling/disabling the functionality of the accelerometer calibration."""
        self.is_strain_enabled = False if self.is_strain_enabled else True
        with open("global_settings.yaml", 'r') as file:
            config = yaml_safe_load(file)
        config['enabled_functionalities']['strain'] = self.is_strain_enabled
        with open("global_settings.yaml", 'w') as file:
            yaml_safe_dump(config, file)

    def enable_accelerometer_triggered(self):
        """SK: Povolenie/zakazanie funkcionality strain kalibracie.
        EN: Enabling/disabling the functionality of the strain calibration."""
        self.is_accelerometer_enabled = False if self.is_accelerometer_enabled else True
        with open("global_settings.yaml", 'r') as file:
            config = yaml_safe_load(file)
        config['enabled_functionalities']['accelerometer'] = self.is_accelerometer_enabled
        with open("global_settings.yaml", 'w') as file:
            yaml_safe_dump(config, file)

    def contextMenuEvent(self, event):
        """SK: Override pre contex menu, ktore sa otvori pravym klikom mysi,
        v tomto menu vieme zapnut vypnut funkcionality aplikacie.
        EN: Override the context menu that opens with a right-click of the mouse,
        in this menu, we can turn on or off the functionalities of the application."""
        cmenu = QMenu(self)

        acc = cmenu.addAction("Accelerometer - ON" if self.is_accelerometer_enabled else "Accelerometer - OFF")
        strain = cmenu.addAction("Strain - ON" if self.is_strain_enabled else "Strain - OFF")
        temp = cmenu.addAction("Temperature - ON" if self.is_temperature_enabled else "Temperature - OFF")
        action = cmenu.exec_(self.mapToGlobal(event.pos()))

        if action == acc:
            self.enable_accelerometer_triggered()
        elif action == strain:
            self.enable_strain_triggered()
        elif action == temp:
            self.enable_temperature_triggered()

    def add_remove_operator(self):
        """SK: Funkcia na prídavanie/vymazanie operátora do/z listu operátorov, vytvorenie pop-up okna na
        interakciu s uživateľom.
        EN:Function for adding/deleting an operator to/from the list of operators, creating a pop-up window for
        interaction with the user"""

        def show_remove_dialog():
            def load_and_delete_operator(operator_to_delete, yaml_file_path="operators.yaml"):
                try:
                    # Load YAML file
                    with open(yaml_file_path, 'r') as f:
                        operators = yaml_safe_load(f)

                    # Check if operator exists and delete
                    if operator_to_delete in operators['operators']:
                        operators['operators'].remove(operator_to_delete)

                        # Update YAML file
                        with open(yaml_file_path, 'w') as f:
                            yaml_safe_dump(operators, f)
                        return f"Operator '{operator_to_delete}' successfully deleted."
                    else:
                        return f"Operator '{operator_to_delete}' not found."
                except Exception as e:
                    from Definitions import save_error
                    save_error(self.my_settings.starting_folder, e)
                    return f"An error occurred: {e}"

            op_to_remv = self.ui.combobox_sel_operator.currentText()

            self.box_remove_op.ui.label.setText(f"{self.translations[self.lang]['remove_op_msg']}\n{op_to_remv}")

            self.box_remove_op.show_modal()
            result = self.box_remove_op.continue_code

            if result:
                load_and_delete_operator(op_to_remv)
                self.load_operators()
                self.operator_changed(0)
                # Logic to remove operator here

        if self.ui.combobox_sel_operator.currentIndex() != 0:
            show_remove_dialog()
        else:
            from Definitions import show_add_dialog
            show_add_dialog(self, self.starting_folder, self.lang, self.translations, parent=self)

    def load_operators(self, select_operator=None):
        """SK: Funkcia ktorá načítava operátorov z yaml súboru.
        EN: A function that loads operators from a YAML file."""
        self.ui.combobox_sel_operator.blockSignals(True)
        self.ui.combobox_sel_operator.clear()
        self.ui.combobox_sel_operator.addItem(self.translations[self.lang]["combobox_sel_operator"])
        file_path = "operators.yaml"
        try:
            with open(file_path, 'r') as f:
                data = yaml_safe_load(f)
            self.operators = data.get('operators', [])
            for operator in self.operators:
                self.ui.combobox_sel_operator.addItem(operator)
            if select_operator:
                self.ui.combobox_sel_operator.setCurrentText(select_operator)
                self.operator_changed(1)
        except Exception as e:
            print(f"An error occurred while loading the YAML file: {e}")
        self.ui.combobox_sel_operator.blockSignals(False)

    def operator_changed(self, idx):
        """SK: Funkcia ktorá pri zmene operátora (combobox) uloží vybraného operátora a následne vykoná kontrolu
        či sa štart tlačidlo povolí.
        EN: A function that, upon changing the operator (combobox), saves the selected operator and then performs
        a check to determine if the start button is enabled."""
        self.operator = self.ui.combobox_sel_operator.itemText(idx)
        if idx != 0:
            self.ui.btn_add_operator.setText("-")
        else:
            self.ui.btn_add_operator.setText("+")
        if (self.ref_connected and self.opt_connected and self.gen_connected and self.ui.start_app.text() ==
                self.translations[self.lang]["start_app_a"] and not self.gen_error and
                self.ui.combobox_sel_operator.currentIndex() != 0 and self.my_settings.opt_channels != 0 and not self.config_contains_none and not self.bad_ref):
            self.ui.start_app.setEnabled(True)
        else:
            self.ui.start_app.setEnabled(False)

    def config_combobox_changed(self, text):
        """SK: Funckia ktorá pri zmene konfiguračného súboru pre senzor, načíta zvolený konfiguračný súbor a
        vykoná kontrolu či sú všetky parametre riadne vyplnené.
        EN: A function that, upon changing the configuration file for a sensor, loads the selected configuration file and
        performs a check to ensure that all parameters are properly filled out."""
        try:
            with open(self.config_file_path, 'r') as file:
                config = yaml_safe_load(file)
            config_file_path = os_path.join(self.my_settings.subfolderConfig_path, f"{text}.yaml")
            with open(config_file_path, 'r') as file:
                config_check = yaml_safe_load(file)
            if config['opt_measurement']['sensor_type'] == config_check['opt_measurement']['sensor_type']:
                self.current_conf = False
                self.config_contains_none = self.my_settings.save_config_file(False, self.config_file_path)

            self.config_file_path = os_path.join(self.my_settings.subfolderConfig_path, f"{text}.yaml")
            self.check_devices_load_comboboxes_load_config_file()
            self.current_conf = True
            self.config_contains_none = self.my_settings.save_config_file(True, self.config_file_path)
        except Exception as e:
            print(e)

    def load_usb_dev_vendors(self):
        """SK: Funkcia slúži na načítanie VID alebo PID pre používané zariadenia, ktoré sa používajú pri kontrole.
        EN: A function for loading the VID or PID for devices used in check."""
        config_file_path = os_path.join(self.starting_folder, self.yaml_devices_vendor)
        with open(config_file_path, 'r') as file:
            data = yaml_safe_load(file)
        if self.ui.sens_type_comboBox.currentText() != "":
            self.opt_dev_vendor = data[self.ui.sens_type_comboBox.currentText()]['optical']
            self.ref_dev_vendor = data[self.ui.sens_type_comboBox.currentText()]['reference']

    def config_contains_null_style(self, ow):
        if not self.config_contains_none:
            self.ui.open_settings_btn.setText(self.translations[self.lang]["open_settings_btn"])
            self.ui.open_settings_btn.setStyleSheet("QPushButton {border: 1px solid gray;"
                                                    "text-align: center;"
                                                    "border-color:rgb(208,208,208);"
                                                    "border-radius: 3px;"
                                                    "background-color: rgb(245, 245, 245);"
                                                    "color: rgb(0, 0, 0);}"
                                                    "QPushButton:hover {"
                                                    "background-color: rgba(150, 190, 13, 100);}")
        if self.config_contains_none or ow:
            if self.ui.null_detect_label.isEnabled():

                self.ui.null_detect_label.setEnabled(False)

                self.ui.open_settings_btn.setText(self.translations[self.lang]["open_settings_btn"])
                self.ui.open_settings_btn.setStyleSheet("QPushButton {border: 1px solid gray;"
                                                        "text-align: center;"
                                                        "border-color:rgb(208,208,208);"
                                                        "border-radius: 3px;"
                                                        "background-color: rgb(245, 245, 245);"
                                                        "color: #EE1918;}"
                                                        "QPushButton:hover {"
                                                        "background-color: rgba(150, 190, 13, 100);}")
            else:

                self.ui.null_detect_label.setEnabled(True)

                self.ui.open_settings_btn.setText(self.translations[self.lang]["open_settings_btn"])
                self.ui.open_settings_btn.setStyleSheet("QPushButton {border: 1px solid gray;"
                                                        "text-align: center;"
                                                        "border-color:rgb(208,208,208);"
                                                        "border-radius: 3px;"
                                                        "background-color: rgb(245, 245, 245);"
                                                        "color: rgb(0, 0, 0);}"
                                                        "QPushButton:hover {"
                                                        "background-color: rgba(150, 190, 13, 100);}")

    def all_dev_connected_signal_temperature(self, chmbr, probe, check_status=False):
        self.chmbr = chmbr
        self.probe = probe
        ow = False
        self.ui.status_opt_label.setText("...")
        self.ui.status_opt_label.setStyleSheet("color: black;")
        if (chmbr and probe and self.ui.combobox_sel_operator.currentIndex() != 0 and not self.config_contains_none and
            self.ui.start_app.text() == self.translations[self.lang]["start_app_a"]) or ow:
            self.ui.start_app.setEnabled(True)
        else:
            self.ui.start_app.setEnabled(False)
        if check_status:
            self.config_contains_null_style(ow)
            if not chmbr:
                self.ui.status_gen_label.setText(
                    self.translations[self.lang]['start_window_status_chamber']['disconnected'])
                blink_red(self.ui.status_gen_label)
            else:
                self.ui.status_gen_label.setText(self.translations[self.lang]['start_window_status_chamber']['connected'])
                self.ui.status_gen_label.setStyleSheet("color: #96be0d;")
            if not probe:
                self.ui.status_ref_label.setText(self.translations[self.lang]['start_window_status_probe']['disconnected'])
                blink_red(self.ui.status_ref_label)
            else:
                self.ui.status_ref_label.setText(self.translations[self.lang]['start_window_status_probe']['connected'])
                self.ui.status_ref_label.setStyleSheet("color: #96be0d;")

    def all_dev_connected_signal_strain(self, opt_connected=True, ref_connected=False, check_status=False):
        """SK: Funkcia kontroluje pripojené zariadenia pre strain kalibráciu a upravuje status pre dané zariadenie pre
        interakciu s uživateľom.
        EN: A function that checks connected devices for strain calibration and modifies the status for a given device for
        interaction with the user."""
        self.opt_connected = True
        self.ref_connected = ref_connected
        self.gen_connected = True

        if not self.block_status_update:
            ow = False
            if (ref_connected and self.ui.start_app.text() == self.translations[self.lang][
                "start_app_a"] and
                self.ui.combobox_sel_operator.currentIndex() != 0 and self.my_settings.opt_channels != 0 and not self.config_contains_none) or ow:
                self.ui.start_app.setEnabled(True)
            else:
                self.ui.start_app.setEnabled(False)
            self.ui.status_ref_label.setText("...")
            self.ui.status_ref_label.setStyleSheet("color: black;")
            self.ui.status_opt_label.setText("...")
            self.ui.status_opt_label.setStyleSheet("color: black;")
            if check_status:
                # print(self.config_contains_none)
                self.config_contains_null_style(ow)
                if not ref_connected:
                    self.ui.status_gen_label.setText(
                        self.translations[self.lang]["status_ref_label_benchtop"]["disconnect"])
                    blink_red(self.ui.status_gen_label)
                    if self.ref_connected:
                        self.check_devices_load_comboboxes_load_config_file()
                        self.ref_connected = False
                else:
                    self.ui.status_gen_label.setText(
                        self.translations[self.lang]["status_ref_label_benchtop"]["connected"])
                    self.ui.status_gen_label.setStyleSheet("color: #96be0d;")
                    if not self.ref_connected:
                        self.ref_connected = True
                        self.check_devices_load_comboboxes_load_config_file()

    def all_dev_connected_signal(self, opt_connected=False, ref_connected=False, gen_connected=False, gen_error=False,
                                 check_status=False, bad_ref=False):
        """SK: Funkcia kontroluje pripojené zariadenia pre acc kalibráciu a upravuje status pre dané zariadenie pre
        interakciu s uživateľom.
        EN: A function that checks connected devices for acc calibration and modifies the status for a given device for
        interaction with the user."""
        self.opt_connected = opt_connected
        self.ref_connected = ref_connected
        self.gen_connected = gen_connected
        self.gen_error = gen_error
        self.check_status = check_status
        self.bad_ref = bad_ref
        ow = False
        if (ref_connected and opt_connected and gen_connected and self.ui.start_app.text() ==
            self.translations[self.lang]["start_app_a"] and not gen_error and
            self.ui.combobox_sel_operator.currentIndex() != 0 and self.my_settings.opt_channels != 0 and not self.config_contains_none and not bad_ref) or ow:
            self.ui.start_app.setEnabled(True)
        else:
            self.ui.start_app.setEnabled(False)

        if check_status:
            self.config_contains_null_style(ow)
            if not ref_connected and not bad_ref:
                self.ui.status_ref_label.setText(self.translations[self.lang]["status_ref_label"]["disconnect"])
                blink_red(self.ui.status_ref_label)
                if self.ref_connected:
                    self.check_devices_load_comboboxes_load_config_file()
                    self.ref_connected = False
            elif bad_ref:
                self.ui.status_ref_label.setText(self.translations[self.lang]["status_ref_label"]["wrong_name"])
                blink_red(self.ui.status_ref_label)
                if self.ref_connected:
                    self.check_devices_load_comboboxes_load_config_file()
                    self.ref_connected = False
            else:
                self.ui.status_ref_label.setText(self.translations[self.lang]["status_ref_label"]["connected"])
                self.ui.status_ref_label.setStyleSheet("color: #96be0d;")
                if not self.ref_connected:
                    self.ref_connected = True
                    self.check_devices_load_comboboxes_load_config_file()

            if not opt_connected:
                self.ui.status_opt_label.setText(self.translations[self.lang]["status_opt_label"]["disconnect"])
                blink_red(self.ui.status_opt_label)
            else:
                self.ui.status_opt_label.setText(self.translations[self.lang]["status_opt_label"]["connected"])
                self.ui.status_opt_label.setStyleSheet("color: #96be0d;")

            if not gen_connected:
                self.ui.status_gen_label.setText(self.translations[self.lang]["status_gen_label"]["disconnect"])
                blink_red(self.ui.status_gen_label)
            else:
                if gen_error:
                    if blink_red(self.ui.status_gen_label):
                        self.ui.status_gen_label.setText(self.translations[self.lang]["status_gen_label"]["error_b"])
                    else:
                        self.ui.status_gen_label.setText(self.translations[self.lang]["status_gen_label"]["error_a"])
                else:
                    self.ui.status_gen_label.setText(self.translations[self.lang]["status_gen_label"]["connected"])
                    self.ui.status_gen_label.setStyleSheet("color: #96be0d;")

    def sens_type_combobox_changed(self, text):
        """SK: Funkcia načíta všetky konfiguračné súbory, VID a PID pre daný/zvolený typ senzora a načíta posledne použitý
        konfiguračný súbor.
        EN: A function that loads all configuration files, VID, and PID for a given/selected type of sensor, and loads the
        last used configuration file."""
        if self.sens_type != text:
            self.ui.status_gen_label.setText("...")
            self.ui.status_gen_label.setStyleSheet("color: black;")
            self.ui.status_opt_label.setText("...")
            self.ui.status_opt_label.setStyleSheet("color: black;")
            self.ui.status_ref_label.setText("...")
            self.ui.status_ref_label.setStyleSheet("color: black;")
        self.opt_connected = False
        self.ref_connected = False
        self.gen_connected = False
        self.ui.start_app.setEnabled(False)
        self.load_usb_dev_vendors()
        self.my_settings.opt_sensor_type = text
        self.sens_type = text
        self.config_file_path = self.check_config_if_selected()
        load_all_config_files(self.ui.opt_config_combobox, self.config_file_path, self.sens_type,
                              self.my_settings.subfolderConfig_path)

        self.check_devices_load_comboboxes_load_config_file()

    def return_all_configs(self):
        """SK: Funkcia vracia všetky konfiguračné súbory pre daný typ senzora.
        EN: A function that returns all configuration files for a given type of sensor."""
        from glob import glob
        yaml_files = glob(os_path.join(self.my_settings.subfolderConfig_path, '*.yaml'))
        yaml_return = []
        for yaml_file in yaml_files:
            try:
                config_file_path = os_path.join(self.my_settings.subfolderConfig_path, yaml_file)
                with open(config_file_path, 'r') as file:
                    config = yaml_safe_load(file)
                    if config['opt_measurement']['sensor_type'] == self.sens_type:
                        yaml_return.append(yaml_file)
            except:
                continue
        return yaml_return

    def check_config_if_selected(self):
        """SK: Funkcia nám vracia posledný použitý konfiguračný súbor.
        EN: A function that returns the last used configuration file."""
        yaml_files = self.return_all_configs()
        for yaml_file in yaml_files:
            config_file_path = os_path.join(self.my_settings.subfolderConfig_path, yaml_file)
            with open(config_file_path, 'r') as file:
                config = yaml_safe_load(file)
                if config['current']:
                    return config_file_path
        return None

    def load_sens_types(self):
        self.ui.sens_type_comboBox.blockSignals(True)
        self.ui.sens_type_comboBox.clear()
        if self.is_accelerometer_enabled:
            self.ui.sens_type_comboBox.addItem('Accelerometer')
        if self.is_temperature_enabled:
            self.ui.sens_type_comboBox.addItem('Temperature')
        if self.is_strain_enabled:
            self.ui.sens_type_comboBox.addItem('Strain')
        self.ui.sens_type_comboBox.setCurrentText(self.sens_type if self.sens_type is not None else None)
        self.sens_type = self.ui.sens_type_comboBox.currentText()
        self.ui.sens_type_comboBox.blockSignals(False)

    def check_devices_load_comboboxes_load_config_file(self):
        """SK: Funkcia ktorá nám načíta comboboxi a class 'my_settings' pre daný typ senzora
        EN: A function that loads comboboxes and class 'my_settings' for a given type of sensor."""

        self.ui.opt_config_combobox.blockSignals(True)
        # load optical sensor types
        self.load_sens_types()
        if self.ui.sens_type_comboBox.currentText() != "":
            if self.sens_type == "Accelerometer":
                self.my_settings = MySettings_acc(self.starting_folder)
            try:
                if self.thread_check_usb_devices is not None:
                    self.thread_check_usb_devices.my_settings = self.my_settings
            except Exception:
                pass

            load_all_config_files(self.ui.opt_config_combobox, self.config_file_path, self.sens_type,
                                  self.my_settings.subfolderConfig_path)

            if self.config_file_path is not None and os_path.exists(self.config_file_path):
                self.config_contains_none = self.my_settings.load_config_file(self.config_file_path)
            else:
                self.config_contains_none, self.config_file_path = self.my_settings.create_config_file()

        self.ui.opt_config_combobox.blockSignals(False)

    def open_settings_window(self):
        """SK: Funckia ktorá nám otvorí okno s nastaveniami.
        EN: A function that opens a window with settings."""
        text = self.ui.sens_type_comboBox.currentText()
        if self.thread_check_usb_devices:
            print("TERMINATING CHECK THREAD")
            self.thread_check_usb_devices.termination = True
        if text == "Accelerometer":
            self.settings_window_acc.my_settings = self.my_settings
            self.settings_window_acc.show_back()
            self.hide()
        elif text == "Strain":
            self.settings_window_strain.my_settings = self.my_settings
            self.settings_window_strain.show_back()
            self.hide()
        elif text == "Temperature":
            self.settings_window_temp.my_settings = self.my_settings
            self.settings_window_temp.show_back()
            self.hide()

    def start_calib_app(self):
        """SK: Funckia ktorá na základne aký typ senzora zavolá funckiu na spustenie okna na
        kalibráciu daného typu senzora.
        EN: A function that, based on the type of sensor, calls a function to launch the calibration window for that
        specific type of sensor."""
        if self.my_settings is not None:
            text = self.ui.sens_type_comboBox.currentText()
            if text == "Accelerometer":
                self.start_acc()
        else:
            raise Exception("my_settings is somehow None...")

    def start_acc(self):
        """SK: Funckia ktorá nám spustí funkciu start_any() a spustí funkciu na načítanie acc kalibračného okna.
        EN: A function that initiates the start_any() function and launches the function for loading the acc
        calibration window."""
        self.start_loading_gif()
        QTimer.singleShot(50, self.start_any)
        QTimer.singleShot(100, self.start_acc_window)

    def start_any(self):
        """SK: Funkcia ktorá nám vykoná všetky potrebné úkony pre úspešné spustenie kalibračného okna.
        EN: A function that performs all necessary actions for the successful launch of the calibration window."""
        self.save_sens_type()
        self.ui.start_app.setStyleSheet("QPushButton:hover { background-color: none; }")
        self.ui.start_app.setText(self.translations[self.lang]["start_app_b"])
        self.thread_check_usb_devices.termination = True
        self.ui.centralwidget.setEnabled(False)

    def start_acc_window(self):
        """SK: Funkcia ktorá nám načíta acc okno na kalibráciu a spustí sentinel-D.
           EN: A function that loads the strain calibration window and starts sentinel-D."""
        self.ui.start_app.setText(self.translations[self.lang]["start_app_b"])
        from SensAcc.MyMainWindow import MyMainWindow
        path_config = os_path.join(self.my_settings.folder_sentinel_D_folder, "config.ini")
        config = ConfigParser()
        with codecs_open(path_config, 'r', encoding='utf-8-sig') as f:
            config.read_file(f)
        config.set('general', 'export_folder_path', self.my_settings.folder_opt_export)
        with open(path_config, 'w') as configfile:
            config.write(configfile)
        start_sentinel_d(self.my_settings.opt_project, self.my_settings.folder_sentinel_D_folder,
                         self.my_settings.subfolder_sentinel_project)
        self.operator = self.ui.combobox_sel_operator.currentText()
        self.calib_window = MyMainWindow(self, self.my_settings)
        QTimer.singleShot(200, lambda: self.calib_window.first_sentinel_start(self.operator))
        QTimer.singleShot(300, self.check_last_calib)

    def show_back(self):
        """SK: Funckia ktorá nám vykonáva zmeny pozície a veľkosti okna pred tým ako sa zavolá show() funkcia,
        vykoná prvé spustenie vlákna na kontrolu priojenia zariadení.
        EN: A function that performs changes to the position and size of the window before the show() function is called,
        and executes the first run of the thread for checking device connections."""
        from ThreadCheckDevicesConnected import ThreadCheckDevicesConnected
        self.set_language()
        if ((self.thread_check_usb_devices is None or not self.thread_check_usb_devices.isRunning()) and
                self.ui.sens_type_comboBox.currentText() != ""):
            self.thread_check_usb_devices = ThreadCheckDevicesConnected(self.my_settings, self)
            self.thread_check_usb_devices.all_connected.connect(self.all_dev_connected_signal)
            self.thread_check_usb_devices.all_connected_strain.connect(self.all_dev_connected_signal_strain)
            self.thread_check_usb_devices.all_connected_temperature.connect(self.all_dev_connected_signal_temperature)
            self.thread_check_usb_devices.start()

        self.setFixedSize(int(self.width() * self.window_scale_delta),
                          int(self.height() * self.window_scale_delta))
        scale_app(self, self.window_scale_delta)
        self.window_scale_delta = 1
        self.check_devices_load_comboboxes_load_config_file()
        if self.operator:
            self.load_operators(self.operator)
        else:
            self.load_operators()

        QTimer.singleShot(0, lambda: center_on_screen(self))

    def showEvent(self, a0):
        """SK: Override pre funkciu showEvent, načíta nám class ktorá nám drží nastavenia pre daný typ senzora.
        EN: Override for the showEvent function, loads a class that holds settings for a specific type of sensor."""

        if self.is_accelerometer_enabled:
            from SensAcc.MySettingsWindow import MySettingsWindow as MySettingsWindowAcc
            if self.my_settings_window_acc is None:
                self.my_settings_window_acc = MySettingsWindowAcc
                self.settings_window_acc = self.my_settings_window_acc(True, self, self.my_settings)

        from MyGeneralPopUp import MyGeneralPopUp
        self.MyGeneralPopUp = MyGeneralPopUp
        self.splash.hide()
        if self.box_close_event is None:
            self.box_close_event = MyGeneralPopUp(parent=self, start_window=self,
                                                  left_btn=self.translations[self.lang]['close_event_yes'],
                                                  right_btn=self.translations[self.lang]['close_event_no'],
                                                  label=self.translations[self.lang]['close_event_b'], show_exit=True)
        if self.box_start_strain is None:
            self.box_start_strain = self.MyGeneralPopUp(parent=self, start_window=self,
                                                        left_btn=self.translations[self.lang]['close_event_yes'],
                                                        right_btn=self.translations[self.lang]['close_event_no'],
                                                        label=self.translations[self.lang]["start_strain_msg"],
                                                        label_text_size=10,
                                                        timer=3)
        if self.box_remove_op is None:
            self.box_remove_op = self.MyGeneralPopUp(parent=self, start_window=self,
                                                     left_btn=self.translations[self.lang]['close_event_yes'],
                                                     right_btn=self.translations[self.lang]['close_event_no'],
                                                     label="")

    def closeEvent(self, event):
        """SK. Override pre funkciu closeEvent, vytvorí pop-up window ktorý sa spýta či naozaj chceme ukončiť aplikáciu,
        vykoná všetky potrebné ukony pre správne vypnutie aplikácie.
        EN: Override for the closeEvent function, creates a pop-up window that asks if we really want to close
        the application, performs all necessary actions for the proper shutdown of the application."""
        self.box_close_event.show_modal()
        result = self.box_close_event.continue_code

        if result:
            self.hide()
            if self.thread_check_usb_devices:
                self.thread_check_usb_devices.termination = True
                self.thread_check_usb_devices.wait()
            sys.stdout.close()
            event.accept()
        else:
            event.ignore()

    def set_language(self):
        """SK: Funkcia ktorá nám nastaví jazyk pre všetok text na konkrétnom okne.
        EN: A function that sets the language for all text in a specific window."""
        file_path = "lang_pack.json"
        with open(file_path, 'r', encoding="utf-8") as f:
            self.translations = json_load(f)
        if self.calib_window is None:
            self.ui.sens_type_label.setText(self.translations[self.lang]["sens_type_label"])
            self.ui.status_opt_label.setText(self.translations[self.lang]["status_opt_label"]["init"])
            self.ui.status_label.setText(self.translations[self.lang]["status_label"])
            self.ui.status_ref_label.setText(self.translations[self.lang]["status_ref_label"]["init"])
            self.ui.opt_channel_label.setText(self.translations[self.lang]["opt_channel_label"])
            self.ui.status_gen_label.setText(self.translations[self.lang]["status_gen_label"]["init"])
            self.ui.start_app.setText(self.translations[self.lang]["start_app_a"])
            self.ui.open_settings_btn.setText(self.translations[self.lang]["open_settings_btn"])

            self.ui.sens_type_comboBox.setToolTip(self.translations[self.lang]["toolTip_sens_type_comboBox"])
            self.ui.opt_config_combobox.setToolTip(self.translations[self.lang]["toolTip_opt_config_combobox"])

            self.ui.status_opt_label.setToolTip(self.translations[self.lang]["toolTip_status"])
            self.ui.status_gen_label.setToolTip(self.translations[self.lang]["toolTip_status"])
            self.ui.status_ref_label.setToolTip(self.translations[self.lang]["toolTip_status"])

            self.ui.open_settings_btn.setToolTip(self.translations[self.lang]["toolTip_start_win_settings_btn"])
            self.ui.combobox_sel_operator.setToolTip(self.translations[self.lang]["toolTip_select_operator"])
            self.ui.btn_add_operator.setToolTip(self.translations[self.lang]["toolTip_add_remove_op"])
            self.ui.start_app.setToolTip(self.translations[self.lang]["toolTip_start_calibration_module"])

    def load_global_settings(self):
        """SK: Funkcia ktorá nám načíta všeobecné/globálne nastavenia.
        EN: A function that loads general/global settings."""
        with open("global_settings.yaml", 'r') as file:
            config = yaml_safe_load(file)
        self.version = config["version"]
        self.app_name = config["app_name"]
        self.app_name_abbre = config["name_abbre"]
        self.lang = config["language"]
        self.window_scale = config["windows_scale"]
        self.last_ref_calib = config["last_ref_calib_acc"]
        self.calib_treshold = int(config["treshold"])
        self.sens_type = config['last_sens_type']
        self.is_accelerometer_enabled = config['enabled_functionalities']['accelerometer']
        self.is_strain_enabled = config['enabled_functionalities']['strain']
        self.is_temperature_enabled = config['enabled_functionalities']['temperature']

    def save_sens_type(self):
        """SK: Funkcia na uloženie posledne použitého typu senzora pri spustení konfiguračného súboru.
        EN: A function to save the last used type of sensor when launching the configuration file."""
        try:
            with open("global_settings.yaml", 'r') as file:
                config = yaml_safe_load(file)
            config['last_sens_type'] = self.sens_type
            with open("global_settings.yaml", 'w') as file:
                yaml_safe_dump(config, file)
        except Exception as e:
            print(f"An error occurred while saving sens_type: {e}")

    def check_last_calib(self, get_bool=False):
        """SK: Funkcia ktorá nám skontroluje poslednú kalibráciu referenčného senzora, otvorí pop-up.
        EN: A function that checks the last calibration of the reference sensor and opens a pop-up."""

        def show_warning(last_date):
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(self.translations[self.lang]["last_calib_warn"])
            msg.setText(f"{self.translations[self.lang]['last_calib_warn_text']}{last_date}.")
            msg.addButton('OK', QMessageBox.AcceptRole)
            msg.exec_()

        if self.last_ref_calib:
            import datetime
            last_calib = None
            if isinstance(self.last_ref_calib, datetime.date):
                last_calib = QDate(self.last_ref_calib.year, self.last_ref_calib.month, self.last_ref_calib.day)

            elif isinstance(self.last_ref_calib, str):
                year, month, day = map(int, self.last_ref_calib.split('-'))
                last_calib = QDate(year, month, day)

            current_date = QDate.currentDate()
            if last_calib:
                days_apart = last_calib.daysTo(current_date)
                if days_apart > self.calib_treshold:
                    if not get_bool:
                        show_warning(last_calib.toString("yyyy-MM-dd"))
                        return
                    return True
                else:
                    return False

    def loading_gif(self):
        def centerLabel():
            # Center the label in the window
            windowWidth = self.width()
            windowHeight = self.height()
            labelWidth = self.loadingLabel.width()
            labelHeight = self.loadingLabel.height()

            newX = (windowWidth - labelWidth) // 2
            newY = (windowHeight - labelHeight) // 2

            self.loadingLabel.move(newX, newY)

        def resizeLabelToMovie(frameNumber):
            if frameNumber == 0:  # Adjust on the first frame
                movieSize = self.loadingLabel.movie().currentImage().size()
                self.loadingLabel.setFixedSize(movieSize)
                centerLabel()

        gifPath = os_path.join(self.my_settings.starting_folder, "images/loading2.gif")
        self.movie = QMovie(gifPath)
        if not self.movie.isValid():
            print("Failed to load GIF. Please check the file path and format.")
            return

        self.loadingLabel = QLabel(self)
        self.loadingLabel.setMovie(self.movie)
        self.loadingLabel.setAlignment(Qt.AlignCenter)
        self.loadingLabel.hide()
        self.movie.frameChanged.connect(resizeLabelToMovie)  # Adjust label size on the first frame

    def start_loading_gif(self):
        self.movie.start()
        self.loadingLabel.show()
