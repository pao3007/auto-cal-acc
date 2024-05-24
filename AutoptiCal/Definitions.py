from math import sqrt as math_sqrt
import time
from datetime import datetime
from configparser import ConfigParser
from codecs import open as codecs_open
import win32api
import pythoncom
import requests
import serial.tools.list_ports
import psutil
import win32com
import win32con
import win32gui
from PyQt5.QtGui import QValidator
from wmi import WMI as wmi_WMI
from PyQt5.QtCore import QThread, QFileInfo, QSize, QTimer, pyqtSignal, Qt

import numpy as np
from numpy import sum as np_sum
from PyQt5.QtWidgets import QApplication, QWidget, QDialog, QLineEdit, QVBoxLayout, QDialogButtonBox, QTextBrowser, \
    QPushButton, QLabel, QDesktopWidget
from os import (chdir as os_chdir, system as os_system, path as os_path, remove as os_remove, makedirs as os_makedirs,
                listdir as os_listdir, chmod as os_chmod)
from pyvisa import ResourceManager as pyvisa_ResourceManager
from DatabaseCom import DatabaseCom
from xml.etree.ElementTree import parse as ET_parse
from yaml import safe_load as yaml_safe_load, safe_dump as yaml_safe_dump
from re import search as re_search, sub as re_sub, escape as re_escape
from shutil import copy as shutil_copy
from platform import system as platform_system
from csv import writer as csv_writer
from subprocess import run as subprocess_run
from json import loads as json_loads
from glob import glob
from time import sleep


def fetch_wavelengths_peak_logger(fetch_wl, channel="1.2", timeout_short=2):
    try:
        api_url = "http://localhost:43122/swagger/index.html" if not fetch_wl else f"http://localhost:43122/peaks?channel={channel}&enableFos4x=false"
        timeout = timeout_short
        response = requests.get(api_url, timeout=timeout)
        if not fetch_wl:
            return response.status_code, ([-1], -1, -1)
        elif response.status_code == 404:
            return response.status_code, ([-1], -1, -1)
        elif response.status_code == 200:
            data = json_loads(response.text)

            wavelengths = [entry['wavelength'] for entry in data if 'wavelength' in entry]
            asy = [entry['asymmetry'] for entry in data if 'asymmetry' in entry]
            width = [entry['width'] for entry in data if 'width' in entry]
            try:
                if float(asy[0]) > 1.5 or float(asy[0]) == -1.0 or float(width[0]) > 1.0:
                    return response.status_code, ([-1], -1, -1)
            except:
                return response.status_code, ([-1], -1, -1)

            return response.status_code, (wavelengths, asy, width)
        else:
            return response.status_code, ([-1], -1, -1)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return -1, ([0], -1, -1)


def channel_to_row_index(channel_name):
    major, minor = channel_name.split('.')
    major = int(major) - 1  # Subtract 1 to align with 0-based indexing
    minor = int(minor) - 1  # Subtract 1 since '1.1' should map to the first row (index 0)
    row_index = major * 4 + minor  # Adjust this calculation based on your actual row grouping
    return row_index


def compare_and_adjust_peaks(_paired_sequence, all_wls):
    for channel, paired_peaks in _paired_sequence.items():
        if channel in all_wls:
            wl_list = all_wls[channel]
            paired_peak_values = [peak for _, peak in paired_peaks]
            for idx, wl in enumerate(paired_peak_values):
                try:
                    if wl is not None:
                        if not abs(wl - wl_list[idx]) <= 0.5:
                            is_inside = False
                            for check in paired_peak_values:
                                if check is not None:
                                    if abs(wl_list[idx] - check) <= 0.5:
                                        is_inside = True
                            if is_inside:
                                wl_list.insert(idx, None)
                            else:
                                wl_list[idx] = None
                    else:
                        is_inside = False
                        for check in paired_peak_values:
                            if check is not None:
                                if abs(wl_list[idx] - check) <= 0.5:
                                    is_inside = True
                        if is_inside:
                            wl_list.insert(idx, None)
                        else:
                            wl_list[idx] = None
                except IndexError:
                    wl_list.append(None)
            if len(wl_list) != len(paired_peak_values):
                all_wls[channel] = [-2, "UNEXPECTED SENSOR"]
            else:
                all_wls[channel] = wl_list
    return all_wls


