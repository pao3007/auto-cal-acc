import builtins
import ctypes
import os
import sys
from datetime import datetime, timedelta
import psutil
import winshell
from win32com.client import Dispatch
import schedule
import time
from Definitions import DailyReport, send_email

start_fold = os.getcwd()
current_month_year = datetime.now().strftime("%Y-%m")
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
filename = f"LOG_FILE.txt"
filename = os.path.join(start_fold, filename)


def excepthook(exc_type, exc_value, exc_tb):
    from traceback import format_exception
    from datetime import datetime

    tb = "".join(format_exception(exc_type, exc_value, exc_tb))
    current_time = datetime.now().time().strftime("%H:%M:%S.%f")
    today = datetime.today().strftime("%b-%d-%Y")
    with open(filename, "a") as f:  # Open the file in append mode
        f.write("\n-- " + today)
        f.write(" " + current_time)
        f.write(tb + "\n")  # Write the traceback to the file
    sys.exit(1)


# Install exception hook
# sys.excepthook = excepthook


def custom_print(*args, **kwargs):
    # Get the current time and date
    timestamp_print = datetime.now().strftime("%H:%M:%S")
    # Construct the message with timestamp, separating it from the actual message by a space
    custom_args = (f"[{timestamp_print}] {' '.join(map(str, args))}",)
    txt = f"[{timestamp_print}] {' '.join(map(str, args))}"
    # Call the original print function with the new message
    with open(filename, 'a') as file:
        file.write(txt + "\n")
    builtins.original_print(*custom_args, **kwargs)


builtins.original_print = builtins.print
builtins.print = custom_print

print("STARTING CalibrationDailyReportSystem")


def hide_console():
    whnd = ctypes.WinDLL('kernel32').GetConsoleWindow()
    if whnd != 0:
        ctypes.WinDLL('user32').ShowWindow(whnd, 0)
        ctypes.WinDLL('kernel32').CloseHandle(whnd)


def terminate_existing_process(process_name):
    for process in psutil.process_iter(['name']):
        try:
            if process.info['name'] == process_name:
                process.terminate()
                process.wait()
                print(f"Terminated '{process_name}'.")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


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
        print("EXCEPTION in round_time_to_nearest_half_hour() : ",e)
        return None


def create_shortcut_at_startup():
    startup_dir = winshell.startup()
    print(startup_dir)
    shortcut_path = os.path.join(startup_dir, "CalibrationDailyReportSystem.lnk")
    print(shortcut_path)
    target_path = os.path.join(start_fold, "CalibrationDailyReportSystem.exe")
    # target_path = "CalibrationDailyReportSystem.exe"
    print(target_path)

    if os.path.isfile(shortcut_path):
        os.remove(shortcut_path)
        print("Existing shortcut removed.")

    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(shortcut_path)
    shortcut.Targetpath = target_path
    shortcut.WorkingDirectory = os.path.dirname(target_path)
    shortcut.IconLocation = target_path
    shortcut.WindowStyle = 7
    shortcut.save()

    print(f"New shortcut created in Startup folder: {shortcut_path}")


def schedule_tasks(start_time, end_time, interval):
    current_time = start_time
    while current_time < end_time:
        schedule_time = current_time.strftime("%H:%M")
        schedule.every().day.at(schedule_time).do(task)
        print(f"Task scheduled at {schedule_time}")
        # Calculate next schedule time
        next_time = current_time + timedelta(minutes=interval)
        current_time = next_time


def trouble(text="Nastala chyba v programe"):
    print("Sending trouble email")
    send_email(cal_report.email_settings, "lukap1999@gmail.com", "Daily-Report-ERROR", text)


def task():
    print(f"Task executed at {datetime.now()}")
    if datetime.today().weekday() < 5:
        current_time = round_time_to_nearest_half_hour(datetime.now())
        if current_time is None:
            trouble()
            return
        res = cal_report.load_email_settings()
        if res is None:
            trouble()
            return
        receivers = cal_report.load_emails_for_report(current_time)
        if receivers is None:
            trouble()
            return
        if receivers[0] != "none":
            date = datetime.now().strftime('%Y-%m-%d')
            res = cal_report.do_daily_report(date, receivers, current_time)
            if res is None or res > 0:
                trouble()
        else:
            print("No receivers to send data")
    else:
        print("Weekend!")


start_time = datetime.strptime("06:00", "%H:%M")
end_time = datetime.strptime("16:30", "%H:%M")
interval = 30  # minutes
schedule_tasks(start_time, end_time, interval)

cal_report = DailyReport(os.getcwd())
create_shortcut_at_startup()
print("Hiding Console!")
time.sleep(1)
hide_console()


while True:
    schedule.run_pending()
    time.sleep(10)
