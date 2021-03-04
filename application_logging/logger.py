from datetime import datetime


def App_Logger(log_message):
    file = open("Training_Logs/GeneralLog.txt", 'a+')
    now = datetime.now()
    date = now.date()
    current_time = now.strftime("%H:%M:%S")
    file.write(str(date) + "/" + str(current_time) + "\t\t" + log_message +"\n")