def format_serial_number(serial, div):
    match = re_search(r"(\d+)(\D+)(\d+)", serial)
    if match:
        part1 = match.group(1)
        part3 = int(match.group(3))  # Convert to integer to remove leading zeros

        formatted_serial = f"{part1}{div}{part3:04}"  # Format the integer with leading zeros to a width of 4
        return formatted_serial
    else:
        return serial


def sort_dict_by_keys(d):
    # Sort the dictionary by its keys, which are assumed to be float-like strings
    return {k: v for k, v in sorted(d.items(), key=lambda item: float(item[0]) if isinstance(item[0], str) else float('inf'))}


def fetch_all_connected_wavelengths(fetch_wl, timeout_short=2):
    try:
        api_url = "http://localhost:43122/swagger/index.html" if not fetch_wl else f"http://localhost:43122/peaks?"
        timeout = timeout_short
        response = requests.get(api_url, timeout=timeout)
        if not fetch_wl:
            return response.status_code, []
        elif response.status_code == 404:
            return response.status_code, []
        elif response.status_code == 200:
            data = json_loads(response.text)
            return response.status_code, data
        else:
            return response.status_code, []
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return -1, []


def contains_only_false(array):
    return all(not x for x in array)


def sort_channel_data(dictionary):
    for channel_key, item in dictionary.items():
        # Sort the list for the specified channel key based on the minimum value in the second item of each sublist
        dictionary[channel_key] = sorted(
            dictionary[channel_key],
            key=lambda x: min(x[1])  # Sorting by the minimum value in the second nested list
        )
        return True  # Sorting successful
    else:
        return False  # Channel key not found


def remove_item_from_nested_list(dictionary, key, identifier):
    # Check if the key exists in the dictionary
    if key in dictionary:
        # Iterate through the list at dictionary[key]
        # Use a list comprehension to filter out the item with the specified identifier
        dictionary[key] = [item for item in dictionary[key] if item[0] != identifier]
        return True  # Indicate success
    else:
        return False  # Key not found

def start_peaklogger(start_folder, peaklogger_folder=r"C:PeakLogger\oapp"):  # ! vybrat path to .exe a project

    def wait_for_window_title(title, timeout=30):
        end_time = time.time() + timeout
        while time.time() < end_time:
            hwnd = win32gui.FindWindow(None, title)
            if hwnd != 0:
                return hwnd
            time.sleep(0.05)  # Sleep for 1 second before retrying
        return None
    # def minimize_window(window_title):
    #
    #     hwnd = wait_for_window_title(window_title)
    #     if hwnd:
    #         win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    #         print(f"Window with title '{window_title}' minimized.")
    #     else:
    #         print(f"Window with title '{window_title}' not found within timeout.")
    folder = os_path.join(start_folder, peaklogger_folder)
    os_chdir(folder)
    os_system("start /min PeakLogger")
    wait_for_window_title("PeakLogger")
    # minimize_window("PeakLogger")


def center_on_screen(self):
    screen_geo = QApplication.desktop().screenGeometry()
    window_geo = self.geometry()

    # Calculate the horizontal and vertical center position
    center_x = int((screen_geo.width() - window_geo.width()) / 2)
    center_y = int((screen_geo.height() - window_geo.height()) / 2)

    # Move the window to the calculated position
    self.move(center_x, center_y)
    self.show()


