from yaml import safe_load as yaml_safe_load, dump as yaml_dump, YAMLError
from os import path as os_path, makedirs as os_makedirs
from Definitions import set_read_only, set_read_write


def check_file_path(file_path, default_path):
    if os_path.exists(file_path):
        return file_path
    else:
        return default_path


class MySettings:

    def __init__(self, starting_folder):

        self.max_acceleration = 0.001
        self.slope_check = None
        self.folder_statistics = None
        self.folder_db_export_folder = None
        self.starting_folder = starting_folder

        self.config = None
        self.generator_max_mvpp = None
        self.generator_sweep_type = None
        self.generator_sweep_stop_freq = None
        self.generator_sweep_start_freq = None
        self.generator_sweep_time = None
        self.calib_optical_sens_tolerance = None
        self.generator_id = None
        self.calib_phase_mark = None
        self.calib_angle_set_freq = None
        self.calib_r_flatness = None
        self.calib_l_flatness = None
        self.opt_dev_vendor = None
        self.ref_dev_vendor = None
        self.opt_first_start = True
        self.check_usbs_first_start = True
        self.calib_window = None
        self.settings_window = None
        self.S_N = None
        self.calib_reference_sensitivity = None
        self.calib_do_spectrum = None
        self.calib_downsample = None
        self.auto_export = None
        self.export_local_server = None
        self.calib_plot = None
        self.calib_filter_data = None
        self.calib_optical_sensitivity = None
        self.calib_gain_mark = None
        self.opt_project = None
        self.opt_sampling_rate = None
        self.opt_channels = None
        self.ref_sample_rate = None
        self.ref_number_of_samples = None
        self.ref_measure_time = None
        self.current_conf = None
        self.ref_device_name = None
        self.ref_channel = None
        self.opt_sensor_type = "Accelerometer"
        self.ref_connected = False

        documents_path = os_path.expanduser('~/Documents')

        self.folder_main = os_path.join(documents_path, 'Sylex_sensors_export')
        self.folder_ref_export = os_path.join(self.folder_main, 'reference')
        self.folder_opt_export = os_path.join(self.folder_main, 'optical')
        self.folder_ref_export_raw = os_path.join(self.folder_main, 'reference_raw')
        self.folder_opt_export_raw = os_path.join(self.folder_main, 'optical_raw')
        self.folder_calibration_export = os_path.join(self.folder_main, 'calibration')
        config_fold = os_path.join(self.starting_folder, "configs")
        self.subfolder_sentinel_project = os_path.join(config_fold, "sensors")
        self.subfolderConfig_path = os_path.join(config_fold, 'x_configs')

        self.folder_sentinel_modbus_folder = os_path.join(self.starting_folder, "modbus")
        self.folder_sentinel_D_folder = os_path.join(self.starting_folder, "sentinel-d")
        self.create_folders()

    def load_config_file(self, config_file_path):
        with open(config_file_path, 'r') as file:
            self.config = yaml_safe_load(file)

        self.current_conf = self.config['current']
        self.ref_channel = self.config['ref_device']['channel']
        self.ref_device_name = self.config['ref_device']['name']

        # self.my_settings.ref_number_of_samples = int(self.config['ref_measurement']['number_of_samples_per_channel'])
        self.ref_sample_rate = int(self.config['ref_measurement']['sample_rate'])

        # self.opt_sensor_type = self.config['opt_measurement']['sensor_type']
        self.opt_sampling_rate = int(self.config['opt_measurement']['sampling_rate'])
        self.opt_project = self.config['opt_measurement']['project']
        self.opt_channels = int(self.config['opt_measurement']['channels'])
        self.max_acceleration = float(self.config['opt_measurement']['max_acceleration'])

        self.calib_gain_mark = int(self.config['calibration']['gain_mark'])
        self.calib_optical_sensitivity = float(self.config['calibration']['optical_sensitivity'])
        self.calib_optical_sens_tolerance = float(self.config['calibration']['optical_sens_tolerance'])
        self.calib_filter_data = self.config['calibration']['filter_data']
        self.calib_plot = self.config['calibration']['plot']
        self.calib_downsample = int(self.config['calibration']['downsample'])
        self.calib_do_spectrum = int(self.config['calibration']['do_spectrum'])
        self.calib_reference_sensitivity = float(self.config['calibration']['reference_sensitivity'])
        self.calib_l_flatness = int(self.config['calibration']['l_flatness'])
        self.calib_r_flatness = int(self.config['calibration']['r_flatness'])
        self.calib_angle_set_freq = int(self.config['calibration']['angle_set_freq'])
        self.calib_phase_mark = int(self.config['calibration']['phase_mark'])
        self.slope_check = self.config['calibration']['slope_check']

        self.folder_main = check_file_path(self.config['save_data']['main_folder'], self.folder_main)
        # self.folder_main = self.config['save_data']['main_folder']
        self.folder_ref_export = check_file_path(self.config['save_data']['ref_export'], self.folder_ref_export)
        # self.folder_ref_export = self.config['save_data']['ref_export']
        self.folder_ref_export_raw = check_file_path(self.config['save_data']['ref_export_raw'], self.folder_ref_export_raw)
        # self.folder_ref_export_raw = self.config['save_data']['ref_export_raw']
        self.folder_opt_export = check_file_path(self.config['save_data']['opt_export'], self.folder_opt_export)
        # self.folder_opt_export = self.config['save_data']['opt_export']
        self.folder_opt_export_raw = check_file_path(self.config['save_data']['opt_export_raw'], self.folder_opt_export_raw)
        # self.folder_opt_export_raw = self.config['save_data']['opt_export_raw']
        self.folder_calibration_export = check_file_path(self.config['save_data']['calibration_export'], self.folder_calibration_export)
        # self.folder_calibration_export = self.config['save_data']['calibration_export']
        self.folder_db_export_folder = self.config['save_data']['db_folder']
        self.folder_statistics = self.config['save_data']['stats_folder']
        self.S_N = self.config['save_data']['S_N']
        self.export_local_server = self.config['save_data']['export_local_server']
        self.auto_export = self.config['save_data']['auto_export']

        self.generator_id = self.config['function_generator']['generator_id']
        self.generator_sweep_time = int(self.config['function_generator']['generator_sweep_time'])
        self.generator_sweep_start_freq = int(self.config['function_generator']['generator_sweep_start_freq'])
        self.generator_sweep_stop_freq = int(self.config['function_generator']['generator_sweep_stop_freq'])
        self.generator_sweep_type = self.config['function_generator']['generator_sweep_type']
        self.generator_max_mvpp = int(self.config['function_generator']['generator_max_vpp'])

        self.ref_measure_time = int(self.generator_sweep_time + 3)
        self.ref_number_of_samples = int(self.ref_measure_time * self.ref_sample_rate)

        return self.check_if_none()

    def set_current_config_file(self, current_conf, config_file_path):
        self.config['current'] = current_conf
        with open(config_file_path, 'w') as file:
            yaml_dump(self.config, file)
        # set_read_only(config_file_path)

        return self.check_if_none()

    def save_config_file(self, current_conf, config_file_path):
        self.config['current'] = current_conf
        self.config['ref_device']['channel'] = self.ref_channel
        self.config['ref_device']['name'] = self.ref_device_name

        self.config['ref_measurement']['number_of_samples_per_channel'] = self.ref_number_of_samples
        self.config['ref_measurement']['sample_rate'] = self.ref_sample_rate

        self.config['opt_measurement']['sensor_type'] = "Accelerometer"
        self.config['opt_measurement']['sampling_rate'] = self.opt_sampling_rate
        self.config['opt_measurement']['project'] = self.opt_project
        self.config['opt_measurement']['channels'] = self.opt_channels
        self.config['opt_measurement']['max_acceleration'] = self.max_acceleration

        self.config['calibration']['gain_mark'] = self.calib_gain_mark
        self.config['calibration']['optical_sensitivity'] = self.calib_optical_sensitivity
        self.config['calibration']['optical_sens_tolerance'] = self.calib_optical_sens_tolerance
        self.config['calibration']['filter_data'] = self.calib_filter_data
        self.config['calibration']['plot'] = self.calib_plot
        self.config['calibration']['downsample'] = self.calib_downsample
        self.config['calibration']['do_spectrum'] = self.calib_do_spectrum
        self.config['calibration']['reference_sensitivity'] = self.calib_reference_sensitivity
        self.config['calibration']['l_flatness'] = self.calib_l_flatness
        self.config['calibration']['r_flatness'] = self.calib_r_flatness
        self.config['calibration']['angle_set_freq'] = self.calib_angle_set_freq
        self.config['calibration']['phase_mark'] = self.calib_phase_mark
        self.config['calibration']['phase_mark'] = self.calib_phase_mark
        self.config['calibration']['slope_check'] = self.slope_check

        self.config['save_data']['main_folder'] = self.folder_main
        self.config['save_data']['ref_export'] = self.folder_ref_export
        self.config['save_data']['ref_export_raw'] = self.folder_ref_export_raw
        self.config['save_data']['opt_export'] = self.folder_opt_export
        self.config['save_data']['opt_export_raw'] = self.folder_opt_export_raw
        self.config['save_data']['calibration_export'] = self.folder_calibration_export
        self.config['save_data']['db_folder'] = self.folder_db_export_folder
        self.config['save_data']['stats_folder'] = self.folder_statistics
        self.config['save_data']['export_local_server'] = self.export_local_server
        self.config['save_data']['auto_export'] = self.auto_export

        self.config['function_generator']['generator_id'] = self.generator_id
        self.config['function_generator']['generator_sweep_time'] = self.generator_sweep_time
        self.config['function_generator']['generator_sweep_start_freq'] = self.generator_sweep_start_freq
        self.config['function_generator']['generator_sweep_stop_freq'] = self.generator_sweep_stop_freq
        self.config['function_generator']['generator_sweep_type'] = self.generator_sweep_type
        self.config['function_generator']['generator_max_vpp'] = self.generator_max_mvpp

        self.config['save_data']['S_N'] = self.S_N

        # set_read_write(config_file_path)

        with open(config_file_path, 'w') as file:
            yaml_dump(self.config, file)
        # set_read_only(config_file_path)

        return self.check_if_none()

    def check_if_none(self):
        def traverse(data):
            if data is None or data == '':
                return True
            if isinstance(data, dict):
                return any(traverse(value) for value in data.values())
            if isinstance(data, list):
                return any(traverse(item) for item in data)
            return False

        try:
            return traverse(self.config)
        except YAMLError as e:
            print(f"Error parsing YAML: {e}")
            return True

    def default_config(self, sensor_type):
        documents_path = os_path.expanduser('~/Documents')

        main_folder_path = os_path.join(documents_path, 'Sylex_sensors_export')
        subfolderRef_path = os_path.join(main_folder_path, 'reference')
        subfolderOpt_path = os_path.join(main_folder_path, 'optical')
        subfolderRefRaw_path = os_path.join(main_folder_path, 'reference_raw')
        subfolderOptRaw_path = os_path.join(main_folder_path, 'optical_raw')
        subfolderCalibrationData = os_path.join(main_folder_path, 'calibration')

        def_config = {
            'current': True,
            'ref_device': {
                'channel': None,
                'name': None,
            },
            'ref_measurement': {
                'number_of_samples_per_channel': 320000,
                'sample_rate': 12800,
                'measure_time': 25
            },
            'opt_measurement': {
                'sensor_type': "Accelerometer",
                'sampling_rate': 800,
                'project': None,
                'channels': 1,
                'max_acceleration': 0.001
            },
            'calibration': {
                'gain_mark': 150,
                'optical_sensitivity': 0,
                'optical_sens_tolerance': 0,
                'filter_data': 'high-pass',
                'plot': 0,
                'downsample': 1,
                'do_spectrum': 1,
                'reference_sensitivity': 1,
                'l_flatness': 10,
                'r_flatness': 100,
                'angle_set_freq': 10,
                'phase_mark': 300,
                'slope_check': 1,
            },
            'save_data': {
                'main_folder': main_folder_path,
                'ref_export': subfolderRef_path,
                'ref_export_raw': subfolderRefRaw_path,
                'opt_export': subfolderOpt_path,
                'opt_export_raw': subfolderOptRaw_path,
                'calibration_export': subfolderCalibrationData,
                'db_folder': None,
                'modbus_folder': None,
                'stats_folder': None,
                'auto_export': True,
                'export_local_server': True,
                'S_N': 'measured_data.csv'
            },
            'function_generator': {
                'generator_id': None,
                'generator_sweep_time': 0,
                'generator_sweep_start_freq': 0,
                'generator_sweep_stop_freq': 0,
                'generator_sweep_type': 'SINusoid',
                'generator_max_vpp': 0,
            }
        }
        return def_config

    def create_folders(self):
        if not os_path.exists(self.folder_main):
            # Create the main folder
            os_makedirs(self.folder_main)
        # Create the subfolders inside the main folder
        os_makedirs(self.folder_ref_export, exist_ok=True)
        os_makedirs(self.folder_opt_export, exist_ok=True)
        os_makedirs(self.folder_ref_export_raw, exist_ok=True)
        os_makedirs(self.folder_opt_export_raw, exist_ok=True)
        os_makedirs(self.folder_calibration_export, exist_ok=True)
        os_makedirs(self.subfolderConfig_path, exist_ok=True)

    def check_properties_for_none(self):
        for attribute, value in self.__dict__.items():
            if value is None:
                print(f"Property '{attribute}' contains None")
                return True
        print("No properties contain None")
        return False

    def create_config_file(self, yaml_name='default_config_acc.yaml'):
        config_file_path = os_path.join(self.subfolderConfig_path, yaml_name)
        new_conf = self.default_config(self.opt_sensor_type)
        with open(config_file_path, 'w') as file:
            yaml_dump(new_conf, file)

        return self.load_config_file(config_file_path), config_file_path

