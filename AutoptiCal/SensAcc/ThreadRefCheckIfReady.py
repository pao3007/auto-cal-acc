import numpy as np
import psutil
from PyQt5.QtCore import QThread, pyqtSignal
from nidaqmx import Task as nidaqmx_Task
from nidaqmx.constants import AcquisitionType, WAIT_INFINITELY
from SensAcc.ThreadControlFuncGenStatements import ThreadControlFuncGenStatements
from MyStartUpWindow import MyStartUpWindow
from Definitions import dominant_frequency, start_sentinel_modbus
from SensAcc.SettingsParams import MySettings


class ThreadRefCheckIfReady(QThread):
    finished_signal = pyqtSignal()
    check_ready = pyqtSignal(int)
    out_value = pyqtSignal(str)
    emit_stop = pyqtSignal()
    from SensAcc.RollingAverager import RollingAverager

    def __init__(self, thcfgs: ThreadControlFuncGenStatements, window: MyStartUpWindow, my_settings: MySettings):
        super().__init__()
        self.task_sin = None
        self.my_settings = my_settings
        self.termination = False
        self.disconnected = False
        self.sample_rate = 12800
        self.data = []
        self.last_peak = 0
        self.first_start = True
        self.noise = [0] * 12
        self.avg_noise = 0
        self.averager = self.RollingAverager(10)
        self.average = 0
        self.thcfgs = thcfgs
        self.window = window

    def run(self):
        number_of_samples_per_channel = int(12800 / 6)
        print("Start ref sens sinus check")
        # nazov zariadenia/channel, min/max value -> očakávané hodnoty v tomto rozmedzí
        while not self.termination:
            # print("REF 1")
            try:
                g = 9.80665
                self.task_sin = nidaqmx_Task(new_task_name='RefCheck')
                self.task_sin.ai_channels.add_ai_accel_chan(self.my_settings.ref_device_name + '/' +
                                                            self.my_settings.ref_channel,
                                                            sensitivity=self.my_settings.calib_reference_sensitivity * g)
                self.task_sin.timing.cfg_samp_clk_timing(self.sample_rate,
                                                         sample_mode=AcquisitionType.CONTINUOUS)

                timeout = 0
                # 2 varianta
                while not self.termination:
                    # print("REF 2")
                    # print("CHECKING REF")
                    data = self.task_sin.read(number_of_samples_per_channel=number_of_samples_per_channel,
                                              timeout=WAIT_INFINITELY)
                    data = data
                    max_g = np.max(np.abs(data))
                    if self.thcfgs.enable_safety_check and (max_g >= self.my_settings.max_acceleration):
                        print("EMERGENCY STOP REF CHECK")
                        self.emit_stop.emit()
                    # ready, amp = data_contains_sinus(data, 0.01)
                    peak = round(dominant_frequency(data, self.sample_rate), 2)
                    # print(str(peak) + " - " + str(max_g))
                    if not self.first_start:
                        if not self.thcfgs.get_start_sens_test():  # kontrola či je pripojený senzor
                            self.check_ready.emit(1)
                            timeout = 0
                            # self.average = self.averager.update(max_g)
                        else:
                            if ((self.my_settings.generator_sweep_stop_freq / 2 - (
                                    self.my_settings.generator_sweep_stop_freq / 2) / 20) <= peak <=
                                (self.my_settings.generator_sweep_stop_freq / 2 + (
                                        self.my_settings.generator_sweep_stop_freq / 2) / 20)) and peak == \
                                    self.last_peak and (0.1 < max_g):
                                # print("True")
                                timeout += 1
                                if timeout >= 10:
                                    self.check_ready.emit(2)  # (2) je ok
                                    if timeout >= 10:
                                        timeout = 10
                            else:
                                if timeout > 0:
                                    timeout = 0
                                timeout -= 1
                                if timeout <= (-5):
                                    self.check_ready.emit(6)
                                    if timeout <= (-5):
                                        timeout = -5
                        self.last_peak = peak
                    self.first_start = False
                    if not self.thcfgs.get_start_sens_test():
                        out = str(np.round(np.mean(data), 5))
                    else:
                        out = str(np.round(max_g, 5))
                    out += " g"
                    self.out_value.emit(out)
                break
            except Exception as e:
                print("REF CHECK:" + str(e))
                self.check_ready.emit(3)
                try:
                    self.task_sin.close()
                except:
                    pass

            QThread.msleep(333)