def scale_app(widget, scale_factor: float):

    def scale_app2(widget, scale_factor: float):
        if isinstance(widget, QWidget):

            if isinstance(widget, QTextBrowser):
                rich_text_content = widget.toHtml()
                def replacer(match):
                    original_size = int(match.group(2))
                    new_size = int(original_size * scale_factor)
                    return f"{match.group(1)}{new_size}{match.group(3)}"
                scaled_text = re_sub(r'(font-size:|size=)(\d+)(pt|px|%)', replacer, rich_text_content)
                widget.setHtml(scaled_text)

            if hasattr(widget, 'font') and hasattr(widget, 'setFont'):
                font = widget.font()
                font.setPointSizeF((font.pointSize() * scale_factor))
                widget.setFont(font)

            if isinstance(widget, QPushButton):
                current_icon_size = widget.iconSize()
                new_icon_size = QSize(int(current_icon_size.width() * scale_factor), int(current_icon_size.height() * scale_factor))
                widget.setIconSize(new_icon_size)

            if isinstance(widget, QLabel):
                pixmap = widget.pixmap()
                if pixmap and not pixmap.isNull():  # Check if pixmap is null
                    scaled_pixmap = pixmap.scaled(
                        int(pixmap.width() * scale_factor),
                        int(pixmap.height() * scale_factor)
                    )
                    widget.setPixmap(scaled_pixmap)
                elif pixmap and pixmap.isNull():  # Log an error message if pixmap is null
                    print(f"Warning: Pixmap for widget {widget.objectName()} is null.")

            current_size = widget.size()
            widget.resize(int(current_size.width() * scale_factor), int(current_size.height() * scale_factor))

            current_pos = widget.pos()
            widget.move(int(current_pos.x() * scale_factor), int(current_pos.y() * scale_factor))

        for child in widget.children():
            scale_app2(child, scale_factor)

    QTimer.singleShot(0, lambda: scale_app2(widget, scale_factor))


def start_sentinel_d(project: str, sentinel_app_folder: str, subfolder_sentinel_project, no_log=False,
                     no_proj=False, get_pid=False):  # ! vybrat path to .exe a project
    kill_sentinel(False, True)
    coms = list_com_ports()
    active_com = "AUTO"
    for com in coms:
        if com.manufacturer == "FTDI":
            active_com = com.device
    os_chdir(sentinel_app_folder)
    comm = "start "
    if not no_log:
        comm += "/min " if not no_log else ""
    comm += f"ClientApp_Dyn -switch={active_com} "
    if no_log:
        comm += "-autolog=NO "
    project = os_path.join(subfolder_sentinel_project, project)
    comm += project
    if not no_proj:
        print("COM: ", active_com)
        os_system(comm)
    else:
        if os_path.exists("test.ssd"):
            os_system(f"start ClientApp_Dyn -switch={active_com} test.ssd")
        else:
            os_system(f"start ClientApp_Dyn")
    if get_pid:
        return 1111
    return None


def list_com_ports():
    com_ports = serial.tools.list_ports.comports()
    coms = []
    for port in com_ports:
        coms.append(port)
    return coms


def start_sentinel_modbus(modbus_path: str, project_path: str, project: str, opt_channels: int, check_pid=False):
    sentinel_app = modbus_path
    os_chdir(sentinel_app)

    config = ConfigParser()
    with codecs_open('settings.ini', 'r', encoding='utf-8-sig') as f:
        config.read_file(f)

    if opt_channels == 1:
        config.set('ranges', 'definition_file', f'{project_path}/{project}')
    elif opt_channels == 2:
        config.set('ranges', 'definition_file', f'{project_path}/{project}')

    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

    os_system("start /min Sentinel-Dynamic-Modbus")
    if check_pid:
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'] == "Sentinel-Dynamic-Modbus":
                return process.info['pid']
    return None


def kill_process(app_name):
    for process in psutil.process_iter(attrs=['pid', 'name']):
        if app_name.lower() in process.info['name'].lower():
            psutil.Process(process.info['pid']).terminate()


def kill_sentinel(dyn: bool, mod: bool):
    if dyn:
        app_name = "ClientApp_Dyn"
        kill_process(app_name)

    if mod:
        app_name = "Sentinel-Dynamic-Modbus"
        kill_process(app_name)


def kill_peaklogger():
    app_name = "PeakLogger"
    kill_process(app_name)


