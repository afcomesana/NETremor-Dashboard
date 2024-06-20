import re
import os
import time
import random
import string
import unicodedata
import numpy as np
import netremor_dashboard.settings as settings

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from datetime import datetime

def str2filename(text):
    """
    Convert any string to a file-like format.
    
    :param text: to be converted
    
    :return str: file-like string
    
    """
    filename = text.strip().lower().replace(" ", "_")
    filename = re.sub(r'[^0-9a-z\_\.]', "", filename)
    filename = re.sub(r'[_]+', "_", filename)
    filename = re.sub(r'[\.]+', "_", filename)
    
    return filename

def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore")
    text = text.decode("ASCII")
    
    return text

def get_random_string(length):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def measure_time(filename):
    """Measure elapsed time for the function to execute

    Args:
        func (function): function whose execution time we want to measure
    """

    def decorator(func):

        def wrapper(*args, **kwargs):
            
            ITER_TIMES = 100
            times = []
            for _ in range(ITER_TIMES):
                start_time = time.time()
                
                func(*args)
                
                end_time = time.time()
                
                times += [end_time - start_time]
                
            
            
            with open(filename, "a") as file:
                file.write(";".join([func.__name__, str(np.mean(times))]))
                file.write("\n")
            print("Mean time for %s: %s" % (func.__name__, np.mean(times)))
            
        return wrapper
    return decorator

def write_log(message, name = "default", level = settings.LOG_INFO):
    
    if not os.path.isdir(settings.LOG_DIR):
        os.mkdir(settings.LOG_DIR, 0o755)
    
    current_time = datetime.now()
    log_filename = "%s-%s.log" % (name, current_time.strftime("%Y-%m-%d"))
    
    with open(os.path.join(settings.LOG_DIR, log_filename), "a") as logfile:
        logfile.write("%s - %s: %s\n" % (current_time.strftime("%Y-%m-%d %H:%M:%S"), level.rjust(5, " "), message))
        

def send_mail(email_from, email_to, email_subject, email_body):
    
    msg            = MIMEMultipart()
    msg['From']    = email_from
    msg['To']      = email_to
    msg['Subject'] = email_subject

    msg.attach(MIMEText(email_body, 'plain'))
    
    with smtplib.SMTP('localhost') as server:
        server.sendmail(email_from, email_to, msg.as_string())