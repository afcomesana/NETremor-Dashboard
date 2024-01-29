from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError
from django.template import loader
from endpoint.models import Subject, Record, DataFile
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .constants import LOGIN_FORM_FIELDS
from django.contrib.auth import logout

from utils import get_random_string
from .utils import send_verification_email

import os
import csv
import json
import math
import itertools
import zipfile

RECORD_PARSE = {
    "x": float,
    "y": float,
    "z": float,
    "timestamp": int,
    "heartRate": int,
}

@login_required
def index(request):
    subjects_list = Subject.objects.all()
    
    # template = loader.get_template("dashboard/index.html")
    context = {
        "subjects_list": subjects_list
    }
    
    return render(request, "dashboard/index.html", context)


def login(request):
    context = {
        "hide_topbar": True,
        "login_form": LOGIN_FORM_FIELDS["login"]["fields"],
        "register_form": LOGIN_FORM_FIELDS["register"]["fields"],
    }
    
    if request.method == "POST":
        try:
            form_type = request.POST["form_type"]
            if form_type not in LOGIN_FORM_FIELDS.keys():
                return HttpResponseBadRequest("No se ha especificado un tipo de formulario válido")  
              
        except Exception as e:
            print("Error during getting form type in login page:", e)
            return HttpResponseBadRequest("No se ha especificado un tipo de formulario válido")
        
        
        form_type_fields, callback = LOGIN_FORM_FIELDS[form_type].values()
        
        missing_fields = []
        form_fields    = {}
        
        
        for field in form_type_fields:
            field_name = "%s_%s" % (form_type, field["name"]) # actual name that this field has in the DOM
            
            try:
                # Field is included in the POST request but it's empty
                if not request.POST[field_name] and field["is_required"]:
                    missing_fields += [field_name]
                    continue
                
                form_fields[field_name] = request.POST[field_name]
               
            # In case this field is not included in the POST request
            # (or any other error), include it as a missing field: 
            except Exception as e:
                missing_fields += [field_name]
            
        # Provide form_fields in case it is necessary to fill the form fields again
        context["form_fields"]    = form_fields
        
        
        if len(missing_fields) > 0:
            context["missing_fields"] = missing_fields
            return render(request, "dashboard/login.html", context)
        
        return callback(request, "dashboard/login.html", context, form_fields)
        
    return render(request, "dashboard/login.html", context)


def verification_form(request):
    
    context = {
        "verification_title": "Indica el correo electrónico de tu usuario:",
        "verification_text": "",
        "verification_subtitle": "",
        "user_email": "",
        "verification_error_message": "",
        "is_input_readonly": False,
        "is_submit_button_hidden": False,
        "is_login_button_hidden": True,
    }
    
    verification_text = "Recibirás un correo electrónico con un enlace para verificar tu cuenta. Por si acaso, revisa tu carpeta de spam."
    
    # Resend button has been clicked:
    if request.method == "POST":
        
        # Email is empty:
        if not request.POST["verification_user_email"]:
            context["verification_error_message"] = "No se ha indicado un correo electrónico para reenviar la verificación."
            return render(request, "dashboard/verification-form.html", context)
        
        context["user_email"] = request.POST["verification_user_email"]
        
        try:
            verification_user = User.objects.get(email = request.POST["verification_user_email"])
            
            if verification_user.verification.is_verified == True:
                context["verification_title"]      = "La cuenta asociada a este correo electrónico ya está verificada."
                context["verification_text"]       = ""
                context["verification_subtitle"]   = "Ya puedes inicar sesión."
                context["is_login_button_hidden"]  = False
                context["is_submit_button_hidden"] = True
                context["is_input_readonly"] = True
                
                return render(request, "dashboard/verification-form.html", context)
            
            verification_user.verification.code = get_random_string(settings.VERIFICATION_CODE_LENGTH)
            verification_user.verification.save()
            
            send_verification_email(verification_user)
            context["is_input_readonly"]       = True
            context["verification_title"]      = "¡Correo de verificación reenviado!"
            context["verification_subtitle"]   = "Si no recibes el correo de verificación, <a style='text-decoration: underline;' href='mailto:alberto.comesana@csic.es'>ponte en contacto con el soporte</a>."
            context["is_submit_button_hidden"] = True
            
            return render(request, "dashboard/verification-form.html", context)
            
        except User.DoesNotExist:
            context["verification_error_message"] = "No existe ningún usuario con ese correo electrónico."
            return render(request, "dashboard/verification-form.html", context)
    
    # The user just signed up:
    if "registered_user_email" in request.COOKIES.keys():
        context["verification_title"]    = "¡Te has registrado correctamente!"
        context["verification_text"]     = verification_text
        context["verification_subtitle"] = "¿No has recibido el correo de verificación?<br>Vuelve a intentarlo"
        context["user_email"]            = request.COOKIES["registered_user_email"]
        context["is_input_readonly"]     = True

    
    return render(request, "dashboard/verification-form.html", context)