def dominant_frequency(samples, sampling_rate):
    # Calculate the FFT and its magnitude
    fft_values = np.fft.fft(samples)
    magnitudes = np.abs(fft_values)

    # Find the frequency with the highest magnitude
    dominant_freq_index = np.argmax(magnitudes[1:]) + 1  # exclude the 0Hz component

    # Calculate the actual frequency in Hz
    freqs = np.fft.fftfreq(len(samples), 1 / sampling_rate)
    dominant_freq = freqs[dominant_freq_index]

    return abs(dominant_freq)


def start_modbus(folder_sentinel_modbus_folder: str, project_path: str, opt_project: str,
                 folder_opt_export: str, opt_channels: int, opt_sentinel_file_name: str):
    kill_sentinel(True, False)
    start_sentinel_modbus(folder_sentinel_modbus_folder, project_path, opt_project, opt_channels)
    QThread.msleep(100)

    os_chdir(folder_opt_export)

    if os_path.exists(opt_sentinel_file_name + '.csv'):
        os_remove(opt_sentinel_file_name + '.csv')


def check_usb(opt_vendor_ids, ref_vendor_ids):
    try:
        c = wmi_WMI()
    except Exception as e:
        print(f"COM Error initializing WMI: {e}")
        return False, False

    opt = False
    ref = False

    try:
        for usb in c.Win32_USBControllerDevice():
            # sleep(0.25)
            try:
                device = usb.Dependent
                device = device.DeviceID
                vid_start = device.find('VID_') + 4
                vid_end = device.find('&', vid_start)
                v_id = device[vid_start:vid_end]

                if opt_vendor_ids:
                    if str(v_id.upper()) in [str(id1) for id1 in opt_vendor_ids]:
                        opt = True
                if ref_vendor_ids:
                    if str(v_id.upper()) in [str(id1) for id1 in ref_vendor_ids]:
                        ref = True
                if opt and ref:
                    break
            except Exception as e:
                continue
    except Exception as e:
        return False, False

    return opt, ref


def check_function_gen_connected(generator_id, first_start=False):
    try:
        rm = pyvisa_ResourceManager(r"C:\Windows\System32\visa64.dll")
        devices = rm.list_resources()
    except Exception as e:
        print(e)

    if generator_id in devices:
        if first_start:
            try:
                inst = rm.open_resource(generator_id)
                res = inst.query("OUTPut1:STATe?")
                if res[0] == "1":
                    inst.write('OUTPut1:STATe OFF')
                rm.close()
                return True, False
            except Exception as e:
                print(e)
                return True, True
        return True, False
    return False, False


def load_all_config_files(combobox, config_file_path: str, opt_sensor_type: str, subfolderConfig_path: str):
    combobox.blockSignals(True)
    combobox.clear()
    yaml_files = return_all_configs(opt_sensor_type, subfolderConfig_path)
    for yaml_file in yaml_files:
        file_name_without_extension = os_path.basename(yaml_file).rsplit('.', 1)[0]
        combobox.addItem(file_name_without_extension)
    if config_file_path is not None:
        file_name_without_extension = os_path.basename(QFileInfo(config_file_path).fileName()).rsplit('.', 1)[0]
        combobox.setCurrentText(file_name_without_extension)
    combobox.blockSignals(False)
    return yaml_files


def set_wavelengths(s_n: str, sentinel_file_path: str, project: str, start_folder: str):
    iwl = DatabaseCom(start_folder)
    wl = iwl.load_sylex_nominal_wavelength(objednavka_id=s_n)

    project_path = os_path.join(sentinel_file_path, project)
    if wl != 0 and wl != -1 and wl is not None:
        if len(wl) == 2:
            mid = np.abs(wl[0] - wl[1]) / 2

            tree = ET_parse(project_path)
            root = tree.getroot()

            i = 0
            for peak_range in root.findall(".//PeakRangeDefinition"):
                # print("PEAK")
                # Find RangeStart and RangeEnd elements
                range_start = peak_range.find("RangeStart")
                range_end = peak_range.find("RangeEnd")

                if range_start is not None and range_end is not None and i < len(wl):
                    # print("Change")
                    # Modify their values
                    if i == 0:
                        range_start.text = str(float(wl[i] - 10))
                        range_end.text = str(float(wl[i] + mid))
                    else:
                        range_start.text = str(float(wl[i] - mid))
                        range_end.text = str(float(wl[i] + 10))
                    i += 1
                else:
                    return -2
            tree.write(project_path)
    if wl is None:
        return 0
    return wl


