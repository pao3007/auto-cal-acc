from PyQt5.QtCore import QThread, pyqtSignal
from pyvisa import ResourceManager as pyvisa_ResourceManager, errors as visa_errors
from SensAcc.ThreadControlFuncGenStatements import ThreadControlFuncGenStatements
from Definitions import kill_sentinel, start_sentinel_d
from MyStartUpWindow import MyStartUpWindow


class ThreadControlFuncGen(QThread):
    connected_status = pyqtSignal(bool)
    step_status = pyqtSignal(str)
    set_btn = pyqtSignal()

    def __init__(self, generator_id: str, generator_sweep_time: int, generator_sweep_start_freq: int,
                 generator_sweep_stop_freq: int, generator_sweep_type: str, generator_max_mvpp: int,
                 thcfgs: ThreadControlFuncGenStatements, opt_project: str, opt_channels: int, sentinel_s_folder: str,
                 start_win: MyStartUpWindow, my_settings):
        super().__init__()
        self.generator_id = generator_id
        self.generator_sweep_time = generator_sweep_time
        self.generator_sweep_start_freq = generator_sweep_start_freq
        self.generator_sweep_stop_freq = generator_sweep_stop_freq
        self.generator_sweep_type = generator_sweep_type
        self.generator_max_vpp = generator_max_mvpp / 1000
        self.opt_project = opt_project
        self.thcfgs = thcfgs
        self.opt_channels = opt_channels
        self.generator_check = True
        self.sentinel_s_folder = sentinel_s_folder
        self.rm = None
        self.instrument = None
        self.start_win = start_win
        self.my_settings = my_settings

    def run(self):
        self.run_gen()
        try:
            print("TURNING OFF CONTROL GEN")
            try:
                self.instrument_write('OUTPut1:STATe OFF')
            except:
                self.msleep(2000)
                self.instrument_write('OUTPut1:STATe OFF')
            self.rm.close()
        except Exception as e:
            print(e)

    def first_control(self):
        self.rm = pyvisa_ResourceManager(r"C:\Windows\System32\visa64.dll")
        self.instrument = self.rm.open_resource(self.generator_id)
        self.msleep(250)
        self.instrument_write('OUTPut1:STATe OFF')
        self.instrument_write('SOURce1:FUNCtion SINusoid')
        self.instrument_write('SOURce1:FREQuency:MODE FIXed')
        self.instrument_write('SOURce1:FREQuency ' + str(self.generator_sweep_stop_freq / 2))
        self.instrument_write('SOURce1:VOLTage:LIMit:HIGH +' + str(self.generator_max_vpp))
        self.instrument_write('SOURce1:VOLTage:LIMit:STATe 0')
        self.instrument_write('SOURce1:VOLTage ' + str(self.generator_max_vpp / 5))
        self.instrument_write('TRIGger1:SOURce IMMediate')
        self.thcfgs.set_start_sens_test(True)
        self.instrument_write('OUTPut1:STATe ON')

    def second_control(self):
        self.instrument_write('SOURce1:FREQuency:MODE SWEep')
        self.instrument_write('SOURce1:FUNCtion ' + str(self.generator_sweep_type))
        self.instrument_write('SOURce1:FREQuency:STARt ' + str(self.generator_sweep_start_freq))
        self.instrument_write('SOURce1:FREQuency:STOP ' + str(self.generator_sweep_stop_freq))
        self.instrument_write('SOURce1:VOLTage ' + str(self.generator_max_vpp))
        self.instrument_write('SOURce1:SWEep:TIME ' + str(5))
        self.instrument_write('TRIGger1:SOURce BUS')
        self.instrument_write('SOURce1:SWEep:SPACing LINear')  # LINear
        self.instrument_write('OUTPut1:STATe ON')
        self.instrument_write('TRIGger1')

    def run_gen(self):
        self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_start_sens_test"])
        self.msleep(200)
        try:
            try:
                self.first_control()
            except:
                self.msleep(2000)
                self.first_control()
            i = 0
            while not self.thcfgs.get_end_sens_test():
                self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_testing"])
                if self.thcfgs.get_emergency_stop() or not self.generator_check:
                    self.thcfgs.set_emergency_stop(True)
                    return
                self.msleep(40)
                i += 1
                if i >= 5:
                    self.set_btn.emit()
            self.instrument_write('OUTPut1:STATe OFF')
            self.thcfgs.enable_safety_check = True
            i = 0
            while i < 10:
                self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_sweep_test_start"])
                i += 1
                if self.thcfgs.get_emergency_stop() or not self.generator_check:
                    self.thcfgs.set_emergency_stop(True)
                    return
                self.msleep(50)
            try:
                self.second_control()
            except:
                self.msleep(2000)
                self.second_control()
            i = 0
            while i < 100:
                self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_sweep_test"])
                i += 1
                if self.thcfgs.get_emergency_stop() or not self.generator_check:
                    self.thcfgs.set_emergency_stop(True)
                    return
                self.msleep(50)
            self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_sentinel_wait"])
            self.start_win.calib_window.autoCalib.thread_check_sin_ref.termination = True
            self.start_win.calib_window.autoCalib.thread_check_sin_opt.termination = True
            kill_sentinel(False, True)
            start_sentinel_d(self.opt_project, self.sentinel_s_folder, self.my_settings.subfolder_sentinel_project)
            # self.thcfgs.set_sentinel_started(True)
            i = 0
            while i < 10:
                i += 1
                if self.thcfgs.get_emergency_stop() or not self.generator_check:
                    self.thcfgs.set_emergency_stop(True)
                    return
                self.msleep(50)
            try:
                self.instrument_write('OUTPut1:STATe OFF')
                self.instrument_write('SOURce1:SWEep:TIME ' + str(self.generator_sweep_time))
            except:
                self.instrument_write('OUTPut1:STATe OFF')
                self.msleep(2000)
                self.instrument_write('OUTPut1:STATe OFF')
                self.instrument_write('SOURce1:SWEep:TIME ' + str(self.generator_sweep_time))

            while not self.thcfgs.get_start_measuring():
                self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_sentinel_wait"])
                if self.thcfgs.get_emergency_stop():
                    self.thcfgs.set_emergency_stop(True)
                    return
                self.msleep(50)

            i = 0

            while i < 10:
                self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_start_measure"])
                if self.thcfgs.get_emergency_stop():
                    self.thcfgs.set_emergency_stop(True)
                    return
                self.msleep(50)
                i += 1
            try:
                self.instrument_write('OUTPut1:STATe ON')
            except:
                self.msleep(2000)
                self.instrument_write('OUTPut1:STATe ON')
            i = 0
            while i < 20:
                self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_start_measure"])
                if self.thcfgs.get_emergency_stop():
                    self.thcfgs.set_emergency_stop(True)
                    return
                self.msleep(50)
                i += 1
            try:
                self.instrument_write('TRIGger1')
            except:
                self.msleep(2000)
                self.instrument_write('TRIGger1')

            while not self.thcfgs.get_finished_measuring():
                self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_response_sweep"])
                if self.thcfgs.get_emergency_stop():
                    return
                self.msleep(50)
            self.step_status.emit(self.start_win.translations[self.start_win.lang]["out_brow_calib"])
        except visa_errors.VisaIOError:
            self.thcfgs.set_emergency_stop(True)
            self.step_status.emit(self.start_win.translations[self.start_win.lang]["gen_visa_error"])
        except Exception as e:
            self.thcfgs.set_emergency_stop(True)
            self.step_status.emit("Error occured : \n" + str(e))

    def instrument_write(self, command):
        self.instrument.write(command)
        self.msleep(50)