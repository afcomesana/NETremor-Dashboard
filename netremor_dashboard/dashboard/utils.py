# PYTHON LIBRARIES
import os
import re
import csv
import math
import requests
import itertools
import numpy as np
from scipy import signal

# CUSTOM MODULES
from utils import get_random_string
import imu

# DJANGO FRAMEWORK
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.conf import settings
from dashboard.models import Verification
from django.urls import reverse


RECORD_PARSE = {
    "x": float,
    "y": float,
    "z": float,
    "timestamp": int,
    "heartRate": int,
}

###############
# HANDLE USERS
###############
def user_exists(username):
    if re.search("@", username):
        return User.objects.filter(email = username).exists()
        
    return User.objects.filter(username = username).exists()

def is_email_domain_valid(email):
    allowed_domains_matchted = list(
        filter(
            lambda email_domain: re.search(rf"\@{email_domain}$", email),
            settings.ALLOWED_EMAIL_DOMAINS
        )
    )

    return len(allowed_domains_matchted) > 0

def is_password_valid(password):
    
    # Minimum length:
    if len(password) < 8: return False
    
    # At least 1 uppercase letter:
    if not re.search(r"[A-Z]", password): return False
    
    # At least 1 lowercase letter:
    if not re.search(r"[a-z]", password): return False
    
    # At least 1 number:
    if not re.search(r"[0-9]", password): return False
    
    # At least 1 strange character:
    if not re.search(r"[!@#$%&/()_-]", password): return False
    
    return True
    
def login_user(request, template, context, form_fields):
    
    # Get username and password from form
    username, password = form_fields.values()
    
    # Check that is reigstered
    if not user_exists(username):
        context["login_error_message"] = "No existe un usuario con ese nombre de usuario o correo electrónico. Por favor, crea una cuenta."
        return render(request, template, context)

    # Check the login method: email or username
    if re.search("@", username):
        username = User.objects.get(email = username)
        
    user = authenticate(request, username = username, password = password)
    
    # If authentication process fails:
    if user is None:
        context["login_error_message"] = "La contraseña es incorrecta. Por favor, inténtalo de nuevo."
        return render(request, template, context)
    
    # Check if the user has verified its account:
    try:
        if not user.verification.is_verified:
            context["login_error_message"] = "La cuenta no está verificada. <a style='text-decoration: underline;' href='%s'>Haz click aquí para reenviar el correo de verificación.</a>" % reverse("dashboard:verification_form")
            
        
    except Verification.DoesNotExist:
        if user.is_superuser:
            pass
        
        else:
            context["login_error_message"] = "La cuenta no está verificada. <a style='text-decoration: underline;' href='%s'>Haz click aquí para reenviar el correo de verificación.</a>" % reverse("dashboard:verification_form")
            return render(request, template, context)
    
    login(request, user)
    
    return redirect("dashboard:index")
    
def register_user(request, template, context, form_fields):
    username, email, password, password_repeat = form_fields.values()
    
    # Validate username
    suggested_username = re.sub(r'[^a-zA-Z0-9\_\.]', "_", username)
    if suggested_username != username:
        suggested_username = re.sub(r'[_]+', "_", suggested_username)
        
        context["register_error_message"] = "El nombre de usuario contiene caracteres no admitidos. Nombre de usuario sugerido: %s" % suggested_username
        return render(request, template, context)
    
    if user_exists(username):
        context["register_error_message"] = "El nombre de usuario ya existe. Por favor, elige otro nombre de usuario."
        return render(request, template, context)
    
    # Validate email:
    if not is_email_domain_valid(email):
        register_error_message = "El dominio del correo electrónico no es válido. Los correos permitidos son "
        register_error_message += ", ".join(settings.ALLOWED_EMAIL_DOMAINS[:-1])
        register_error_message += " y %s." % settings.ALLOWED_EMAIL_DOMAINS[-1]
        context["register_error_message"] = register_error_message
        
        return render(request, template, context)
    
    if user_exists(email):
        context["register_error_message"] = "Este correo electrónico ya está en uso."
        return render(request, template, context)
    
    # Validate password:
    if not is_password_valid(password):
        context["register_error_message"] = "La contraseña no cumple los requerimientos. Por favor, elige una contraseña adecuada."
        return render(request, template, context)
    
    if password != password_repeat:
        context["register_error_message"] = "Las contraseñas no coinciden."
        return render(request, template, context)
    
    user = User.objects.create_user(username, email, password)
    user.save()
    
    user_verification = Verification(user=user, code=get_random_string(settings.VERIFICATION_CODE_LENGTH))
    user_verification.save()
    send_verification_email(user)
    
    
    # request.session["registered_user_email"] = user.email
    
    response = redirect("dashboard:verification_form")
    response.set_cookie("registered_user_email", user.email, max_age=10)
    return response

