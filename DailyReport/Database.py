from os import path
from yaml import safe_load


class DatabaseCom:
    import pyodbc as pyodbc

    def __init__(self, start_folder):
        self.filename = path.join(start_folder, "db_config.yaml")
        self.database_conf = None
        self.load_config()

    def load_config(self):
        with open(self.filename, 'r', encoding="utf-8") as file:
            self.database_conf = safe_load(file)

    def do_connection_string(self):
        try:
            integrated_security = 'True' if self.database_conf['ConnectionKey']['IntegratedSecurity'] else 'False'
            mars = 'True' if self.database_conf['ConnectionKey']['MultipleActiveResultSets'] else 'False'
            persist_security_info = 'True' if self.database_conf['ConnectionKey']['PersistSecurityInfo'] else 'False'
            conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};" \
                       f"SERVER={str(self.database_conf['ConnectionKey']['DataSource'])};" \
                       f"DATABASE={str(self.database_conf['ConnectionKey']['DatabaseToConnect'])};" \
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

    def get_records(self, conn_str, query, date):
        try:
            conn = self.pyodbc.connect(conn_str)
            with conn.cursor() as cursor:
                cursor.execute(query, date)
                rows = cursor.fetchall()
            conn.close()
            if rows:
                return rows
            return 0
        except self.pyodbc.Error as e:
            print("EXCEPTION in get_records(): ", e)
            return None

    def get_records_by_on(self, conn_str, on, query):
        try:
            conn = self.pyodbc.connect(conn_str)
            with conn.cursor() as cursor:
                cursor.execute(query, on)
                rows = cursor.fetchall()
            conn.close()
            if rows:
                grouped_records = {}
                for record in rows:
                    modifiable_record = list(record)
                    customer_id = modifiable_record[1]  # Second value in the record
                    sensor_type = modifiable_record[3]  # Fourth value in the record

                    if customer_id not in grouped_records:
                        grouped_records[customer_id] = {}
                    if sensor_type not in grouped_records[customer_id]:
                        grouped_records[customer_id][sensor_type] = []

                    # Append the record to the appropriate group
                    grouped_records[customer_id][sensor_type].append(modifiable_record)

                # Now, it's safe to use 'customer_id' as it's guaranteed to be assigned
                # Sort the records within each sensor type by the serial number (the first value in each record)
                for sensor_type in grouped_records[customer_id].keys():
                    grouped_records[customer_id][sensor_type] = sorted(grouped_records[customer_id][sensor_type],
                                                                       key=lambda x: x[0])
                return grouped_records
            return 0
        except self.pyodbc.Error as e:
            print("EXCEPTION in get_records(): ", e)
            return None

    def get_all_records(self, current_date):
        try:
            query_results = {}
            conn = self.do_connection_string()
            for query_name, query in self.database_conf['CalibrationsToReport'].items():
                print(f"Executing query: {query_name}")
                query_results[query_name] = self.get_records(conn, query, current_date)
            grouped_records = {}
            for query_name, query_records in query_results.items():
                # Check if there are records to process
                if not query_records:
                    continue  # Skip to the next iteration if there are no records

                for record in query_records:
                    modifiable_record = list(record)
                    customer_id = modifiable_record[1]  # Second value in the record
                    sensor_type = modifiable_record[3]  # Fourth value in the record
                    modifiable_record.append(query_name)

                    if customer_id not in grouped_records:
                        grouped_records[customer_id] = {}
                    if sensor_type not in grouped_records[customer_id]:
                        grouped_records[customer_id][sensor_type] = []

                    # Append the record to the appropriate group
                    grouped_records[customer_id][sensor_type].append(modifiable_record)

                # Now, it's safe to use 'customer_id' as it's guaranteed to be assigned
                # Sort the records within each sensor type by the serial number (the first value in each record)
                for sensor_type in grouped_records[customer_id].keys():
                    grouped_records[customer_id][sensor_type] = sorted(grouped_records[customer_id][sensor_type],
                                                                       key=lambda x: x[0])
            print(grouped_records)
            return grouped_records
        except Exception as e:
            print("EXCEPTION in get_all_records() :", e)
            return None