def get_params(s_n, start_folder):
    iwl = DatabaseCom(start_folder)
    info = iwl.load_sylex_nominal_wavelength(objednavka_id=re_search(r'(-?\d+(\.\d+)?)', s_n).group(1), all_info=True)
    if info != 0:
        arr = [str(info[0]), str(info[5])]
        arr2 = [str(info[3]), str(info[6])]
        return arr, arr2
    else:
        return [None, None], [None, None]


def format_serial_number(serial, div):
    match = re_search(r"(\d+)(\D+)(\d+)", serial)
    if match:
        part1 = match.group(1)
        part3 = int(match.group(3))  # Convert to integer to remove leading zeros

        formatted_serial = f"{part1}{div}{part3:04}"  # Format the integer with leading zeros to a width of 4
        return formatted_serial
    else:
        return serial


def return_all_configs(opt_sensor_type: str, subfolder_config_path: str):
    yaml_files = glob(os_path.join(subfolder_config_path, '*.yaml'))
    yaml_return = []
    for yaml_file in yaml_files:
        config_file_path = os_path.join(subfolder_config_path, yaml_file)
        with open(config_file_path, 'r') as file:
            config = yaml_safe_load(file)
            if config['opt_measurement']['sensor_type'] == opt_sensor_type:
                yaml_return.append(yaml_file)
    return yaml_return


def copy_files(serial_number, folder_id, source_folders, export_folder):
    print("EXPORT TO LOCAL SERVER")
    try:
        return_str = []
        folder_name_dict = {'optical': 'opt', 'reference': 'ref', 'calibration': 'cal'}

        target_folder = None
        for folder in os_listdir(export_folder):
            if folder.startswith(f"{folder_id}_"):
                target_folder = os_path.join(export_folder, folder)
                break

        if target_folder is None:
            return -1, f"No folder with ID {folder_id} found in {export_folder}"

        kalibracia_folder = os_path.join(target_folder, f"9_App_calibration")
        if not os_path.exists(kalibracia_folder):
            os_makedirs(kalibracia_folder)

        for short_name in folder_name_dict.values():
            sub_folder = os_path.join(kalibracia_folder, short_name)
            if not os_path.exists(sub_folder):
                os_makedirs(sub_folder)

        for folder_type, folder_path in source_folders.items():
            file_found = False
            for file_name in os_listdir(folder_path):
                if not file_name.endswith('.csv'):
                    continue

                name_without_extension = os_path.splitext(file_name)[0]
                if name_without_extension == serial_number:
                    print("NAME WITHOUT: ", name_without_extension)
                    file_found = True
                    source_file = os_path.join(folder_path, file_name)

                    target_subfolder = os_path.join(kalibracia_folder, folder_name_dict[folder_type])

                    # Check for files with the same name
                    existing_files = [f for f in os_listdir(target_subfolder) if f.startswith(name_without_extension)]
                    if existing_files:
                        highest_index = 0
                        for existing_file in existing_files:
                            # Match number_number_index.csv pattern
                            match = re_search(rf'{re_escape(name_without_extension)}_(\d+)\.csv$', existing_file)
                            if match:
                                index = int(match.group(1))
                                highest_index = max(highest_index, index)
                        # new_file_name = f"{name_without_extension}_{highest_index + 1}.csv"
                        new_file_name = name_without_extension
                        new_file_name += f"_{highest_index + 1}.csv"
                    else:
                        new_file_name = name_without_extension
                        new_file_name += "_0.csv"

                    target_file = os_path.join(target_subfolder, new_file_name)

                    shutil_copy(source_file, target_file)

            if not file_found:
                print(f"No file with serial number {serial_number} found in {folder_path}")
                return_str.append(f"No file with serial number {serial_number} found in {folder_path}")

        if len(return_str) == 0:
            print("Export to the local raw database was successful!")
            return_str = (0, "Export to the local raw database was successful!", kalibracia_folder)
        else:
            return_str = (-1, return_str, None)
    except Exception as e:
        print(f"Unexpected error happened during export to the local raw DB: \n {e}")
        return -1, f"Unexpected error happened during export to the local raw DB: \n {e}", None
    return return_str


