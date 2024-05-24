import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from nidaqmx.constants import WAIT_INFINITELY
from scipy.signal import resample

from Definitions import kill_sentinel, start_sentinel_modbus, save_error, linear_regression, get_params
from SensAcc.ThreadControlFuncGenStatements import ThreadControlFuncGenStatements
from MyStartUpWindow import MyStartUpWindow
from os import path as os_path, remove as os_remove, rename as os_rename, chdir as os_chdir
from time import time as time_time
from datetime import datetime, date
from SensAcc.SettingsParams import MySettings
from numpy import array as np_array, sum as np_sum, max as np_max, abs as np_abs, ndarray
from SensAcc.AC_functions_1FBG_v2 import resample_by_interpolation


class ThreadRefSensDataCollection(QThread):
    out_value = pyqtSignal(ndarray, str, int)
    emit_stop = pyqtSignal()

    def __init__(self, window: MyStartUpWindow, thcfgs: ThreadControlFuncGenStatements, s_n: str,
                 my_settings: MySettings, s_n_export: str):
        super().__init__()
        self.ref_file_path = None
        self.extracted_column2 = []
        self.extracted_column1 = []
        self.wl_slopes = None
        self.extracted_columns = None
        self.s_n_export = s_n_export
        self.opt_time = None
        self.out = None
        self.time_string = None
        self.current_date = None
        self.time_stamp = None
        self.task = None
        self.thcfgs = thcfgs
        self.my_settings = my_settings
        self.window = window
        self.s_n = s_n
        self.sensitivities_file = "sensitivities.csv"
        self.time_corrections_file = "time_corrections.csv"
        self.acc_calib = None
        self.num_of_samples_per_cycle = int(self.my_settings.ref_sample_rate / 10)
        self.i = 1

    def run(self):
        self.start_ref_sens_data_collection()

    def start_ref_sens_data_collection(self):
        def downsample_data(input_data, input_frequency, output_frequency):
            # Calculate the number of output samples needed
            num_output_samples = int(len(input_data) * (output_frequency / input_frequency))
            # Perform resampling
            output_data = resample(input_data, num_output_samples)
            return output_data

        # spustenie získavania vzoriek
        self.task.start()
        print("Start merania")
        current_time = datetime.now().time()
        self.time_string = current_time.strftime("%H:%M:%S.%f")
        start_time = time_time()

        # čítam získane vzorky
        # data = self.task.read(number_of_samples_per_channel=self.my_settings.ref_number_of_samples,
        #                       timeout=float(self.my_settings.generator_sweep_time+10))
        data = []
        try:
            while len(data) < self.my_settings.ref_number_of_samples and not self.thcfgs.get_emergency_stop():
                temp = self.task.read(number_of_samples_per_channel=self.num_of_samples_per_cycle,
                                      timeout=WAIT_INFINITELY)
                temp = temp
                if np_max(np_abs(temp)) >= self.my_settings.max_acceleration:
                    self.emit_stop.emit()
                    break
                data.extend(temp)
                self.out_value.emit(
                    resample_by_interpolation(temp, self.my_settings.ref_sample_rate,
                                              self.my_settings.opt_sampling_rate),
                    str(round(np_max(np_abs(temp)), 3)), self.i)
                # self.out_value.emit(downsample_data(temp, self.my_settings.ref_sample_rate, self.my_settings.opt_sampling_rate*2), str(round(np_max(np_abs(temp)), 3)), self.i)
                self.i += + 1

        except Exception as e:
            save_error(self.my_settings.starting_folder, e)
            print(e)
            self.thcfgs.set_emergency_stop(True)
            self.msleep(100)

        end_time = time_time()
        self.task.close()
        self.thcfgs.set_finished_measuring(True)
        kill_sentinel(True, False)
        if self.thcfgs.get_emergency_stop():
            return

        # stop
        # task.close()
        print("Stop merania")

        # dĺžka merania
        elapsed_time = (end_time - start_time) * 1000

        # ulozenie dát do txt súboru
        # self.save_data(data, elapsed_time)
        reversed_data = [-x for x in data]
        self.save_data(reversed_data, elapsed_time)
        # self.refData = data
        start_sentinel_modbus(self.my_settings.folder_sentinel_modbus_folder,
                              self.my_settings.subfolder_sentinel_project,
                              self.my_settings.opt_project, self.my_settings.opt_channels)
        self.thread_ref_sens_finished()

    def save_data(self, data, elapsed_time):

        today = date.today()
        self.current_date = today.strftime("%b-%d-%Y")

        file_path = os_path.join(self.my_settings.folder_ref_export, self.s_n + '.csv')
        file_path_raw = os_path.join(self.my_settings.folder_ref_export_raw, self.s_n + '.csv')
        with open(file_path, 'w') as file:
            file.write("# " + self.current_date + '\n')
            file.write("# " + self.time_string + '\n')
            file.write(
                "# Dĺžka merania : " + str(self.my_settings.ref_measure_time) + "s (" + str(
                    round(elapsed_time / 1000, 2)) +
                "s)" + '\n')
            file.write("# Vzorkovacia frekvencia : " + str(self.my_settings.ref_sample_rate) + '\n')
            file.write("# Počet vzoriek : " + str(self.my_settings.ref_number_of_samples) + '\n')
            file.write("# Merane zrýchlenie :" + '\n')
            for item in data:
                file.write(str(item) + '\n')

        with open(file_path_raw, 'w') as file:
            for item in data:
                file.write(str(item) + '\n')

        print("Zapisane do txt")

    def thread_ref_sens_finished(self):
        print("CALIBRATION --------------->")
        if not self.thcfgs.get_emergency_stop():
            self.make_opt_raw(4)
            time_format = "%H:%M:%S.%f"
            opt = datetime.strptime(self.opt_time, time_format)
            ref = datetime.strptime(self.time_string, time_format)
            time_difference = opt - ref
            time_difference = time_difference.total_seconds()

            file_path = os_path.join(self.my_settings.folder_main, self.sensitivities_file)
            if os_path.exists(file_path):
                os_remove(file_path)
            file_path = os_path.join(self.my_settings.folder_main, self.time_corrections_file)
            if os_path.exists(file_path):
                os_remove(file_path)
            if self.my_settings.opt_channels == 1:
                from SensAcc.AC_calibration_1FBG_v3 import ACCalib_1ch
                self.out = ACCalib_1ch(self.s_n, self.window.starting_folder, self.my_settings.folder_main,
                                       self.my_settings.folder_opt_export_raw,
                                       self.my_settings.folder_ref_export_raw,
                                       float(self.my_settings.calib_reference_sensitivity),
                                       int(self.my_settings.calib_gain_mark),
                                       int(self.my_settings.opt_sampling_rate),
                                       int(self.my_settings.ref_sample_rate),
                                       self.my_settings.calib_filter_data,
                                       int(self.my_settings.calib_downsample),
                                       int(self.my_settings.calib_do_spectrum),
                                       int(self.my_settings.calib_l_flatness),
                                       int(self.my_settings.calib_r_flatness),
                                       int(self.my_settings.calib_angle_set_freq),
                                       int(self.my_settings.calib_phase_mark)).start(False,
                                                                                     self.my_settings.calib_optical_sensitivity / 1000,
                                                                                     True, time_difference)
                self.acc_calib = self.out[0]
                self.out = ACCalib_1ch(self.s_n, self.window.starting_folder, self.my_settings.folder_main,
                                       self.my_settings.folder_opt_export_raw,
                                       self.my_settings.folder_ref_export_raw,
                                       float(self.my_settings.calib_reference_sensitivity),
                                       int(self.my_settings.calib_gain_mark),
                                       int(self.my_settings.opt_sampling_rate),
                                       int(self.my_settings.ref_sample_rate),
                                       self.my_settings.calib_filter_data,
                                       int(self.my_settings.calib_downsample),
                                       int(self.my_settings.calib_do_spectrum),
                                       int(self.my_settings.calib_l_flatness),
                                       int(self.my_settings.calib_r_flatness),
                                       int(self.my_settings.calib_angle_set_freq),
                                       int(self.my_settings.calib_phase_mark)).start(self.my_settings.calib_plot,
                                                                                     self.acc_calib[1] / 1000,
                                                                                     True,
                                                                                     time_difference + self.acc_calib[
                                                                                         8])
                self.acc_calib = self.out[0]
                # [0]>wavelength 1,[1]>sensitivity pm/g at gainMark,[2]>flatness_edge_l,
                # [3]>flatness_edge_r,[4]>sens. flatness,[5]>MAX SensAcc,[6]>MIN SensAcc,[7]>DIFF symmetry,[8]>TimeCorrection,
                # [9]>wavelength 2
            elif self.my_settings.opt_channels == 2:
                from SensAcc.AC_calibration_2FBG_edit import ACCalib_2ch

                self.out = ACCalib_2ch(self.s_n, self.window.starting_folder, self.my_settings.folder_main,
                                       self.my_settings.folder_opt_export_raw, self.my_settings.folder_ref_export_raw,
                                       float(self.my_settings.calib_reference_sensitivity),
                                       int(self.my_settings.calib_gain_mark),
                                       int(self.my_settings.opt_sampling_rate),
                                       int(self.my_settings.ref_sample_rate), self.my_settings.calib_filter_data,
                                       int(self.my_settings.calib_downsample),
                                       int(self.my_settings.calib_do_spectrum),
                                       int(self.my_settings.calib_l_flatness),
                                       int(self.my_settings.calib_r_flatness),
                                       int(self.my_settings.calib_angle_set_freq),
                                       int(self.my_settings.calib_phase_mark)).start(False,
                                                                                     self.my_settings.calib_optical_sensitivity / 1000,
                                                                                     True, 0)
                self.acc_calib = self.out[0]
                self.out = ACCalib_2ch(self.s_n, self.window.starting_folder, self.my_settings.folder_main,
                                       self.my_settings.folder_opt_export_raw, self.my_settings.folder_ref_export_raw,
                                       float(self.my_settings.calib_reference_sensitivity),
                                       int(self.my_settings.calib_gain_mark),
                                       int(self.my_settings.opt_sampling_rate),
                                       int(self.my_settings.ref_sample_rate), self.my_settings.calib_filter_data,
                                       int(self.my_settings.calib_downsample),
                                       int(self.my_settings.calib_do_spectrum),
                                       int(self.my_settings.calib_l_flatness),
                                       int(self.my_settings.calib_r_flatness),
                                       int(self.my_settings.calib_angle_set_freq),
                                       int(self.my_settings.calib_phase_mark)).start(self.my_settings.calib_plot,
                                                                                     self.acc_calib[1] / 1000,
                                                                                     True, self.acc_calib[8])
                self.acc_calib = self.out[0]

                # [3]>flatness_edge_r,[4]>sens. flatness,[5]>MAX SensAcc,[6]>MIN SensAcc,[7]>DIFF symmetry,[8]>TimeCorrection,
                # [9]>wavelength 2
            self.time_stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.lin_reg()
            self.save_calib_data()

    # def save_calib_data(self):
    #     file_path = os_path.join(self.my_settings.folder_calibration_export, self.s_n + '.csv')
    #     self.ref_file_path = file_path
    #     with open(file_path, 'w') as file:
    #         file.write("# S/N :" + '\n' + '\t\t' + str(self.s_n_export) + '\n')
    #         file.write("# Time stamp: " + '\n' + '\t\t' + self.time_stamp + '\n')
    #         if len(self.acc_calib) <= 9:
    #             file.write("# Channels : " + '\n' + '\t\t' "1" + '\n')
    #             file.write("# Center wavelength : " + '\n' + '\t\t' + str(self.acc_calib[0]) + '\n')
    #         else:
    #             file.write("# Channels : " + '\n' + '\t\t' "2 \n")
    #             file.write("# Center wavelengths : " + '\n' + '\t\t' + str(self.acc_calib[0]) + ';' +
    #                        str(self.acc_calib[9]) + '\n')
    #         file.write("# Sensitivity : " + '\n' + '\t\t' + str(self.acc_calib[1]) + " pm/g at " + str(
    #             self.my_settings.calib_gain_mark) + " Hz" + '\n')
    #         file.write("# Sensitivity flatness : " + '\n' + '\t\t' + str(self.acc_calib[4]) + " between " + str(
    #             self.acc_calib[2]) + " Hz and " + str(self.acc_calib[3]) + " Hz" + '\n')
    #         file.write("# Difference in symmetry : " + '\n' + '\t\t' + str(self.acc_calib[7]) + " % " + '\n')
    #
    #         text_to_append = str(self.wl_slopes[1])
    #         if self.my_settings.opt_channels >= 2:
    #             text_to_append += f", {self.wl_slopes[4]}"
    #         file.write("# Slope check : " + '\n' + '\t\t' + text_to_append + '\n')

    def save_calib_data(self):
        params, params2 = get_params(self.window.calib_window.s_n_export, self.my_settings.starting_folder)
        single_values = [
            ('SN', self.window.calib_window.s_n_export),
            ('TYPE', self.my_settings.opt_sensor_type),
            ('SENSOR', params2[1]),
            ('ON', params[0]),
            ('CUSTOMER', params[1]),
            ('CWL1', self.acc_calib[0]),
            ('CWL2', self.acc_calib[9] if len(self.acc_calib) >= 10 else None),
            ('Sensitivity', f"{self.acc_calib[1]} pm/g at {self.my_settings.calib_gain_mark}"),
            ('Sensitivity_flatness', f"{self.acc_calib[4]} between {self.acc_calib[2]} hz and {self.acc_calib[3]} hz"),
            ('Assymetry', f"{self.acc_calib[7]} %"),
            ('Slope', self.wl_slopes[1]),
            ('Time_tamp', self.time_stamp)
        ]

        file_path = os_path.join(self.my_settings.folder_calibration_export, self.s_n + '.csv')
        self.ref_file_path = file_path
        with open(file_path, 'w') as file:
            for label, value in single_values:
                file.write(f'{label}: {value}\n')

    def make_opt_raw(self, num_lines_to_skip):
        opt_sentinel_file_name = self.window.calib_window.autoCalib.opt_sentinel_file_name
        # print(str(self.my_settings.folder_opt_export) + "or\n" + str(self.opt_sentinel_file_name))
        file_path = os_path.join(self.my_settings.folder_opt_export, opt_sentinel_file_name)
        file_path_raw = os_path.join(self.my_settings.folder_opt_export_raw, self.s_n + '.csv')

        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith(": Start Time:"):
                    # Remove ': Start Time:' part and strip leading and trailing whitespaces
                    full_time_string = line.replace(": Start Time:", "").strip()

                    # Extract only the time from the full datetime string
                    try:
                        # Try to parse the full datetime string
                        datetime_obj = datetime.strptime(full_time_string, "%Y.%m.%d %H:%M:%S.%f")
                        self.opt_time = datetime_obj.strftime("%H:%M:%S.%f")
                        break
                    except ValueError:
                        pass

            file.seek(0)

            total_lines = sum(1 for line in file)

            # Reset the file pointer to the beginning
            file.seek(0)

            # Skip the specified number of lines
            for _ in range(num_lines_to_skip):
                next(file)

            # Initialize the extracted columns list
            extracted_columns = []

            # Determine the number of lines to read (excluding the last line)
            lines_to_read = total_lines - num_lines_to_skip - 1  # int(window.my_settings.opt_sampling_rate*0.15)
            if self.my_settings.opt_channels == 1:
                for _ in range(lines_to_read):
                    line = file.readline()
                    columns = line.strip().split(';')
                    extracted_columns.append(columns[2].lstrip())
                    self.extracted_column1.append(columns[2].lstrip())
            elif self.my_settings.opt_channels == 2:
                for _ in range(lines_to_read):
                    line = file.readline()
                    columns = line.strip().split(';')
                    extracted_columns.append(columns[2].lstrip() + ' ' + columns[3].lstrip())
                    self.extracted_column1.append(columns[2].lstrip())
                    self.extracted_column2.append(columns[3].lstrip())

            # for _ in range(lines_to_read):
            #     line = file.readline()
            #     columns = line.strip().split(';')
            #
            #     if self.my_settings.opt_channels == 1 and len(columns) >= 3:
            #         extracted_columns.append(columns[2].lstrip())
            #     elif self.my_settings.opt_channels == 2 and len(columns) >= 4:
            #         extracted_columns.append(columns[2].lstrip() + ' ' + columns[3].lstrip())

        with open(file_path_raw, 'w') as output_file:
            output_file.write('\n'.join(extracted_columns))

        os_chdir(self.my_settings.folder_opt_export)

        if os_path.exists(self.s_n + '.csv'):
            os_remove(self.s_n + '.csv')

        os_rename(opt_sentinel_file_name, self.s_n + '.csv')

    def lin_reg(self):
        wl1 = np.array(self.extracted_column1[800:len(self.extracted_column1) - 250], dtype=float) - self.acc_calib[
            0]  # dtype=float
        index_values = np_array(range(len(wl1)), dtype=float)  # Convert range to NumPy array
        slope1, intercept1 = linear_regression(index_values, wl1)
        check_wl1 = abs(slope1) * 10e6
        slope_samp1 = [slope1 * x + intercept1 for x in index_values]
        self.wl_slopes = [index_values, round(check_wl1, 3), slope_samp1, wl1]

        if self.my_settings.opt_channels == 2:
            wl2 = np.array(self.extracted_column2[800:len(self.extracted_column1) - 250], dtype=float) - self.acc_calib[
                9]
            # Linear regression for the second column against index
            slope2, intercept2 = linear_regression(index_values, wl2)
            check_wl2 = abs(slope2) * 10e6
            slope_samp2 = [slope2 * x + intercept2 for x in index_values]
            self.wl_slopes.extend([round(check_wl2, 3), slope_samp2, wl2])
