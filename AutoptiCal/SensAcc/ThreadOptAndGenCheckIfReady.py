import numpy as np
import pythoncom

from PyQt5.QtCore import QThread, pyqtSignal
from SensAcc.ThreadSentinelCheckNewFile import ThreadSentinelCheckNewFile
from Definitions import check_function_gen_connected, check_usb, start_modbus, kill_sentinel, start_sentinel_d
from MyStartUpWindow import MyStartUpWindow
from SensAcc.SettingsParams import MySettings
from SensAcc.ThreadControlFuncGenStatements import ThreadControlFuncGenStatements


class ThreadOptAndGenCheckIfReady(QThread):
    check_ready_opt = pyqtSignal(int)
    check_ready_gen = pyqtSignal(bool)
    check_gen_error = pyqtSignal(bool)
    out_value = pyqtSignal(str)
    from pyModbusTCP.client import ModbusClient
    from SensAcc.RollingAverager import RollingAverager

    def __init__(self, server_ip, server_port, unit_id, address, number_of_samples, threshold, window: MyStartUpWindow,
                 my_settings: MySettings, thcfgs: ThreadControlFuncGenStatements):
        super().__init__()
        self.my_settings = my_settings
        self.thcfgs = thcfgs
        self.average2 = 0
        self.client = None
        self.thread_check_new_file = None
        self.server_ip = server_ip
        self.server_port = server_port
        self.unit_id = unit_id
        self.address = address
        self.number_of_samples = number_of_samples
        self.threshold = threshold
        self.termination = False
        self.restart = False
        self.disconnect_count = 0
        self.do_action = False
        self.samples2 = np.empty(self.number_of_samples)
        self.samples1 = np.empty(self.number_of_samples)
        self.first_start = True
        self.averager1 = self.RollingAverager(3)
        self.averager2 = self.RollingAverager(3)
        self.average1 = 0
        self.window = window
        self.check = 0
        self.prevEmit = 0

    def run(self):
        self.start_opt_check()

    def start_opt_check(self):
        self.client = self.ModbusClient(host=self.server_ip, port=self.server_port, unit_id=self.unit_id)
        self.client.open()
        pythoncom.CoInitialize()
        print("START OPT CHECK")
        while not self.termination:
            # print("CHECKING   OPT")
            try:
                if self.window.calib_window.measure:
                    gen, _ = check_function_gen_connected(self.my_settings.generator_id)
                else:
                    gen, gen_error = check_function_gen_connected(self.my_settings.generator_id, True)
                    self.check_gen_error.emit(gen_error)
                self.check_ready_gen.emit(gen)
                self.check_ready_opt.emit(self.check_if_ready())
            except Exception as e:
                print("OPT: " + str(e))

    def check_if_ready(self):
        i = -1
        opt, _ = check_usb(self.window.opt_dev_vendor, self.window.ref_dev_vendor)
        if opt:
            self.do_action = True
        else:
            self.do_action = False

        if self.do_action:
            self.disconnect_count = 0
            while i < self.number_of_samples - 1 and not self.termination:
                regs1 = self.client.read_input_registers(self.address, 2)
                if regs1 is not None:
                    i += 1
                    sample = regs1[0] + regs1[1] / 1000
                    self.samples1[i] = sample
                    # print(sample)
                if self.my_settings.opt_channels == 2:
                    regs2 = self.client.read_input_registers(self.address + 2, 2)
                    if regs2 is not None:
                        sample = regs2[0] + regs2[1] / 1000
                        self.samples2[i] = sample
                        # print(sample)
                QThread.msleep(1)
            if self.termination:
                print("END OPT prevEmit")
                return self.prevEmit

            max_g_1 = np.max(self.samples1)
            mean_1 = np.mean(self.samples1)
            if not self.thcfgs.get_start_sens_test():
                out = str(round(mean_1, 3))
            else:
                out = str(round(max_g_1, 3))
            out += " nm\n"
            if self.my_settings.opt_channels == 2:
                max_g_2 = np.max(self.samples2)
                mean_2 = np.mean(self.samples2)
                if not self.thcfgs.get_start_sens_test():
                    out += str(round(mean_2, 3))
                else:
                    out += str(round(max_g_2, 3))
                out += " nm"

            self.out_value.emit(out)

            if not self.first_start:
                if not self.thcfgs.get_start_sens_test():
                    self.average1 = self.averager1.update(mean_1)
                    if self.my_settings.opt_channels == 1:
                        self.prevEmit = int(not (np.any(self.samples1 == 0.0)))
                        return self.prevEmit
                    elif self.my_settings.opt_channels == 2:
                        self.average2 = self.averager2.update(mean_2)
                        dev = (np.abs(self.average1 - max_g_1) + np.abs(self.average2 - max_g_2)) / 2
                        if np.any(self.samples1 == 0.0) and np.any(self.samples2 == 0.0):
                            self.prevEmit = 0
                        elif np.any(self.samples1 == 0.0) or np.any(self.samples2 == 0.0):
                            self.prevEmit = 10
                        elif dev < 0.075:
                            self.prevEmit = 1
                        else:
                            self.prevEmit = 11

                        return self.prevEmit
                else:
                    if self.my_settings.opt_channels == 1:
                        dev = np.abs(self.average1 - max_g_1)
                        # print(dev)
                        if not np.any(self.samples1 == 0.0):
                            if dev > 0.001:
                                self.check += 1
                                if self.check >= 2:
                                    self.check = 0
                                    self.prevEmit = 5
                            else:
                                self.check -= 1
                                if self.check >= -2:
                                    self.check = 0
                                self.prevEmit = 4
                        else:
                            self.prevEmit = 0
                        return self.prevEmit
                    elif self.my_settings.opt_channels == 2:
                        dev = (np.abs(self.average1 - max_g_1) + np.abs(self.average2 - max_g_2)) / 2
                        print("dev : " + str(dev))
                        if ((not (np.any(self.samples1 == 0.0)) and int(not (np.any(self.samples2 == 0.0)))) and
                                (dev >= 0.1)):  # self.average1 - 0.075 > max_g_1 or self.average1 + 0.075 < max_g_1
                            self.check += 1
                            if self.check >= 2:
                                self.check = 0
                                self.prevEmit = 5
                                return self.prevEmit
                        else:
                            self.check = 0
                            self.prevEmit = 4
                            return self.prevEmit
            self.first_start = False
        else:
            self.check_ready_opt.emit(3)
            print("OPT. DEVICE IS DISCONNECTED \n")
            opt, _ = check_usb(self.window.opt_dev_vendor, self.window.ref_dev_vendor)
            while not opt:
                opt, _ = check_usb(self.window.opt_dev_vendor, self.window.ref_dev_vendor)
            self.restart_sentinel()
            self.client.open()

    def restart_sentinel(self):
        print("RESTART SENTINEL")
        kill_sentinel(True, True)
        QThread.msleep(100)
        start_sentinel_d(self.my_settings.opt_project, self.my_settings.folder_sentinel_D_folder, self.my_settings.subfolder_sentinel_project)
        self.thread_check_new_file = ThreadSentinelCheckNewFile(self.my_settings.folder_opt_export)
        self.thread_check_new_file.finished.connect(self.thread_check_new_file_finished)
        self.thread_check_new_file.start()
        self.thread_check_new_file.wait()

    def thread_check_new_file_finished(self):
        start_modbus(self.my_settings.folder_sentinel_modbus_folder,
                     self.my_settings.subfolder_sentinel_project,
                     self.my_settings.opt_project, self.my_settings.folder_opt_export,
                     self.my_settings.opt_channels,
                     self.thread_check_new_file.opt_sentinel_file_name)