def centerWindow(self):
    # Get the rectangle specifying the geometry of the main window
    qr = self.frameGeometry()
    # Get the resolution of the screen and find the center point
    cp = QDesktopWidget().availableGeometry().center()
    # Set the center of the rectangle to the center of the screen
    qr.moveCenter(cp)
    # Move the top-left point of the application window to the top-left point of the qr rectangle, thus centering the window on the screen
    self.move(qr.topLeft())


def set_read_only(file_path):
    if platform_system() == "Windows":
        os_system(f"attrib +r {file_path}")
    else:
        os_chmod(file_path, 0o444)


def set_read_write(file_path):
    if platform_system() == "Windows":
        os_system(f"attrib -r {file_path}")
    else:
        os_chmod(file_path, 0o666)


def disable_ui_elements(ui_elements):
    for element in ui_elements:
        element.setEnabled(False)


def is_in_range(wl):
    try:
        if 1400.0 <= float(wl) <= 1600.0:
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False

def enable_ui_elements(ui_elements, set=True, only_widget_provided=False):
    if only_widget_provided:
        for widget in ui_elements:
            for element in widget.findChildren(QWidget):
                element.setEnabled(set)
    for element in ui_elements:
        element.setEnabled(set)


def save_statistics_to_csv(folder_path, file_name, time_stamp, serial_number, sensitivity, wl1, wl2=None):
    try:
        date = time_stamp.split(" ")[0]
        wavelengths = str(wl1)
        if wl2 is not None:
            wavelengths += "/" + str(wl2)

        # Append .csv to the file name
        file_name += ".csv"

        # Check if folder exists, if not, create it
        stats_folder_path = os_path.join(folder_path, "statistics")
        if not os_path.exists(stats_folder_path):
            os_makedirs(stats_folder_path)

        # Check if file exists, if not, create it and write header
        file_path = os_path.join(stats_folder_path, file_name)
        file_exists = os_path.exists(file_path)

        with open(file_path, mode='a', newline='') as file:
            writer = csv_writer(file)

            if not file_exists:
                writer.writerow(['Date', 'Serial Number', 'Wavelengths', 'Sensitivity'])

            writer.writerow([date, serial_number, wavelengths, str(sensitivity)])
        return 0
    except Exception as e:
        return e


def save_statistics_to_csv_strain(folder_path, file_name, time_stamp, serial_number, coef, ffl, error, wl1, wl2=None):
    try:
        date = time_stamp.split(" ")[0]
        wavelengths = str(wl1)
        if wl2 is not None:
            wavelengths += "/" + str(wl2)

        # Append .csv to the file name
        file_name += ".csv"

        # Check if folder exists, if not, create it
        stats_folder_path = os_path.join(folder_path, "statistics")
        if not os_path.exists(stats_folder_path):
            os_makedirs(stats_folder_path)

        # Check if file exists, if not, create it and write header
        file_path = os_path.join(stats_folder_path, file_name)
        file_exists = os_path.exists(file_path)

        with open(file_path, mode='a', newline='') as file:
            writer = csv_writer(file)

            if not file_exists:
                writer.writerow(['Date', 'Serial Number', 'Wavelengths', 'CoeffA', 'FFL', 'ERROR'])

            writer.writerow([date, serial_number, wavelengths, str(coef), str(ffl), str(error)])
        return 0
    except Exception as e:
        return e


