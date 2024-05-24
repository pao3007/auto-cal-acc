import ipaddress

import pythoncom
from PyQt5.QtCore import QThread, pyqtSignal

from Definitions import check_usb, check_function_gen_connected
from nidaqmx import Task as nidaqmx_Task
from MyStartUpWindow import MyStartUpWindow


def check_ip(ip):
    if ip is not None and ip not in ('None', 'none'):
        return ipaddress.IPv4Address(ip)
    else:
        return False


class ThreadCheckDevicesConnected(QThread):
    all_connected = pyqtSignal(bool, bool, bool, bool, bool, bool)
    all_connected_strain = pyqtSignal(bool, bool, bool)
    all_connected_temperature = pyqtSignal(bool, bool, bool)
    opt_connected = pyqtSignal(bool)

    def __init__(self, my_settings, my_start_window: MyStartUpWindow, block=False):
        super().__init__()
        self.gen_error = False
        self.gen = False
        self.bad_ref = False
        self.ref = False
        self.opt = False
        self.probe = None
        self.chmbr = None
        self.temp_probe = None
        self.chamber = None
        self.task_sin = None
        self.termination = False
        self._my_settings = my_settings
        self.block = block
        self.my_start_window = my_start_window
        self.i = 9

    def run(self):
        print("START CHECK")
        pythoncom.CoInitialize()
        while not self.termination:
            if self.my_start_window.sens_type == "Accelerometer":
                self.check_acc()
            QThread.msleep(50)
        print("END CHECK")

    def check_acc(self):
        if not self.block:
            self.i += 1
            if self.i % 10:
                self.opt, self.ref = check_usb(self.my_start_window.opt_dev_vendor, self.my_start_window.ref_dev_vendor)
                if self.ref:
                    try:
                        self.task_sin = nidaqmx_Task(new_task_name='FirstCheckRef')
                        self.task_sin.ai_channels.add_ai_accel_chan(self._my_settings.ref_device_name + '/' +
                                                                    self._my_settings.ref_channel)
                        self.bad_ref = False
                    except Exception as e:
                        print(e)
                        self.bad_ref = True
                    finally:
                        self.task_sin.close()
                try:
                    self.gen, self.gen_error = check_function_gen_connected(self._my_settings.generator_id, True)
                    if self.my_start_window.sens_type == "Accelerometer":
                        self.all_connected.emit(self.opt, self.ref, self.gen, self.gen_error, True, self.bad_ref)
                except Exception:
                    pass
                self.i = 0
            else:
                if self.my_start_window.sens_type == "Accelerometer":
                    self.all_connected.emit(self.opt, self.ref, self.gen, self.gen_error, False, self.bad_ref)
        else:
            try:
                self.opt, _ = check_usb(self.my_start_window.opt_dev_vendor, self.my_start_window.ref_dev_vendor)
                self.opt_connected.emit(self.opt)
            except Exception as e:
                print(e)

    @property
    def my_settings(self):
        return self._my_settings

    @my_settings.setter
    def my_settings(self, value):
        self._my_settings = value