def send_verification_email(user):
    data = {
        "email_to": user.email,
        "email_from": "NETremor <netremor@oriontech.es>",
        "email_subject": "Verificación de cuenta",
    }
    
    email_message  = "Hola %s,\n\n" % user.username
    email_message += "Te has registrado correctamente en la plataforma de NETremor.\nPara verificar tu cuenta y poder utilizar la plataforma debes acceder a la siguiente dirección:\n\n"
    email_message +=  "https://netremor.oriontech.es/verification/%s/%s/\n\n" % (user.id, user.verification.code)
    email_message += "Con cualquier duda, puedes enviar un correo a la siguiente dirección:\n"
    email_message += "alberto.comesana@csic.es\n\n"
    email_message += "Un saludo."
    
    data["email_message"] = email_message
    
    req = requests.post("https://mailproxy.oriontech.es", json = data)
    
    print(req.text)
 
#################
# HANDLE RECORDS   
#################
def get_record_tasks(record, columns, callback):

    columns      = list(set(["task_id"] + columns))
    record_tasks = record.datafile_task_rel_set.values(*columns).distinct().order_by("task_id")
    tasks        = {}
    
    for task_id, group in itertools.groupby(record_tasks, lambda item: item["task_id"]):
                
        tasks[task_id] = {
            "task": Task.objects.get(id=task_id),
            "trials": list(map(callback, group)), 
        }
        
    return tasks.values()


def get_continuous_datafile(datafile, samples, timestamp_from = None, timestamp_to = None):
    """Read inertial sensor data from raw file.

    Args:
        datafile (Datafile): datafile from the database the has been requested
        samples (Int): number of samples to read from the datafile (this is given by the screen width of the user)
        selection (Float[]): proportion of the file at which start and finish to read

    Returns:
        JSON: Raw data from the datafile.
        List of objects with the following keys: "x", "y", "z", "timestamp"
    """
    
    record_data   = []
    datafile_path = os.path.join(settings.DATAFILES_DIR, datafile.name)
    
    with open(datafile_path) as file:
        
        # Count how many rows are there in the CSV file:
        file_rows = sum(1 for _ in file) - 1
        file.seek(0)
        
        if timestamp_from is None and timestamp_to is None:
        
            # Number of rows to skip per read row
            step = max(1, math.floor(file_rows / samples))

            index = 0
        
            for row in csv.DictReader(file):
                
                # This row number has to be skipped:
                if index % step != 0:
                    index += 1
                    continue
                
                index += 1

                record_data += [{key: RECORD_PARSE[key](row[key]) for key in row}]
                
        else:
            
            for row in csv.DictReader(file):
                
                if int(row["timestamp"]) < timestamp_from:
                    continue
                
                if int(row["timestamp"]) > timestamp_to:
                    break

                record_data += [{key: RECORD_PARSE[key](row[key]) for key in row}]

        
    record_data = sorted(record_data, key=lambda item: item["timestamp"]) if len(record_data) > 0 else None
 
    return record_data
    