def show_add_dialog(self, start_fold, lang, trans, parent=None, start=True):
    from MyGeneralInputPopUp import MyGeneralInputPopUp

    def add_operator_to_yaml(new_operator, file_path="operators.yaml"):
        os_chdir(start_fold)
        # Read the existing YAML file
        with open(file_path, 'r') as f:
            data = yaml_safe_load(f)

        # Check if 'operators' key exists in the YAML, if not create one
        if 'operators' not in data:
            data['operators'] = []

        # Add the new operator to the list of operators
        data['operators'].append(new_operator)

        # Write the updated data back to the YAML file
        with open(file_path, 'w') as f:
            yaml_safe_dump(data, f)

        print(f"Added {new_operator} to {file_path}")
        if start:
            self.load_operators(select_operator=new_operator)

    box = MyGeneralInputPopUp(parent=parent, left_btn=trans[lang]['add_op'],
                              right_btn=trans[lang]['close_btn'],
                              label=trans[lang]['add_op_msg'])
    box.ui.input_line.setPlaceholderText(trans[lang]['add_op_msg_placeHolder'])
    box.ui.input_line.setFocus()
    box.show_modal()
    result = box.continue_code

    if result:
        op = box.value
        if op:
            add_operator_to_yaml(op)
        return op
    else:
        return None


def open_folder_in_explorer(folder_path):
    folder_path = folder_path.replace("/", "\\")
    print(folder_path)
    if os_path.exists(folder_path):
        subprocess_run(['explorer', folder_path])
    else:
        print("Folder does not exist")


def save_error(path, e):
    os_chdir(os_path.join(path, "LOGS"))
    current_time = datetime.now().time().strftime("%H:%M:%S.%f")
    today = datetime.today().strftime("%b-%d-%Y")
    with open("error_log.txt", "a") as f:  # Open the file in append mode
        f.write("\n-- " + today)
        f.write(" " + current_time)
        if isinstance(e, list):
            for item in e:
                f.write(str(item) + "\n")  # Convert each item to string and write to the file
        else:
            f.write(str(e) + "\n")  # Convert 'e' to string to ensure compatibility and write to the file


def linear_regression(x, y):
    n = len(x)
    m = (n * np_sum(x * y) - np_sum(x) * np_sum(y)) / (n * np_sum(x ** 2) - (np_sum(x)) ** 2)
    b = (np_sum(y) - m * np_sum(x)) / n
    return m, b


