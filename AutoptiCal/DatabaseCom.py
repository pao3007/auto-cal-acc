import re

from yaml import safe_load
from os import path


def find_wl_index(arr):
    # Iterate through the array
    for index, item in enumerate(arr):
        # Convert the item to string and check if 'WL:' is in the string
        if isinstance(item, str) and 'WL:' in item:
            return index  # Return the index of the first occurrence
    return -1  # Return -1 if 'WL:' is not found in any element


class DatabaseCom:
    import pyodbc as pyodbc

    def __init__(self, start_folder):
        filename = path.join(start_folder, "database_com.yaml")
        with open(filename, 'r', encoding="utf-8") as file:
            self.database_conf = safe_load(file)

    def do_connection_string(self, database):
        try:
            integrated_security = 'True' if self.database_conf['ConnectionKey']['IntegratedSecurity'] else 'False'
            mars = 'True' if self.database_conf['ConnectionKey']['MultipleActiveResultSets'] else 'False'
            persist_security_info = 'True' if self.database_conf['ConnectionKey']['PersistSecurityInfo'] else 'False'
            conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};" \
                       f"SERVER={str(self.database_conf['ConnectionKey']['DataSource'])};" \
                       f"DATABASE={str(database)};" \
                       f"UID={str(self.database_conf['ConnectionKey']['UserID'])};" \
                       f"PWD={str(self.database_conf['ConnectionKey']['Password'])};" \
                       f"Integrated Security={integrated_security};" \
                       f"MultipleActiveResultSets={mars};" \
                       f"Persist Security Info={persist_security_info};" \
                       f"Connect Timeout={str(self.database_conf['ConnectionKey']['ConnectTimeout'])};"
            conn_str += ";TrustServerCertificate=yes;Encrypt=no"
            return conn_str
        except Exception as e:
            print("do_connection_string:", e)
            return -1

    def export_to_database_acc_strain(self, params, sensor):
        print("EXPORT TO DATABASE")
        try:
            conn_str = self.do_connection_string(self.database_conf['ExportDatabase'])
            query = '''INSERT INTO tblKalibracia_Accel (SylexON, Customer,
            SylexSN, ErrorCount, CalibrationNumber, CalibrationFinal, Sensitivity, CWL1, CWL2, Flatness, Offset,
            Asymmetry, RawDataLocation, CalibrationProfile, TempCoef1, TempCoef2, Notes, Timestamp, Operator,
            ProductDescription, SensorName, Evaluation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?)'''
            if sensor == "ACC":
                query = self.database_conf['ExportToDatabaseAcc']
                cal_num = self.fetch_records_by_sylexsn(params[2], conn_str, sensor="ACC")
            elif sensor == "STRAIN":
                query = self.database_conf['ExportToDatabaseStrain']
                cal_num = self.fetch_records_by_sylexsn(params[2], conn_str, sensor="STRAIN")
            if cal_num == 0:
                params[4] = 0
            elif len(cal_num) >= 1:
                if sensor == "ACC":
                    self.set_last_calibration_old(params[2], "ACC")
                elif sensor == "STRAIN":
                    self.set_last_calibration_old(params[2], "STRAIN")
                params[4] = int(cal_num[5]) + 1
            print(params)
        except Exception as e:
            print(f"export_to_database1:{e}")
            return -2, e
        try:
            conn = self.pyodbc.connect(conn_str)
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
            conn.close()
            return 0, ""
        except Exception as e:
            print("export_to_database2:", e)
            return -1, e

    def update_export_note(self, s_n, notes, sensor):
        conn_str = self.do_connection_string(self.database_conf['ExportDatabase'])
        query = "UPDATE tblKalibracia_Accel SET Notes = ? WHERE SylexSN = ? AND CalibrationFinal = 1"
        if sensor == "ACC":
            query = self.database_conf['ExportNoteAcc']
        elif sensor == "STRAIN":
            query = self.database_conf['ExportNoteStrain']
        try:
            conn = self.pyodbc.connect(conn_str)
            with conn.cursor() as cursor:
                cursor.execute(query, (notes, s_n))
                conn.commit()
            conn.close()
            return 1, ""
        except self.pyodbc.Error as e:
            print("update_export_note:", e)
            return -1, e

    def fetch_records_by_sylexsn(self, sylexsn_value, conn_str, sensor):
        # query = """
        #     SELECT TOP 1 *
        #     FROM tblKalibracia_Accel
        #     WHERE SylexSN = ?
        #     ORDER BY Id DESC
        #     """
        if sensor == "ACC":
            query = self.database_conf['FindMostRecentSN_ACC']
        elif sensor == "STRAIN":
            query = self.database_conf['FindMostRecentSN_STRAIN']
        try:
            conn = self.pyodbc.connect(conn_str)
            with conn.cursor() as cursor:
                cursor.execute(query, sylexsn_value)
                rows = cursor.fetchone()
            conn.close()
            if rows:
                return rows
            return 0
        except self.pyodbc.Error as e:
            print("fetch_records_by_sylexsn:", e)
            return -1

    def use_fetch_records_by_sylexsn(self, sylexsn_value, sensor):
        conn_str = self.do_connection_string(self.database_conf['ExportDatabase'])
        return self.fetch_records_by_sylexsn(sylexsn_value, conn_str, sensor)

    def set_last_calibration_old(self, s_n, sensor):
        conn_str = self.do_connection_string(self.database_conf['ExportDatabase'])
        query = """
        UPDATE tblKalibracia_Accel
        SET CalibrationFinal=0
        WHERE SylexSN = ? AND CalibrationFinal=1
        """
        if sensor == "ACC":
            query = self.database_conf['UpdateFinalValuesAcc']
        if sensor == "STRAIN":
            query = self.database_conf['UpdateFinalValuesStrain']
        try:
            conn = self.pyodbc.connect(conn_str)
            with conn.cursor() as cursor:
                cursor.execute(query, s_n)
                conn.commit()
            conn.close()
            return 0
        except self.pyodbc.Error as e:
            print("set_last_calibration_old:", e)
            return -1

    def load_sylex_nominal_wavelength(self, objednavka_id, all_info=False):
        query = """
        SELECT
            [Zákazky].[ID] AS [Zakazka],
            [Výrobky].[ID] AS [Objednavka],
            [Výrobky].[Množstvo],
            [Výrobky].[Popis],
            [Zákazky].[Divízia],
            [Zákazky].[Obchodné meno] AS [Zakaznik],
            [Výrobky].[Sensor]
        FROM
            [Zákazky]
        INNER JOIN
            [Výrobky] ON [Zákazky].[ID] = [Výrobky].[IDZákazky]
        LEFT OUTER JOIN
            [ČíselníkNálepky] ON [Výrobky].[ČíselníkNálepkyID] = [ČíselníkNálepky].[ID]
        LEFT OUTER JOIN
            [VýrobkyNálepky] ON [Výrobky].[ID] = [VýrobkyNálepky].[VýrobkyID]
        WHERE
            [Výrobky].[ID] = ?
        """
        query = self.database_conf['GetWaveLengthQuery']
        try:

            database = self.database_conf['LoadWLDatabase']
            con_str = self.do_connection_string(database)
            conn = self.pyodbc.connect(con_str)
            with conn.cursor() as cursor:
                cursor.execute(query, objednavka_id)
                row = cursor.fetchone()
            conn.close()

            if row:
                if all_info:
                    return row
                else:
                    return self.extract_wavelengths(row)
            return 0
        except self.pyodbc.Error as e:
            print("load_sylex_nominal_wavelength:", e)
            return -1

    # def extract_wavelengths(self, arr):
    #     import re
    #     pattern = r'WL:\s*([\d,\.]+)(?:[\/\-_]([\d,\.]+))?nm'
    #     try:
    #         for item in arr:
    #             s = str(item)
    #             match = re.search(pattern, s)
    #             print(match)
    #             # match_split = re.split(r'[\/\-_]', match.group(1))
    #             # print(match_split)
    #             # match = [float(w.replace(',', '.')) for w in match if w is not None]
    #             # print(match)
    #             if match:
    #                 match_split = re.split(r'[\/\-_]', match.group(1))
    #                 print(match_split)
    #                 match_split = [float(w.replace(',', '.')) for w in match_split if w is not None]
    #                 print(match_split)
    #                 return list(map(int, match_split))
    #         return None
    #     except Exception as e:
    #         print("extract_wavelengths:", e)
    #         return -1

    # def extract_wavelengths(self, arr):
    #     import re
    #     pattern = r'WL:\s*([\d,\.]+)(?:[\/\-_]([\d,\.]+))?nm'
    #     try:
    #         for item in arr:
    #             s = str(item)
    #             match = re.search(pattern, s)
    #             print(match)
    #             if match:
    #                 # Initialize list to store the wavelengths
    #                 wavelengths = []
    #
    #                 # Check and append the first wavelength
    #                 if match.group(1):
    #                     wavelengths.append(float(match.group(1).replace(',', '.')))
    #
    #                 # Check and append the second wavelength if it exists
    #                 if match.group(2):
    #                     wavelengths.append(float(match.group(2).replace(',', '.')))
    #
    #                 print(wavelengths)
    #
    #                 # Convert each wavelength to int
    #                 return [int(w) for w in wavelengths]
    #         return None
    #     except Exception as e:
    #         print("extract_wavelengths:", e)
    #         return -1

    def extract_wavelengths(self, arr):
        import re
        print(arr)
        try:
            index = find_wl_index(arr)
            s = arr[index]
            # Regular expression to match the patterns
            # This regex is further updated to capture whole numbers and numbers with decimals,
            # considering divisors between them
            pattern = r'WL:.*?;'
            matches = re.findall(pattern, s)[0]
            s = matches
            pattern = r'\b\d{4}(?:[,.]\d)?(?:[/_-]\d{4}(?:[,.]\d)?)?'
            # Find all matches in the text
            matches = re.findall(pattern, s)

            # Processing each match to replace commas with dots and split if there are divisors
            values = []
            for match in matches:
                # Splitting the match by the divisors if they exist
                split_values = re.split('[/_-]', match)
                # Replacing commas with dots and adding to the values list
                values.extend([float(value.replace(',', '.')) for value in split_values])

            return values
            return None
        except Exception as e:
            print("extract_wavelengths:", e)
            return -1

    def extract_wavelengths_strain(self, sql_return):
        # Regular expression to match the patterns
        # This regex is further updated to capture whole numbers and numbers with decimals,
        # considering divisors between them

        index = find_wl_index(sql_return)
        text = str(sql_return[index])
        # Find all matches in the text
        pattern = r'WL:.*?;'
        matches = re.findall(pattern, text)[0]
        text = matches
        pattern = r'\b\d{4}(?:[,.]\d)?(?:[/_-]\d{4}(?:[,.]\d)?)?'
        matches = re.findall(pattern, text)

        # Processing each match to replace commas with dots and split if there are divisors
        values = []
        for match in matches:
            # Splitting the match by the divisors if they exist
            split_values = re.split('[/_-]', match)
            # Replacing commas with dots and adding to the values list
            values.extend([float(value.replace(',', '.')) for value in split_values])
        return values

    def get_strain_info(self, SN, all_info=False, get_wl=False):
        query = self.database_conf['GetStrainData']
        try:
            database = self.database_conf['ExportDatabase']
            con_str = self.do_connection_string(database)
            conn = self.pyodbc.connect(con_str)
            with conn.cursor() as cursor:
                cursor.execute(query, SN)
                row = cursor.fetchone()
            conn.close()
            if row:
                wl = None
                if get_wl:
                    wl = self.extract_wavelengths_strain(row)
                return row if all_info else row[-1]/1000, wl
            return 0, None
        except self.pyodbc.Error as e:
            print("load_sylex_nominal_wavelength:", e)
            return -1, None

    def get_info_for_sensor(self, sn):
        query = self.database_conf['GetInfoForSensor']
        try:
            database = self.database_conf['ExportDatabase']
            con_str = self.do_connection_string(database)
            conn = self.pyodbc.connect(con_str)
            with conn.cursor() as cursor:
                cursor.execute(query, sn)
                row = cursor.fetchone()
            conn.close()
            if row:
                return 0, row
            else:
                return 0, None
        except self.pyodbc.Error as e:
            print("get_info_for_sensor:", e)
            return -1, None


    def get_strain_wavelength(self, ID):
        id_peak = self.get_strain_peak_id(ID)
        if id_peak == -1 or id_peak == 0:
            return id_peak
        query = self.database_conf['GetStrainWavelengths']
        try:
            database = self.database_conf['ExportDatabase']
            con_str = self.do_connection_string(database)
            conn = self.pyodbc.connect(con_str)
            with conn.cursor() as cursor:
                cursor.execute(query, id_peak)
                row = cursor.fetchall()
            conn.close()

            if row:
                return row
            return 0
        except self.pyodbc.Error as e:
            print("load_sylex_nominal_wavelength:", e)
            return -1

    def get_strain_peak_id(self, ID):
        query = self.database_conf['GetStrainIDPeak']
        try:
            database = self.database_conf['ExportDatabase']
            con_str = self.do_connection_string(database)
            conn = self.pyodbc.connect(con_str)
            with conn.cursor() as cursor:
                cursor.execute(query, ID)
                row = cursor.fetchone()
            conn.close()

            if row:
                return row
            return 0
        except self.pyodbc.Error as e:
            print("load_sylex_nominal_wavelength:", e)
            return -1
        