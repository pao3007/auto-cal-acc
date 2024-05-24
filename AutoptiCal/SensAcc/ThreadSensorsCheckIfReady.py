import psutil
from PyQt5.QtCore import QThread, pyqtSignal
from SensAcc.ThreadControlFuncGenStatements import ThreadControlFuncGenStatements
from Definitions import start_sentinel_modbus
from os import kill


def is_process_running(pid):
    try:
        process = psutil.Process(pid)
        return True
    except psutil.NoSuchProcess:
        return False


class ThreadSensorsCheckIfReady(QThread):
    check_ready = pyqtSignal(bool)

    def __init__(self, thcfgs: ThreadControlFuncGenStatements, my_settings, auto_calib=None):
        super().__init__()
        self.real_pid = None
        self.termination = False
        self.auto_calib = auto_calib
        self.thcfgs = thcfgs
        self.my_settings = my_settings
        self.load_real_pid = False
        self.skip = False

    def run(self):
        print("STARTING SENS CHECK THREAD LOOP")
        i = 4
        while not self.termination and not self.thcfgs.get_start_measuring():
            while (not self.termination and self.auto_calib.thread_check_sin_opt.isRunning() and
                   self.auto_calib.thread_check_sin_ref.isRunning()):
                i += 1
                if not (i % 5):
                    self.check_ready.emit(True)
                    # i = 0
                else:
                    self.check_ready.emit(False)
                if not (i % 20):
                    if (self.auto_calib.thread_check_sin_opt.isRunning() and
                            self.auto_calib.thread_check_sin_ref.isRunning()):
                        self.start_process()
                    i = 0
                QThread.msleep(50)
                # print("CHECKING SENSORS")
            QThread.msleep(250)
        print("END SENS CHECKING")

    def start_process(self):
        pid = self.auto_calib.calib_window.pid
        if pid is not None:
            if self.real_pid is not None:
                if not is_process_running(self.real_pid) and not self.termination:
                    if self.skip:
                        print("START MODBUS SENTINEL CLOSED")
                        start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                                              self.my_settings.subfolder_sentinel_project,
                                              self.my_settings.opt_project, self.my_settings.opt_channels)
                        self.auto_calib.calib_window.pid = None
                        self.load_real_pid = False
                        self.real_pid = None
                        self.skip = False
                    self.skip = True
            elif not self.load_real_pid:
                self.load_real_pid = True
                return
            elif self.real_pid is None:
                print("FIND REAL PID")
                for process in psutil.process_iter(['pid', 'name']):
                    if process.info['name'] == "ClientApp_Dyn.exe":
                        self.real_pid = process.info['pid']