class ThreadAddVendorIds(QThread):
    update_label = pyqtSignal(str)

    def __init__(self, start_folder, sensor_type, device_type, yaml_folder=None):
        super().__init__()
        print("BUILDING THREAD")
        self.start_folder = start_folder
        self.sensor_type = sensor_type
        self.device_type = device_type
        self.yaml_folder = yaml_folder
        self.exit_flag = False

    def run(self):
        print("START THREAD")
        pythoncom.CoInitialize()
        self.add_vendor_id(self.start_folder, self.sensor_type, self.device_type, self.yaml_folder)

    def add_vendor_id(self, start_folder, sensor_type, device_type, yaml_folder=None):
        if yaml_folder is None:
            yaml_folder = os_path.join(start_folder, "devices_vendor_ids.yaml")
        vid = None
        pid = None

        def add_vid_to_yaml():
            # Read existing data from YAML file
            with open(yaml_folder, "r") as file:
                data = yaml_safe_load(file)
            if data[sensor_type][device_type] is None:
                # Add the VID to the list
                data[sensor_type][device_type] = []
            if vid not in data[sensor_type][device_type]:
                # Add the VID to the list
                data[sensor_type][device_type].append(vid)

                # Write the updated data back to the YAML file
                with open(yaml_folder, "w") as file:
                    yaml_safe_dump(data, file)
                    return True
            else:
                print("VID is already in yaml file")
                return False

        def on_device_event(event):
            instance = event.TargetInstance
            if instance is not None:
                if "USB" in instance.PNPDeviceID:
                    device_id = instance.PNPDeviceID
                    print(f"New USB Device Connected with ID: {device_id}")
                    nonlocal vid, pid
                    # Extract VID and PID using regular expressions
                    match = re_search(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", device_id)
                    if match:
                        vid, pid = match.groups()
                        print(f"Vendor ID: {vid}, Product ID: {pid}")
                        self.exit_flag = True

        # Initialize WMI and set up event subscription
        wmi = wmi_WMI()
        watcher = wmi.ExecNotificationQuery(
            "SELECT * FROM __InstanceCreationEvent WITHIN 2 WHERE TargetInstance ISA 'Win32_PnPEntity'")

        # Event loop
        while not self.exit_flag:
            print("LOOP")
            event = watcher.NextEvent()
            on_device_event(event)
            self.msleep(50)

        if vid is not None:
            res = add_vid_to_yaml()
            self.update_label.emit(f"VID: {vid},PID: {pid}, OK!" + "\nDevice was added" if res else "Duplicate VID/PID")

        print("CLOSE")


class PopupWindow(QWidget):
    def __init__(self, msg, w=200, h=50, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setFixedSize(w, h)
        layout = QVBoxLayout(self)
        label = QLabel(msg, alignment=Qt.AlignCenter)
        layout.addWidget(label)

    def show_for_a_while(self, timeout=1000):
        # Center the popup relative to its parent (the main window)
        if self.parent():
            parent_geometry = self.parent().frameGeometry()
            self.move(
                parent_geometry.x() + (parent_geometry.width() - self.width()) // 2,
                parent_geometry.y() + (parent_geometry.height() - self.height()) // 2
            )
        self.show()
        QTimer.singleShot(timeout, self.close)


class RollingAverager:
    from collections import deque

    def __init__(self, window_size):
        self.window_size = window_size
        self.buffer = self.deque(maxlen=window_size)
        self.total = 0

    def update(self, new_sample):
        """
        Updates the total based on the new sample, maintains the buffer size,
        and returns the updated average value.
        """
        if len(self.buffer) == self.window_size:
            self.total -= self.buffer.popleft()  # remove oldest value if buffer is full
        if new_sample != 0:
            self.buffer.append(new_sample)
            self.total += new_sample
        return self.average()

    def average(self):
        """
        Returns the average of the samples in the buffer.
        If no samples are present, returns None.
        """
        count = len(self.buffer)
        if count == 0:
            return -1
        return self.total / count


class DecimalValidator(QValidator):
    def __init__(self):
        super().__init__()

    def validate(self, input_str, pos):
        # Check if the input string is empty
        if not input_str:
            return (QValidator.Acceptable, input_str, pos)

        # Replace commas with dots and check if it's a valid float
        input_str = input_str.replace(',', '.')
        try:
            float(input_str)
            return (QValidator.Acceptable, input_str, pos)
        except ValueError:
            return (QValidator.Invalid, input_str, pos)


class PassWindowBig(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Red Window")
        self.setAutoFillBackground(True)
        self.thread = WaitForMouseMovement()

    def show_color(self, color, parent):
        self.thread = WaitForMouseMovement()
        self.thread.finished.connect(self.hide)
        p = self.palette()
        p.setColor(self.backgroundRole(), color)
        self.setPalette(p)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.thread.start()
        parent.raise_()
        parent.activateWindow()


class WaitForMouseMovement(QThread):

    def __init__(self):
        super().__init__()

    def run(self):
        savedpos = win32api.GetCursorPos()
        while True:
            curpos = win32api.GetCursorPos()
            if self.distance(savedpos, curpos) >= 5:
                break
            self.msleep(250)

    def distance(self, pos1, pos2):
        return math_sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)


class WaitForPeakLogger(QThread):

    def __init__(self, start_folder, peaklogger_folder=r"C:PeakLogger\oapp"):
        super().__init__()
        self.start_folder = start_folder
        self.peaklogger_folder = peaklogger_folder

    def run(self):
        print("START WaitForPeakLogger")
        def wait_for_window_title(title, timeout=30):
            end_time = time.time() + timeout
            while time.time() < end_time:
                hwnd = win32gui.FindWindow(None, title)
                if hwnd != 0:
                    return hwnd
                self.msleep(250)  # Sleep for 1 second before retrying
            return None
        try:
            folder = os_path.join(self.start_folder, self.peaklogger_folder)
            os_chdir(folder)
            os_system("start /min PeakLogger")
            self.msleep(1000)
            wait_for_window_title("PeakLogger")
            start_peaklogger(self.start_folder, self.peaklogger_folder)
            print("Finished WaitForPeakLogger")
        except Exception as e:
            print("WaitForPeakLogger: ",e)