def get_continuous_imufile(imufile, samples, timestamp_from = None, timestamp_to = None):
    imufile_path = os.path.join(settings.IMUFILES_DIR, imufile.name)
    
    data, step, initial_timestamp, delta_t = imu.rimu(imufile_path, n_samples = int(samples))
    
    return [{"x": item[0], "y": item[1], "z": item[2], "timestamp": initial_timestamp + (step*delta_t*index)} for index, item in enumerate(data)][1:]
    
    
def get_ambulatory_record_trial_data(record, task_id, trial):

    datafile_ids = record.datafile_task_rel_set.filter(task_id=task_id, trial=trial).values_list("datafile", flat=True)
    datafiles    = Datafile.objects.filter(pk__in=datafile_ids)
    
    record_data = []
    
    for datafile in datafiles:
        
        datafile_path = os.path.join(settings.DATAFILES_DIR, datafile.name)
        
        # Limit file reading, we are going to send the first two hours
        # If the user wants to see more, it will have to be requested
        with open(datafile_path) as file:
            
            for row in csv.DictReader(file):

                data_row = {}
                
                for key in row:
                    data_row[key] = RECORD_PARSE[key](row[key])

                data_row["sensor"] = datafile.sensor

                record_data += [data_row]
        
    record_data = sorted(record_data, key=lambda item: item["timestamp"]) if len(record_data) > 0 else None
 
    return record_data

def get_ambulatory_record_trial_spectrogram(record, task_id, trial, axis = "x"):
    
    LOW_PASS_FREQ  = 2 # Herz
    HIGH_PASS_FREQ = 8 # Herz
    SAMPLE_FREQ    = 30 # Herz
    SAMPLE_PERIOD  = 1 / SAMPLE_FREQ # seconds
    HOP_SECONDS    = 1 # seconds
    HOP_SAMPLES    = HOP_SECONDS*SAMPLE_FREQ
    WINDOW_SECONDS = 2
    WINDOW_SIZE    = WINDOW_SECONDS*SAMPLE_FREQ
    
    OVERSAMPLING_FACTOR = 16
    GAUSSIAN_WINDOW = signal.windows.gaussian(WINDOW_SIZE, std=12, sym=True)
    
    raw_data = get_ambulatory_record_trial_data(record, task_id, trial)

    raw_data_acc  = np.array(list(map(lambda item: item[axis], filter(lambda item: item["sensor"] == "accelerometer", raw_data))))
    raw_data_gyro = np.array(list(map(lambda item: item[axis], filter(lambda item: item["sensor"] == "gyroscope", raw_data))))
    
    # Numerator and denominator of the polynomials of the IIR filter
    b, a = signal.butter(N=4, Wn=[LOW_PASS_FREQ, HIGH_PASS_FREQ], btype="bandpass", fs=SAMPLE_FREQ)

    # filtfilt the input acceleracion_(x|y|z) filtered
    raw_data_acc  = signal.filtfilt(b, a, signal.filtfilt(b, a, raw_data_acc))
    raw_data_gyro = signal.filtfilt(b, a, signal.filtfilt(b, a, raw_data_gyro))

    
    SFT = signal.ShortTimeFFT(GAUSSIAN_WINDOW, hop=HOP_SAMPLES, fs=SAMPLE_FREQ, mfft=OVERSAMPLING_FACTOR*SAMPLE_FREQ, scale_to="psd")
    
    Sx_acc  = SFT.spectrogram(raw_data_acc).tolist()
    Sx_gyro = SFT.spectrogram(raw_data_gyro).tolist()
    
    
    Sx_acc  = list(map(lambda item: {"psd": item, "sensor": "accelerometer"}, Sx_acc))
    Sx_gyro = list(map(lambda item: {"psd": item, "sensor": "gyroscope"}, Sx_gyro))
    
    return Sx_acc + Sx_gyro
    