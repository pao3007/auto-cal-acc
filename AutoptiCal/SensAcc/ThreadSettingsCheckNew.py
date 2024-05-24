from PyQt5.QtCore import QThread, pyqtSignal
from nidaqmx import system as nidaqmx_system
from pyvisa import ResourceManager as pyvisa_ResourceManager
from Definitions import return_all_configs
from SensAcc.SettingsParams import MySettings


class ThreadSettingsCheckNew(QThread):
    status = pyqtSignal()

    def __init__(self, nidaq_devices, resources, all_configs, my_settings: MySettings):
        super().__init__()
        self.termination = None
        self.nidaq_devices = nidaq_devices
        self.resources = resources
        self.all_configs = all_configs
        self.my_settings = my_settings

    def run(self):
        while True:
            self.msleep(1000)
            try:
                system = nidaqmx_system.System.local()
                current_devices = system.devices.device_names

                rm = pyvisa_ResourceManager(r"C:\Windows\System32\visa64.dll")
                current_resources = rm.list_resources()

                current_configs = return_all_configs(self.my_settings.opt_sensor_type, self.my_settings.subfolderConfig_path)
                if not (set(self.nidaq_devices) == set(current_devices)) or \
                        not (set(self.resources) == set(current_resources)) or \
                        not (set(self.all_configs) == set(current_configs)):
                    print("True")
                    print(str(self.nidaq_devices) + " + " + str(current_devices))
                    print(str(self.resources) + " + " + str(current_resources))
                    print(str(self.all_configs) + " + " + str(current_configs))
                    self.status.emit()
            except Exception as e:
                print("ThreadSettingsCheckNew:", e)