def verification_process(request, user_id, verification_code):
    context = {
        "is_success": False,
        "error_message": "",
        "warning_message": "",
    }
    
    # Get user corresponding to provided ID
    try:
        user = User.objects.get(id = user_id)
        
    except User.DoesNotExist:
        context["error_message"] = "El usuario que se está tratando de verificar no existe."
        return render(request, "dashboard/verification-process.html", context)

        
    if user.verification.is_verified == True:
        context["warning_message"] = "Tu usuario ya ha sido verificado."
        return render(request, "dashboard/verification-process.html", context)
    
    # User code doesn't match:
    if user.verification.code != verification_code:
        context["error_message"] = "El código de verificación no es correcto."
        return render(request, "dashboard/verification-process.html", context)
    
    # Save user as a verified user:
    user.verification.is_verified = True
    user.verification.save()
    
    context["is_success"] = True
    
    return render(request, "dashboard/verification-process.html", context)

@login_required
def logout_user(request):
    logout(request)
    return redirect("dashboard:login")

@login_required
def records(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    
    context = {"subject": subject}
    
    try:
        context["continuous_record"] = subject.record_set.get(type = "continuous")
        
    except Record.DoesNotExist:
        pass
    
    ambulatory_records = subject.record_set.filter(type = "ambulatory")
    if ambulatory_records:
        for record in ambulatory_records:
            record.tasks_number = record.datafile_set.filter(task_name__isnull=False).values("task_name").distinct().count()
            
        context["ambulatory_records"] = ambulatory_records
    
    
    return render(request, "dashboard/records.html", context)

@login_required
def record(request, record_id):
    record     = get_object_or_404(Record, pk=record_id)

    # Download files of the record:
    if "download" in request.GET.keys():
        
        # Stuff all the record files into a zip file:
        zip_filename  = "%s-%s-%s.zip" % (record.subject.id, record.type, record.id)
        zip_file_path = os.path.join(settings.DATA_FILES_DIR, zip_filename)
        
        with zipfile.ZipFile(zip_file_path, "w") as temp_zip:
            for data_file in DataFile.objects.filter(record_id=record_id):
                data_file_path = os.path.join(settings.DATA_FILES_DIR, data_file.name)
                temp_zip.write(data_file_path, data_file.name)
                
        # Send bytes of zip files as a downloadable:
        with open(zip_file_path, "rb") as temp_zip:
            
            response = HttpResponse(temp_zip.read(), content_type="application/octet-stream")
            response.headers["Content-disposition"] = "inline; filename=%s" % zip_filename
            
            os.remove(zip_file_path)
                
            return response

    
    # REQUEST ONLY THE DATA OF THE SENSORS:
    if request.method == "POST":
        
        if record.type == "continuous":
            
            sensor, metric, samples, selection = json.loads(request.body).values()
            
            data_file = record.datafile_set.get(sensor=sensor)
            response_data = get_continuous_data_file(data_file, samples, selection)
            
        elif record.type == "ambulatory":            
            params = json.loads(request.body)
            
            if params["metric"] == "raw":
                try:
                    response_data = get_ambulatory_data_file(params["id"])
                    
                except FileNotFoundError:
                    return HttpResponseBadRequest("Requested file doesn't exists.")
                
                except KeyError as e:
                    print(e)
                    return HttpResponseBadRequest("CSV file ill-formed.")
                
            elif params["metric"] == "spectrogram":
                response_data = []
                
            elif params["metric"] == "energy":
                response_data = []
                
            else:
                return HttpResponseBadRequest("Requested metric is not defined.")

            
        else:
            return HttpResponseServerError()
            
        
        return HttpResponse(json.dumps(response_data))


    # REQUESTING THE PAGE
    
    response = {
        "record": record,
        "sensor_choices": settings.SENSOR_CHOICES
    }
    
    if record.type == "ambulatory":
        response["tasks"] = get_ambulatory_record_tasks(record)
    
    return render(
        request,
        "dashboard/record.html",
        response
    )
    

def get_ambulatory_record_tasks(record):
    
    data_files = record.datafile_set.filter(task_name__isnull = False).values("id", "trial", "task_name", "task_description")

    tasks = {}

    for key, group in itertools.groupby(data_files, lambda item: item["task_name"]):
        
        for item in group:
            item["id"] = str(item["id"])
            
            if key not in tasks.keys():
                tasks[key] = {
                    "task_name": key,
                    "task_description": item["task_description"],
                    "data_file_ids": {
                        item["trial"]: [item["id"]]
                    }
                }
                
            elif item["trial"] not in tasks[key]["data_file_ids"].keys():
                tasks[key]["data_file_ids"][item["trial"]] = [item["id"]]
            
            else:
                tasks[key]["data_file_ids"][item["trial"]] += [item["id"]]
        
    tasks = list(tasks.values())
    
    for task in tasks:
        task["data_file_ids"] = sorted(task["data_file_ids"].items())
        task["data_file_ids"] = list(map(lambda item: "-".join(item[1]), task["data_file_ids"]))
        
        
    return tasks


def get_continuous_data_file(data_file, samples, selection):
    
    try:
        start_selection, end_selection = selection
    except ValueError:
        start_selection = end_selection = None
    
    record_data = []
    
    data_file_path = os.path.join(settings.DATA_FILES_DIR, data_file.name)
    
    # Limit file reading, we are going to send the first two hours
    # If the user wants to see more, it will have to be requested
    with open(data_file_path) as file:
        
        file_rows = selection_rows = sum(1 for _ in file) - 1
        file.seek(0) # reset pointer
        
        if not start_selection is None and not end_selection is None:
            start_selection = math.floor(start_selection * file_rows)
            end_selection   = math.ceil(end_selection * file_rows)
            
            selection_rows = end_selection - start_selection
        
        step = max(1, math.floor(selection_rows / samples)) # prevent step from becoming 0
        
        index = 0
    
        for row in csv.DictReader(file):
            
            if not start_selection is None and index < start_selection:
                index += 1
                continue
            
            if not end_selection is None and index > end_selection:
                index += 1
                continue
            
            if index % step != 0:
                index += 1
                continue
            
            index += 1
            
            data_row = {}
            
            for key in row:
                data_row[key] = RECORD_PARSE[key](row[key])

            record_data += [data_row]
        
    record_data = sorted(record_data, key=lambda item: item["timestamp"]) if len(record_data) > 0 else None
 
    return record_data
    
    
    
def get_ambulatory_data_file(data_file_ids):
    
    data_files = DataFile.objects.filter(pk__in=data_file_ids)
    
    record_data = []
    
    for data_file in data_files:
        
        data_file_path = os.path.join(settings.DATA_FILES_DIR, data_file.name)
        

        # Limit file reading, we are going to send the first two hours
        # If the user wants to see more, it will have to be requested
        with open(data_file_path) as file:
            
            for row in csv.DictReader(file):

                data_row = {}
                
                for key in row:
                    data_row[key] = RECORD_PARSE[key](row[key])   
                    
                data_row["taskName"] = data_file.task_name
                data_row["taskDescription"] = data_file.task_description
                data_row["sensor"] = data_file.sensor

                record_data += [data_row]
        
    record_data = sorted(record_data, key=lambda item: item["timestamp"]) if len(record_data) > 0 else None
 
    return record_data

def get_task_name_data_metric(record_id, task_name, metric):
    
    return True


def get_ambulatory_record_data(record):
    
    return True