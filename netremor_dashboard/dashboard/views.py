from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, HttpResponseBadRequest, HttpResponseServerError
from django.template import loader
from endpoint.models import Subject, Record, Datafile, Task, Datafile_task_rel
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .constants import LOGIN_FORM_FIELDS
from django.contrib.auth import logout

from utils import get_random_string
from .utils import send_verification_email, get_record_tasks, get_continuous_record_data
import os
import json
import zipfile
import numpy as np
from pytz import timezone
from datetime import datetime


@login_required
def index(request):
    
    subject_ids = set(datafile.record.subject.id for datafile in Datafile.objects.filter(is_processed=True))    
    subjects_list = Subject.objects.filter(id__in=subject_ids)
    
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
        context["form_fields"] = form_fields
        
        
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
    
    ambulatory_records = subject.record_set.filter(type="ambulatory")
    if ambulatory_records:
        for record in ambulatory_records:
            record.tasks_number = record.datafile_task_rel_set.values("task_id").distinct().count()
            
        context["ambulatory_records"] = ambulatory_records
    
    
    return render(request, "dashboard/records.html", context)

@login_required
def record(request, record_id):
    """
    Get information and files data about a certain record.
    Several different requests are meant to be handled by this view:
    1) GET request when record page is first loaded
    2) GET request to download the data from the record
    3.a) POST request to get the data from a certain task
    3.b) POST request to get the data from in a selected range

    Args:
        request (WSGIRequest): default arguments received by django views
        record_id (Int): ID of the requested record

    Returns:
        HttpResponse: 
        1) HTML document without a chart and with the information of all the tasks related to this record.
        2) ZIP file containing all of the data belonging to this record
        3) JSON with the the data of the sensors
    """
    
    record = get_object_or_404(Record, pk=record_id)

    # 2)
    if "download" in request.GET.keys():
        
        # Stuff all the record files into a temporary zip file:
        zip_filename  = "%s-%s-%s.zip" % (record.subject.id, record.type, record.id)
        zip_file_path = os.path.join(settings.DATAFILES_DIR, zip_filename)
        
        with zipfile.ZipFile(zip_file_path, "w") as temp_zip:
            for datafile in Datafile.objects.filter(record_id=record_id):
                filename = datafile.name
                try:
                    datafile_task_rel = Datafile_task_rel.objects.get(datafile=datafile)
                    task_id = datafile_task_rel.task.id.lower()
                    filename, extension = filename.split(".")
                    if len(list(filter(lambda item: item.lower() == task_id, filename.split("-")))) == 0:
                        filename += "-%s" % task_id
                        
                    filename = ".".join([filename, extension])
                    
                except Datafile_task_rel.DoesNotExist:
                    pass
                
                data_file_path = os.path.join(settings.DATAFILES_DIR, datafile.name)
                temp_zip.write(data_file_path, filename)
             
                
            # For continuous records, add a CSV with the information regarding
            # start and finish timestamps for each task in the record
            if record.type == "continuous":
                
                record_tasks = record.datafile_task_rel_set.values("task_id", "starts_at", "ends_at").distinct()
                record_tasks = list(map(lambda task: "%s,%s,%s" % (
                    task["task_id"],    
                    int(task["starts_at"].timestamp() * 1000),    
                    int(task["ends_at"].timestamp() * 1000),
                ), record_tasks))
                
                temp_zip.writestr("%s-tasks.csv" % record.subject.id, "\n".join(record_tasks))
                            
        # Send bytes of zip files as a downloadable and remove the zip file:
        with open(zip_file_path, "rb") as temp_zip:
            
            response = HttpResponse(temp_zip.read(), content_type="application/octet-stream")
            response.headers["Content-disposition"] = "inline; filename=%s" % zip_filename
            
            os.remove(zip_file_path)
                
            return response

    
    # 3)
    if request.method == "POST":
        
        # 3.b)
        if record.type == "continuous":
            sensor, metric, samples, time_range = json.loads(request.body).values()
            
            if not time_range:
                timestamp_from = timestamp_to = None
                
            else:
                time_range = [int(item) for item in time_range]
                timestamp_from, timestamp_to = time_range
            
            try:
                data, limits, step = get_continuous_record_data(record, sensor, metric, samples, timestamp_from, timestamp_to)
                
                filter_size = 30
                
                data_keys = list(filter(lambda key: key != "timestamp", data[0][0].keys()))
                
                for chunk in data:
                
                    chunk_length = len(chunk)
                    
                    for index in range(chunk_length):
                        
                        from_index = max(0, index - filter_size)
                        to_index   = min(index + filter_size, chunk_length)
                        
                        mean_set  = chunk[from_index:to_index]
                        mean_item = {"timestamp": chunk[index]["timestamp"]}
                        for key in data_keys:
                            mean_item[key] = np.mean([item[key] for item in mean_set])
                            
                        chunk[index] = mean_item
                            
            except Exception as e:
                print(e)
                return HttpResponseServerError("There is still no data in this record.")
            
            # 1) CSV files:
            # response_data = get_continuous_record_csv_data(record, samples, timestamp_from, timestamp_to)
            
            # 2) IMU files:
            # response_data = get_continuous_record_imu_data(record, samples, timestamp_from, timestamp_to)
            
            response_data = {"data": data, "limits": limits, "step": step}
            
        elif record.type == "ambulatory":
            params = json.loads(request.body)
            
            if params["metric"] == "raw":
                try:
                    response_data = get_ambulatory_record_trial_data(record, params["taskId"], params["trial"])
                    
                except FileNotFoundError:
                    return HttpResponseBadRequest("Requested file doesn't exists.")
                
                except KeyError as e:
                    print(e)
                    return HttpResponseBadRequest("CSV file ill-formed.")
                
            elif params["metric"] == "spectrogram":
                response_data = get_ambulatory_record_trial_spectrogram(record, params["taskId"], params["trial"])
                
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
        columns  = ["trial"]
        callback = lambda item: item["trial"]
        
    elif record.type == "continuous":
        columns  = ["starts_at", "ends_at"]
        callback = lambda item: [
            datetime.fromtimestamp(item["starts_at"]/1000).astimezone(timezone("Europe/Madrid")),
            datetime.fromtimestamp(item["ends_at"]/1000).astimezone(timezone("Europe/Madrid"))
        ]
        
    response["tasks"] = get_record_tasks(record, columns, callback)
        
    return render(
        request,
        "dashboard/record.html",
        response
    )

