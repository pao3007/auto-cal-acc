import smtplib
import time
from datetime import timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from os import path
from yaml import safe_load
from Database import DatabaseCom


def send_email(email_settings, receiver_email, subject, body):
    print("send_email")
    try:
        smtp_server = email_settings['smtp_server']
        port = int(email_settings['port'])
        psw = email_settings['sender_password']
        user = email_settings['user']
        sender_email = email_settings['sender_email']
        server = smtplib.SMTP(smtp_server, port)
        if email_settings['ssl']:
            print("TLS ON")
            server.starttls()
        server.login(user, psw)

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        server.send_message(msg)
        server.quit()
        return 0
    except Exception as e:
        print("EXCEPTION in send_email() :", e)
        return None


def generate_email_body(grouped_records):
    print("generate_email_body")
    try:
        email_body = ""

        for customer_id, sensors in grouped_records.items():
            customer_name = list(sensors.values())[0][0][2]

            email_body += f"{customer_id} - {customer_name}:\n"

            for sensor_type, records in sensors.items():
                pass_count = sum(1 for record in records if record[4] == 'PASS')
                fail_count = len(records) - pass_count

                email_body += f"\t{sensor_type}: {len(records)} kalibrované, {pass_count} PASS, {fail_count} FAIL\n"

                for record in records:
                    serial_number = record[0]  # 1st value of record
                    pass_fail = record[4]  # 2nd from last position
                    val1 = record[6]
                    val2 = record[7]
                    if isinstance(val1, str):
                        val1 = float(val1.replace(',', '.'))
                    if isinstance(val2, str) and not None:
                        val2 = float(val2.replace(',', '.'))

                    query = record[-1]
                    if query == "GetParamsAcc":
                        val1_info = "Sens: "
                        val1 = f"{round(val1, 2)} pm/g"
                        val2_info = ""
                        if val2 is not None:
                            val2_info = "Offset: "
                            val2 = f"{round(val2, 4)} nm"
                        else:
                            val2 = ""
                    elif query == "GetParamsStrain":
                        val1_info = "ACoeff: "
                        val1 = "{:.4e}".format(val1)
                        val2_info = "FFL: "
                        val2 = f"{round(val2, 4)} m"
                    else:
                        val1_info = ""
                        val2_info = ""
                    email_body += f"\t\t{serial_number}: {pass_fail}\n\t\t\t{val1_info}{val1}; {val2_info}{val2}\n"

                email_body += "\n"  # Add a newline for separation between sensor types

            email_body += "-"*70 + "\n"  # Add a separator line between different orders
        return email_body
    except Exception as e:
        print("EXCEPTION in generate_email_body() :", e)
        return None


def round_time_to_nearest_half_hour(current_time):
    print("round_time_to_nearest_half_hour")
    try:
        minutes = current_time.minute
        seconds = current_time.second

        if minutes < 15 or (minutes == 15 and seconds == 0):
            rounding = timedelta(minutes=-minutes, seconds=-seconds)
        elif 15 <= minutes < 45 or (minutes == 45 and seconds == 0):
            rounding = timedelta(minutes=30-minutes, seconds=-seconds)
        else:
            rounding = timedelta(hours=1, minutes=-minutes, seconds=-seconds)

        rounded_time = current_time + rounding
        return str(rounded_time.strftime('%H:%M'))
    except Exception as e:
        print("EXCEPTION in round_time_to_nearest_half_hour() :", e)
        return None


class DailyReport:

    def __init__(self, start_folder):
        self.start_folder = start_folder
        self.db = DatabaseCom(self.start_folder)
        self.email_settings = None
        self.load_email_settings()

    def load_email_settings(self):
        print("load_email_settings")
        try:
            filename = path.join(self.start_folder, "email_settings.yaml")
            with open(filename, 'r', encoding="utf-8") as file:
                self.email_settings = safe_load(file)
            return 0
        except Exception as e:
            print("EXCEPTION in load_email_settings(): ", e)
            return None

    def do_daily_report(self, today, receivers, current_time, subject="Kalibrácia - Automatický Report"):
        print("do_daily_report")
        error = 0
        try:
            self.db.load_config()
            grouped_records = self.db.get_all_records(today)
            if grouped_records is None:
                return None
            body = generate_email_body(grouped_records)
            if body is None:
                return None
            if len(body) == 0:
                if current_time != "14:00":
                    print("Preskakujem odoslanie zbytočného emailu")
                    return 0
                body = "Dnes neprebehla žiadna ACC alebo STRAIN kalibrácia"
            print("body: ", body)
            for receiver in receivers:
                res = send_email(self.email_settings, receiver, subject, body)
                if res is not None:
                    print("Report send to : ", receiver)
                else:
                    print("Could not send report to : ", receiver)
                    error += 1
                time.sleep(1)
            return error
        except Exception as e:
            print("EXCEPTION in do_daily_report() :", e)
            return None

    def load_emails_for_report(self, scheduled_time):
        print("load_emails_for_report")
        try:
            filename = path.join(self.start_folder, "receivers.yaml")
            with open(filename, 'r', encoding="utf-8") as file:
                receivers_yaml = safe_load(file)
            all_receivers = receivers_yaml['time'][f'{scheduled_time}']
            return all_receivers
        except Exception as e:
            print("EXCEPTION in load_emails_for_report() :", e)
            return None
